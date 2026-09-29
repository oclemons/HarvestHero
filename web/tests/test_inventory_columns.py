"""Inventory sort order and per-Admin column layout stay safe and persistent."""

import html
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


class InventoryColumns(unittest.TestCase):
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
        for name, role in (("admin", "admin"), ("helper", "student")):
            hashed, salt = hash_password("PantryPass!123")
            self.db.create_user(name, hashed, salt, role)
        section = self.db.create_pantry_section("Section 3")
        first = self.db.create_pantry_shelf(section, "Shelf 1")
        second_section = self.db.create_pantry_section("Section 2")
        second = self.db.create_pantry_shelf(second_section, "Shelf 2")
        self.db.create_item_on_shelf("B1", "banana", "Fruit", 2, 0, first, "admin")
        self.db.create_item_on_shelf("A1", "Apple", "Fruit", 3, 0, second, "admin")
        self.db.create_item_on_shelf("C1", "carrot", "Vegetables", 1, 0, first, "admin")
        from app import create_app
        self.app = create_app()
        self.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False, RATELIMIT_ENABLED=False)
        self.client = self.app.test_client()

    def tearDown(self):
        self.tmp.cleanup()

    def login(self, name):
        self.client.post("/login", data={"username": name, "password": "PantryPass!123"})

    def names(self, url="/inventory/"):
        html = self.client.get(url).get_data(as_text=True)
        return re.findall(r'href="/inventory/\d+"[^>]*>\s*([^<]+)</a>', html)

    def test_default_alphabetical_and_header_sorts(self):
        self.login("admin")
        self.assertEqual(self.names(), ["Apple", "banana", "carrot"])
        self.assertEqual(self.names("/inventory/?sort=item&direction=desc"),
                         ["carrot", "banana", "Apple"])
        self.assertEqual(self.names("/inventory/?sort=quantity&direction=asc"),
                         ["carrot", "banana", "Apple"])
        self.assertEqual(self.names("/inventory/?sort=location&direction=asc"),
                         ["Apple", "banana", "carrot"])
        self.assertEqual(self.names("/inventory/?sort=not-a-column&direction=desc"),
                         ["Apple", "banana", "carrot"])

    def test_admin_can_hide_and_order_columns_without_changing_student_view(self):
        self.login("admin")
        response = self.client.post("/inventory/columns", data={
            "visible": ["item", "quantity", "barcode"],
            "position_item": "2", "position_quantity": "1", "position_barcode": "3",
        })
        self.assertEqual(response.status_code, 302)
        body = self.client.get("/inventory/").get_data(as_text=True)
        headings = re.findall(r"<th[^>]*>(.*?)</th>", body, flags=re.S)
        self.assertEqual(len(headings), 3)
        self.assertIn("Qty", headings[0])
        self.assertIn("Item", headings[1])
        self.assertIn("Barcode", headings[2])
        self.client.get("/logout")
        self.login("admin")
        self.assertEqual(self.db.get_inventory_columns(self.db.get_user("admin")["id"]),
                         ["quantity", "item", "barcode"])
        self.client.get("/logout")
        from auth import hash_password
        hashed, salt = hash_password("PantryPass!123")
        self.db.create_user("other_admin", hashed, salt, "admin")
        self.login("other_admin")
        self.assertEqual(self.db.get_inventory_columns(self.db.get_user("other_admin")["id"]),
                         ["barcode", "item", "category", "quantity", "minimum", "location"])
        self.client.get("/logout")
        self.login("helper")
        student_page = self.client.get("/inventory/").data
        self.assertIn(b"Category", student_page)
        self.assertIn(b"Location", student_page)
        self.assertEqual(self.client.post("/inventory/columns", data={
            "visible": ["item"], "position_item": "1",
        }).status_code, 403)

    def test_search_and_pagination_preserve_sort_direction(self):
        section = self.db.create_pantry_section("Section 5")
        shelf = self.db.create_pantry_shelf(section, "Shelf 2")
        for index in range(27):
            self.db.create_item_on_shelf(f"E{index:03d}", f"Extra {index:02d}", "Other",
                                         index, 0, shelf, "admin")
        self.login("admin")
        body = html.unescape(self.client.get(
            "/inventory/?q=Extra&sort=quantity&direction=desc"
        ).get_data(as_text=True))
        self.assertIn("q=Extra&sort=quantity&direction=desc&page=2", body)
        self.assertIn('name="sort" value="quantity"', body)
        self.assertIn('name="direction" value="desc"', body)

    def test_column_layout_post_requires_csrf(self):
        self.login("admin")
        self.app.config["WTF_CSRF_ENABLED"] = True
        response = self.client.post("/inventory/columns", data={
            "visible": ["item", "quantity"], "position_item": "2", "position_quantity": "1",
        })
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.db.get_inventory_columns(self.db.get_user("admin")["id"]),
                         ["barcode", "item", "category", "quantity", "minimum", "location"])

    def test_invalid_sort_or_column_keys_never_become_sql(self):
        self.login("admin")
        response = self.client.post("/inventory/columns", data={
            "visible": ["item", "password_hash"], "position_item": "1",
            "position_password_hash": "2",
        })
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.db.get_inventory_columns(self.db.get_user("admin")["id"]),
                         ["barcode", "item", "category", "quantity", "minimum", "location"])


if __name__ == "__main__":
    unittest.main()
