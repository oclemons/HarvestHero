"""Demo intake and account provisioning regressions."""

import os
import sys
import tempfile
import unittest
from pathlib import Path

WEB = Path(__file__).resolve().parents[1]
ROOT = WEB.parent
for directory in (str(ROOT), str(WEB)):
    if directory not in sys.path:
        sys.path.insert(0, directory)


class DemoFlow(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        os.environ["HARVESTHERO_DEV_DIR"] = self.temp.name
        os.environ["HARVESTHERO_SECRET_KEY"] = "test-secret-abcdefghijklmnop"
        os.environ["HARVESTHERO_COOKIE_SECURE"] = "0"
        for name in ("paths", "database", "auth", "app", "extensions", "security",
                     "errors", "logging_config", "decorators", "routes.auth",
                     "routes.dashboard", "routes.account", "routes.inventory",
                     "routes.scan", "routes.users"):
            sys.modules.pop(name, None)
        from auth import hash_password
        from database import Database
        self.db = Database()
        for username, role in (("demo_admin", "admin"), ("demo_student", "student")):
            hashed, salt = hash_password("DemoPass!123")
            self.db.create_user(username, hashed, salt, role)
        self.db.add_item("IN-123", "Peanut butter", "Pantry", 4, 5, "",
                         barcode_out="OUT-123")
        section_id = self.db.create_pantry_section("Pantry")
        self.shelf_id = self.db.create_pantry_shelf(section_id, "Shelf A")
        from app import create_app
        self.app = create_app()
        self.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False, RATELIMIT_ENABLED=False)
        self.client = self.app.test_client()

    def tearDown(self):
        self.temp.cleanup()

    def login(self, username):
        self.client.post("/login", data={"username": username, "password": "DemoPass!123"})

    def test_student_scan_in_is_atomic_and_visible(self):
        self.login("demo_student")
        self.client.post("/scan/in/add", data={"barcode": "IN-123", "shelf_id": self.shelf_id})
        self.assertEqual(self.db.get_item_by_barcode("IN-123")["current_quantity"], 4)
        cart = self.db.get_active_cart(self.db.get_user("demo_student")["id"], "IN")
        response = self.client.post("/scan/in/complete", data={"cart_id": cart["id"]},
                                    follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Intake recorded", response.data)
        self.assertEqual(self.db.get_item_by_barcode("IN-123")["current_quantity"], 5)
        stock = {row["shelf_id"]: row["quantity"] for row in self.db.get_item_shelf_stock(
            self.db.get_item_by_barcode("IN-123")["id"])}
        self.assertEqual(stock[self.shelf_id], 1)
        conn = self.db._connect()
        txn = conn.execute("SELECT * FROM transactions").fetchone()
        activity = conn.execute("SELECT * FROM activity_log WHERE action='CART_IN'").fetchone()
        conn.close()
        self.assertEqual((txn["transaction_type"], txn["username"], txn["quantity"]),
                         ("SCAN_IN", "demo_student", 1))
        self.assertEqual(activity["username"], "demo_student")

    def test_scan_out_barcode_rejected_without_stock_change(self):
        self.login("demo_student")
        response = self.client.post("/scan/in/add", data={
            "barcode": "OUT-123", "shelf_id": self.shelf_id,
        }, follow_redirects=True)
        self.assertIn(b"scan-out", response.data)
        self.assertEqual(self.db.get_item_by_barcode("IN-123")["current_quantity"], 4)
        self.assertEqual(self.db.get_recent_transactions(), [])

    def test_failed_transaction_rolls_back_quantity(self):
        conn = self.db._connect()
        conn.execute("CREATE TRIGGER fail_scan BEFORE INSERT ON transactions "
                     "BEGIN SELECT RAISE(ABORT, 'test failure'); END")
        conn.commit()
        conn.close()
        owner_id = self.db.get_user("demo_student")["id"]
        self.db.add_scan_to_cart(owner_id, "IN-123", self.shelf_id)
        cart = self.db.get_active_cart(owner_id, "IN")
        with self.assertRaises(Exception):
            self.db.complete_scan_in_cart(owner_id, cart["id"], "demo_student")
        item = self.db.get_item_by_barcode("IN-123")
        self.assertEqual(item["current_quantity"], 4)
        self.assertEqual(self.db.get_item_shelf_stock(item["id"])[0]["quantity"], 4)

    def test_admin_can_scan_and_student_cannot_create_users(self):
        self.login("demo_student")
        self.assertEqual(self.client.get("/admin/users/").status_code, 403)
        self.assertEqual(self.client.post("/admin/users/", data={"username": "hacker"}).status_code, 403)
        self.client.get("/logout")
        self.login("demo_admin")
        self.assertEqual(self.client.post("/scan/in/add", data={
            "barcode": "IN-123", "shelf_id": self.shelf_id,
        }).status_code, 302)
        self.assertEqual(self.client.get("/admin/users/").status_code, 200)

    def test_admin_creates_student_with_private_password(self):
        self.login("demo_admin")
        response = self.client.post("/admin/users/", data={
            "username": "new_student", "full_name": "New Student",
            "role": "student", "password": "AnotherPass!123",
            "confirm_password": "AnotherPass!123",
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(self.db.get_user("new_student"))
        self.assertNotIn(b"AnotherPass!123", response.data)

    def test_login_page_displays_harvest_hero_logo(self):
        response = self.client.get("/login")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'/assets/HarvestHeroIcon.png', response.data)
        self.assertIn(b'login-page', response.data)
        self.assertIn(b'login-hero', response.data)
        self.assertIn(b'font-family: "Times New Roman"', response.data)
        self.assertIn(b'body.login-page { background-color: #daf1de;', response.data)
        self.assertIn(b'.login-hero { background-color: #0c3b2e;', response.data)
        self.assertNotIn(b'<section class="bg-emerald-900', response.data)
        self.assertIn(b'A Clemons Collective', response.data)
        self.assertNotIn(b'Harvest Hero &middot; v', response.data)
        logo = self.client.get("/assets/HarvestHeroIcon.png")
        self.assertEqual(logo.status_code, 200)
        self.assertEqual(logo.mimetype, "image/png")

    def test_new_student_can_sign_in_with_temporary_password_regardless_of_username_case(self):
        self.login("demo_admin")
        response = self.client.post("/admin/users/", data={
            "username": "New_Student", "full_name": "New Student",
            "role": "student", "password": "AnotherPass!123",
            "confirm_password": "AnotherPass!123",
        })
        self.assertEqual(response.status_code, 302)
        self.client.get("/logout")
        response = self.client.post("/login", data={
            "username": "new_student", "password": "AnotherPass!123",
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"How intake works", response.data)
        self.assertNotIn(b"/admin/users/", response.data)

    def test_admin_reset_student_password_kicks_old_session(self):
        student_id = self.db.get_user("demo_student")["id"]
        student_session = self.app.test_client()
        student_session.post("/login", data={
            "username": "demo_student", "password": "DemoPass!123",
        })
        self.assertEqual(student_session.get("/app").status_code, 200)
        self.login("demo_admin")
        self.assertEqual(self.client.get(f"/admin/users/{student_id}/reset").status_code, 200)
        self.client.post(f"/admin/users/{student_id}/reset", data={
            "admin_password": "wrong", "password": "NewStudent!456",
            "confirm_password": "NewStudent!456",
        })
        from auth import verify_password
        unchanged = self.db.get_user("demo_student")
        self.assertTrue(verify_password("DemoPass!123", unchanged["password_hash"], unchanged["salt"]))
        response = self.client.post(f"/admin/users/{student_id}/reset", data={
            "admin_password": "DemoPass!123", "password": "NewStudent!456",
            "confirm_password": "NewStudent!456",
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(b"NewStudent!456", response.data)
        self.assertEqual(student_session.get("/app").status_code, 302)
        self.assertEqual(student_session.post("/login", data={
            "username": "demo_student", "password": "DemoPass!123",
        }).status_code, 200)
        login = student_session.post("/login", data={
            "username": "DEMO_STUDENT", "password": "NewStudent!456",
        }, follow_redirects=True)
        self.assertIn(b"How intake works", login.data)
        self.assertNotIn(b"/admin/users/", login.data)

    def test_student_cannot_reset_passwords_or_admin_account(self):
        student_id = self.db.get_user("demo_student")["id"]
        admin_id = self.db.get_user("demo_admin")["id"]
        self.login("demo_student")
        self.assertEqual(self.client.get(f"/admin/users/{student_id}/reset").status_code, 403)
        self.assertEqual(self.client.post(f"/admin/users/{admin_id}/reset", data={
            "password": "Wrong!123", "confirm_password": "Wrong!123",
        }).status_code, 403)
        self.client.get("/logout")
        self.login("demo_admin")
        self.assertNotEqual(self.client.get(f"/admin/users/{admin_id}/reset").status_code, 200)

    def test_admin_rejects_mismatched_temporary_passwords(self):
        self.login("demo_admin")
        response = self.client.post("/admin/users/", data={
            "username": "new_student", "role": "student", "password": "AnotherPass!123",
            "confirm_password": "DifferentPass!123",
        })
        self.assertEqual(response.status_code, 400)
        self.assertIsNone(self.db.get_user("new_student"))

    def test_case_insensitive_duplicate_username_is_rejected(self):
        self.login("demo_admin")
        response = self.client.post("/admin/users/", data={
            "username": "DEMO_STUDENT", "role": "student",
            "password": "AnotherPass!123", "confirm_password": "AnotherPass!123",
        })
        self.assertEqual(response.status_code, 400)
        self.assertEqual(sum(user["role"] == "student" for user in self.db.get_all_users()), 1)

    def test_reset_student_password_requires_csrf(self):
        self.login("demo_admin")
        student_id = self.db.get_user("demo_student")["id"]
        self.app.config["WTF_CSRF_ENABLED"] = True
        response = self.client.post(f"/admin/users/{student_id}/reset", data={
            "admin_password": "DemoPass!123", "password": "NewStudent!456",
            "confirm_password": "NewStudent!456",
        })
        self.assertEqual(response.status_code, 400)
        from auth import verify_password
        original = self.db.get_user("demo_student")
        self.assertTrue(verify_password("DemoPass!123", original["password_hash"], original["salt"]))

    def test_admin_can_disable_student_but_not_self(self):
        admin_id = self.db.get_user("demo_admin")["id"]
        student_id = self.db.get_user("demo_student")["id"]
        self.login("demo_student")
        self.assertEqual(self.client.post(f"/admin/users/{admin_id}/status", data={
            "active": "0",
        }).status_code, 403)
        self.client.get("/logout")
        self.login("demo_admin")
        self.client.post(f"/admin/users/{admin_id}/status", data={"active": "0"})
        self.assertIsNotNone(self.db.get_user("demo_admin"))
        self.client.post(f"/admin/users/{student_id}/status", data={"active": "0"})
        self.assertIsNone(self.db.get_user("demo_student"))
        self.client.get("/logout")
        self.assertEqual(self.client.post("/login", data={
            "username": "demo_student", "password": "DemoPass!123",
        }).status_code, 200)

    def test_role_dashboards_show_relevant_actions_and_activity(self):
        self.login("demo_student")
        student_page = self.client.get("/app").data
        self.assertIn(b"How intake works", student_page)
        self.assertNotIn(b"/admin/users/", student_page)
        self.client.post("/scan/in/add", data={"barcode": "IN-123", "shelf_id": self.shelf_id})
        cart = self.db.get_active_cart(self.db.get_user("demo_student")["id"], "IN")
        self.client.post("/scan/in/complete", data={"cart_id": cart["id"]})
        self.client.get("/logout")
        self.login("demo_admin")
        admin_page = self.client.get("/app").data
        self.assertIn(b"Recent intake", admin_page)
        self.assertIn(b"demo_student", admin_page)
        self.assertIn(b"/admin/users/", admin_page)

    def test_admin_sees_multiple_items_on_shelf_and_can_rename_layout(self):
        section_id = self.db.create_pantry_section("Section 3")
        shelf_id = self.db.create_pantry_shelf(section_id, "Shelf 1")
        self.db.create_item_on_shelf("VEGS", "Mixed vegetables", "Canned", 4, 0,
                                     shelf_id, "demo_admin")
        self.db.create_item_on_shelf("POTATO", "Potatoes", "Produce", 7, 0,
                                     shelf_id, "demo_admin")
        self.login("demo_admin")
        pantry = self.client.get("/pantry/").data
        self.assertIn(b"Mixed vegetables", pantry)
        self.assertIn(b"Potatoes", pantry)
        self.assertEqual(self.client.post(f"/pantry/sections/{section_id}/edit", data={
            "name": "Section 3 East",
        }).status_code, 302)
        self.assertEqual(self.client.post(f"/pantry/shelves/{shelf_id}/edit", data={
            "name": "Shelf 1A", "is_overflow": "on",
        }).status_code, 302)
        self.assertIn(b"Shelf 1A", self.client.get("/pantry/").data)
        self.client.get("/logout")
        self.login("demo_student")
        self.assertEqual(self.client.post(f"/pantry/sections/{section_id}/edit", data={
            "name": "Forged",
        }).status_code, 403)
        self.assertEqual(self.client.post(f"/pantry/shelves/{shelf_id}/edit", data={
            "name": "Forged",
        }).status_code, 403)

    def test_layout_edits_require_csrf(self):
        section_id = self.db.create_pantry_section("Section 3")
        shelf_id = self.db.create_pantry_shelf(section_id, "Shelf 1")
        self.login("demo_admin")
        self.app.config["WTF_CSRF_ENABLED"] = True
        self.assertEqual(self.client.post(f"/pantry/sections/{section_id}/edit", data={
            "name": "Changed",
        }).status_code, 400)
        self.assertEqual(self.client.post(f"/pantry/shelves/{shelf_id}/edit", data={
            "name": "Changed",
        }).status_code, 400)
        names = next(section for section in self.db.get_pantry_layout()
                     if section["id"] == section_id)
        self.assertEqual(names["name"], "Section 3")
        self.assertEqual(names["shelves"][0]["name"], "Shelf 1")

    def test_admin_creates_empty_shelf_and_student_is_denied(self):
        self.login("demo_admin")
        self.assertEqual(self.client.post("/pantry/sections", data={"name": "Dry goods"}).status_code, 302)
        section = next(row for row in self.db.get_pantry_layout() if row["name"] == "Dry goods")
        self.assertEqual(self.client.post("/pantry/shelves", data={
            "section_id": section["id"], "name": "Shelf A",
        }).status_code, 302)
        self.assertIn(b"Shelf A", self.client.get("/pantry/").data)
        self.client.get("/logout")
        self.login("demo_student")
        self.assertEqual(self.client.get("/pantry/").status_code, 403)
        self.assertEqual(self.client.post("/pantry/sections", data={"name": "No"}).status_code, 403)
        self.assertEqual(self.client.post("/pantry/shelves", data={
            "section_id": section["id"], "name": "No",
        }).status_code, 403)
        self.assertNotIn(b"/pantry/", self.client.get("/app").data)

    def test_scan_and_user_creation_require_csrf(self):
        self.login("demo_admin")
        self.app.config["WTF_CSRF_ENABLED"] = True
        self.assertEqual(self.client.post("/scan/in/add", data={
            "barcode": "IN-123", "shelf_id": self.shelf_id,
        }).status_code, 400)
        self.assertEqual(self.client.post("/admin/users/", data={"username": "new_student"}).status_code, 400)
        self.assertEqual(self.db.get_item_by_barcode("IN-123")["current_quantity"], 4)

    def test_login_rejects_external_next(self):
        response = self.client.post("/login?next=//untrusted.invalid", data={
            "username": "demo_student", "password": "DemoPass!123",
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/app")


if __name__ == "__main__":
    unittest.main()
