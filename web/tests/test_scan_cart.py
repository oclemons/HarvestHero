"""Cart review, atomic intake, role isolation and weight provenance."""

import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WEB = ROOT / "web"
for location in (str(ROOT), str(WEB)):
    if location not in sys.path:
        sys.path.insert(0, location)


class ScanCart(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["HARVESTHERO_DEV_DIR"] = self.tmp.name
        os.environ["HARVESTHERO_SECRET_KEY"] = "test-secret-abcdefghijklmnop"
        os.environ["HARVESTHERO_COOKIE_SECURE"] = "0"
        for name in ("paths", "database", "auth", "app", "extensions", "security",
                     "errors", "logging_config", "decorators", "routes.auth", "routes.dashboard",
                     "routes.account", "routes.inventory", "routes.scan", "routes.sections",
                     "routes.users"):
            sys.modules.pop(name, None)
        from auth import hash_password
        from database import Database
        self.db = Database()
        for name, role in (("student_a", "student"), ("student_b", "student"), ("admin_a", "admin")):
            hashed, salt = hash_password("PantryPass!123")
            self.db.create_user(name, hashed, salt, role)
        self.student_id = self.db.get_user("student_a")["id"]
        self.admin_id = self.db.get_user("admin_a")["id"]
        section = self.db.create_pantry_section("Dry goods")
        self.shelf_id = self.db.create_pantry_shelf(section, "Shelf 1")
        self.item_id = self.db.create_item_on_shelf(
            "RICE1", "Rice", "Dry", 3, 2, self.shelf_id, "admin_a", 625
        )
        self.unknown_id = self.db.create_item_on_shelf(
            "BEANS1", "Beans", "Dry", 1, 0, self.shelf_id, "admin_a"
        )
        from app import create_app
        self.app = create_app()
        self.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False, RATELIMIT_ENABLED=False)
        self.client = self.app.test_client()

    def tearDown(self):
        self.tmp.cleanup()

    def login(self, name):
        self.client.post("/login", data={"username": name, "password": "PantryPass!123"})

    def test_two_scans_stay_in_cart_until_checkout_and_complete_once(self):
        self.login("student_a")
        for _ in range(2):
            self.assertEqual(self.client.post("/scan/in/add", data={
                "barcode": "RICE1", "shelf_id": self.shelf_id,
            }).status_code, 302)
        self.assertEqual(self.db.get_item_by_id(self.item_id)["current_quantity"], 3)
        page = self.client.get("/scan/in").data
        self.assertIn(b"Rice", page)
        self.assertIn(b"2 units", page)
        self.assertIn(f'value="{self.shelf_id}" selected'.encode(), page)
        cart = self.db.get_active_cart(self.student_id, "IN")
        response = self.client.post("/scan/in/complete", data={"cart_id": cart["id"]})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.db.get_item_by_id(self.item_id)["current_quantity"], 5)
        self.assertEqual(self.db.get_item_shelf_stock(self.item_id)[0]["quantity"], 5)
        receipt = self.db.complete_scan_in_cart(self.student_id, cart["id"], "student_a")
        self.assertEqual(receipt["known_weight_milli_lb"], 1250)
        self.assertEqual(self.db.get_item_by_id(self.item_id)["current_quantity"], 5)
        self.assertIn(b"Rice", self.client.get(response.headers["Location"]).data)

    def test_pending_weight_is_not_recorded_as_zero(self):
        self.db.add_scan_to_cart(self.student_id, "BEANS1", self.shelf_id)
        cart = self.db.get_active_cart(self.student_id, "IN")
        receipt = self.db.complete_scan_in_cart(self.student_id, cart["id"], "student_a")
        self.assertEqual(receipt["pending_lines"], 1)
        conn = self.db._connect()
        weight = conn.execute(
            "SELECT weight_milli_lb FROM inventory_movements WHERE cart_id = ?", (cart["id"],)
        ).fetchone()[0]
        conn.close()
        self.assertIsNone(weight)

    def test_all_or_nothing_on_checkout_failure(self):
        self.db.add_scan_to_cart(self.student_id, "RICE1", self.shelf_id)
        self.db.add_scan_to_cart(self.student_id, "BEANS1", self.shelf_id)
        cart = self.db.get_active_cart(self.student_id, "IN")
        conn = self.db._connect()
        conn.execute("CREATE TRIGGER fail_movement BEFORE INSERT ON inventory_movements "
                     "WHEN NEW.item_id = {} BEGIN SELECT RAISE(ABORT, 'failure'); END".format(self.unknown_id))
        conn.commit()
        conn.close()
        with self.assertRaises(Exception):
            self.db.complete_scan_in_cart(self.student_id, cart["id"], "student_a")
        self.assertEqual(self.db.get_item_by_id(self.item_id)["current_quantity"], 3)
        self.assertEqual(self.db.get_item_by_id(self.unknown_id)["current_quantity"], 1)
        self.assertEqual(self.db.get_active_cart(self.student_id, "IN")["id"], cart["id"])

    def test_student_cannot_override_weight_or_view_other_cart(self):
        self.login("student_a")
        self.client.post("/scan/in/add", data={"barcode": "RICE1", "shelf_id": self.shelf_id,
                                                 "weight_override_milli_lb": 9999})
        cart = self.db.get_active_cart(self.student_id, "IN")
        self.assertIsNone(cart["lines"][0]["weight_override_milli_lb"])
        self.assertEqual(self.client.post(f"/scan/in/weight/{cart['lines'][0]['id']}", data={
            "measured_lb": "9.999", "reason": "Forged",
        }).status_code, 403)
        self.client.post("/scan/in/complete", data={"cart_id": cart["id"]})
        self.client.get("/logout")
        self.login("student_b")
        self.assertEqual(self.client.get(f"/scan/in/receipt/{cart['id']}").status_code, 404)
        self.client.post("/scan/in/complete", data={"cart_id": cart["id"]})
        self.assertEqual(self.db.get_item_by_id(self.item_id)["current_quantity"], 4)

    def test_admin_can_measure_cart_line_with_reason(self):
        self.login("admin_a")
        self.client.post("/scan/in/add", data={"barcode": "RICE1", "shelf_id": self.shelf_id})
        cart = self.db.get_active_cart(self.admin_id, "IN")
        response = self.client.post(f"/scan/in/weight/{cart['lines'][0]['id']}", data={
            "measured_lb": "0.750", "reason": "Scale reading",
        })
        self.assertEqual(response.status_code, 302)
        receipt = self.db.complete_scan_in_cart(self.admin_id, cart["id"], "admin_a")
        self.assertEqual(receipt["known_weight_milli_lb"], 750)
        conn = self.db._connect()
        reason = conn.execute(
            "SELECT weight_override_reason FROM inventory_movements WHERE cart_id = ?",
            (cart["id"],),
        ).fetchone()[0]
        conn.close()
        self.assertEqual(reason, "Scale reading")

    def test_cart_post_requires_csrf(self):
        self.login("student_a")
        self.app.config["WTF_CSRF_ENABLED"] = True
        self.assertEqual(self.client.post("/scan/in/add", data={
            "barcode": "RICE1", "shelf_id": self.shelf_id,
        }).status_code, 400)
        self.assertIsNone(self.db.get_active_cart(self.student_id, "IN"))


if __name__ == "__main__":
    unittest.main()
