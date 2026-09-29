"""Generated pantry Code 128 identifiers and Admin-only printable labels."""

import os
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WEB = ROOT / "web"
for location in (str(ROOT), str(WEB)):
    if location not in sys.path:
        sys.path.insert(0, location)


class BarcodeLabels(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["HARVESTHERO_DEV_DIR"] = self.tmp.name
        os.environ["HARVESTHERO_SECRET_KEY"] = "test-secret-abcdefghijklmnop"
        os.environ["HARVESTHERO_COOKIE_SECURE"] = "0"
        for name in ("paths", "database", "auth", "app", "extensions", "security",
                     "errors", "logging_config", "decorators", "routes.auth", "routes.dashboard",
                     "routes.account", "routes.inventory", "routes.scan", "routes.sections",
                     "routes.users", "routes.clients", "routes.reports"):
            sys.modules.pop(name, None)
        from auth import hash_password
        from database import Database
        self.db = Database()
        for username, role in (("admin", "admin"), ("helper", "student")):
            hashed, salt = hash_password("PantryPass!123")
            self.db.create_user(username, hashed, salt, role)
        section = self.db.create_pantry_section("Dry food")
        self.shelf_id = self.db.create_pantry_shelf(section, "Shelf A")
        from app import create_app
        self.app = create_app()
        self.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False, RATELIMIT_ENABLED=False)
        self.client = self.app.test_client()

    def tearDown(self):
        self.tmp.cleanup()

    def login(self, username):
        self.client.post("/login", data={"username": username, "password": "PantryPass!123"})

    def test_item_without_barcodes_gets_distinct_pantry_pair_and_printable_labels(self):
        self.login("admin")
        response = self.client.post("/inventory/new", data={
            "item_name": "Canned corn", "category": "Canned",
            "shelf_id": self.shelf_id, "current_quantity": "0", "minimum_stock": "1",
        })
        self.assertEqual(response.status_code, 302)
        item = self.db.get_all_items()[0]
        self.assertRegex(item["barcode"], r"^HHI-[0-9A-F]{16}$")
        self.assertEqual(item["barcode_out"], item["barcode"].replace("HHI-", "HHO-"))
        self.assertNotEqual(item["barcode"], item["barcode_out"])
        self.client.post("/scan/in/add", data={"barcode": item["barcode"], "shelf_id": self.shelf_id})
        cart = self.db.get_active_cart(self.db.get_user("admin")["id"], "IN")
        self.assertEqual(cart["lines"][0]["item_id"], item["id"])
        rejected = self.client.post("/scan/in/add", data={
            "barcode": item["barcode_out"], "shelf_id": self.shelf_id,
        }, follow_redirects=True)
        self.assertIn(b"barcode is for scan-out", rejected.data)
        page = self.client.get(f"/inventory/{item['id']}/labels")
        self.assertEqual(page.status_code, 200)
        self.assertIn(item["barcode"].encode(), page.data)
        self.assertIn(item["barcode_out"].encode(), page.data)
        for direction in ("in", "out"):
            image = self.client.get(f"/inventory/{item['id']}/barcode/{direction}.svg")
            self.assertEqual(image.status_code, 200)
            self.assertIn(b"<svg", image.data)
            self.assertTrue(image.mimetype.startswith("image/svg+xml"))
        self.client.get("/logout")
        self.login("helper")
        self.assertEqual(self.client.get(f"/inventory/{item['id']}/labels").status_code, 403)
        self.assertEqual(self.client.get(f"/inventory/{item['id']}/barcode/out.svg").status_code, 403)

    def test_admin_supplied_in_code_gets_generated_out_code(self):
        self.login("admin")
        response = self.client.post("/inventory/new", data={
            "barcode": "123456789012", "item_name": "Pasta", "shelf_id": self.shelf_id,
            "current_quantity": "0", "minimum_stock": "0",
        })
        self.assertEqual(response.status_code, 302)
        item = self.db.get_item_by_barcode("123456789012")
        self.assertRegex(item["barcode_out"], r"^HHO-[0-9A-F]{16}$")
        self.assertNotEqual(item["barcode_out"], item["barcode"])

    def test_each_new_item_has_unique_codes(self):
        first = self.db.create_item_on_shelf("", "Rice", "Dry", 0, 0, self.shelf_id, "admin")
        second = self.db.create_item_on_shelf("", "Beans", "Dry", 0, 0, self.shelf_id, "admin")
        self.assertNotEqual(self.db.get_item_by_id(first)["barcode"],
                            self.db.get_item_by_id(second)["barcode"])
        self.assertNotEqual(self.db.get_item_by_id(first)["barcode_out"],
                            self.db.get_item_by_id(second)["barcode_out"])


if __name__ == "__main__":
    unittest.main()
