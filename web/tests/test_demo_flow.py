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
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(self.db.get_user("new_student"))
        self.assertNotIn(b"AnotherPass!123", response.data)

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
