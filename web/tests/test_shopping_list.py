"""Shopping list is populated by distribution and cleared by intake."""

from __future__ import annotations

import datetime
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
WEB = os.path.join(ROOT, "web")
for location in (ROOT, WEB):
    if location not in sys.path:
        sys.path.insert(0, location)


PW = "AdminPass!123"


class ShoppingList(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        os.environ["HARVESTHERO_DEV_DIR"] = self._tmp.name
        os.environ["HARVESTHERO_SECRET_KEY"] = "test-secret-abcdefghijklmnop"
        os.environ["HARVESTHERO_COOKIE_SECURE"] = "0"
        for mod in ("paths", "database", "auth", "app", "extensions",
                    "routes.auth", "routes.dashboard", "routes.account",
                    "routes.inventory", "routes.scan", "routes.clients"):
            sys.modules.pop(mod, None)
        from database import Database
        from auth import hash_password
        self.db = Database()
        ph, salt = hash_password(PW)
        self.db.create_user("admin", ph, salt, "admin")
        self.admin_id = self.db.get_user("admin")["id"]
        self.client_id = self.db.create_pantry_client(
            first_name="Test", last_name="Client", student_id="S123",
            email="", phone="", semester="Fall 2026",
            enrollment_status="full_time",
        )
        conn = self.db._connect()
        conn.execute(
            "UPDATE pantry_clients SET birth_date = ?, expected_graduation_semester = ? "
            "WHERE id = ?",
            ("2000-01-01", "Spring 2028", self.client_id),
        )
        conn.commit()
        conn.close()
        verified_until = (datetime.date.today() + datetime.timedelta(days=30)).isoformat()
        self.db.verify_client_term(self.client_id, "Fall 2026",
                                   verified_until, "admin")
        section = self.db.create_pantry_section("Dry goods")
        self.shelf_id = self.db.create_pantry_shelf(section, "Shelf A")
        self.low_id = self.db.create_item_on_shelf("LOW1", "Low item", "Dry", 2, 3,
                                                   self.shelf_id, "admin")
        self.out_id = self.db.create_item_on_shelf("OUT1", "Out item", "Dry", 1, 0,
                                                   self.shelf_id, "admin")
        self.low_barcode_out = self.db.get_item_by_id(self.low_id)["barcode_out"]
        self.out_barcode_out = self.db.get_item_by_id(self.out_id)["barcode_out"]
        from app import create_app
        self.app = create_app()
        self.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False,
                               RATELIMIT_ENABLED=False)
        self.client = self.app.test_client()

    def tearDown(self):
        self._tmp.cleanup()

    def _login(self):
        return self.client.post("/login", data={"username": "admin", "password": PW})

    def test_distribution_adds_item_when_below_minimum(self):
        self.db.start_scan_out_cart(self.admin_id, self.client_id, mode="IMMEDIATE",
                                    fulfillment_type="in_person")
        self.db.record_immediate_scan_out(self.admin_id, self.low_barcode_out,
                                          self.shelf_id, "admin", "token-low-1")
        items = self.db.get_shopping_list()
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["barcode"], "LOW1")
        self.assertEqual(items[0]["quantity_needed"], 2)

    def test_distribution_adds_item_when_out_of_stock(self):
        self.db.start_scan_out_cart(self.admin_id, self.client_id, mode="IMMEDIATE",
                                    fulfillment_type="in_person")
        self.db.record_immediate_scan_out(self.admin_id, self.out_barcode_out,
                                          self.shelf_id, "admin", "token-out-1")
        items = self.db.get_shopping_list()
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["barcode"], "OUT1")
        self.assertEqual(items[0]["quantity_needed"], 1)

    def test_intake_clears_shopping_list(self):
        self.db.add_scan_to_cart(self.admin_id, "LOW1", self.shelf_id, "admin")
        self.db.add_scan_to_cart(self.admin_id, "LOW1", self.shelf_id, "admin")
        cart = self.db.get_active_cart(self.admin_id, "IN")
        self.db.complete_scan_in_cart(self.admin_id, cart["id"], "admin")
        self.assertEqual(self.db.get_shopping_list(), [])

    def test_shopping_list_page_requires_admin(self):
        from auth import hash_password
        ph, salt = hash_password("StudentPass!123")
        self.db.create_user("student", ph, salt, "student")
        self.client.post("/login", data={"username": "student", "password": "StudentPass!123"})
        self.assertEqual(self.client.get("/inventory/shopping-list").status_code, 403)

    def test_shopping_list_page_shows_items(self):
        self._login()
        self.db.start_scan_out_cart(self.admin_id, self.client_id, mode="IMMEDIATE",
                                    fulfillment_type="in_person")
        self.db.record_immediate_scan_out(self.admin_id, self.low_barcode_out,
                                          self.shelf_id, "admin", "token-low-2")
        body = self.client.get("/inventory/shopping-list").data.decode("utf-8")
        self.assertIn("Low item", body)
        self.assertIn("LOW1", body)


if __name__ == "__main__":
    unittest.main()
