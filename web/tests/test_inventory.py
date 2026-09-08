"""Integration tests for the inventory list + detail routes."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_WEB  = os.path.dirname(_HERE)
_ROOT = os.path.dirname(_WEB)
for p in (_ROOT, _WEB):
    if p not in sys.path:
        sys.path.insert(0, p)


ADMIN_PW = "AdminPass!123"


class InventoryRoutes(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        os.environ["HARVESTHERO_DEV_DIR"] = self._tmp.name
        os.environ["HARVESTHERO_SECRET_KEY"] = "test-secret-abcdefghijklmnop"
        os.environ["HARVESTHERO_COOKIE_SECURE"] = "0"

        for mod in ("paths", "database", "auth", "app", "extensions",
                    "routes.auth", "routes.dashboard",
                    "routes.account", "routes.inventory"):
            sys.modules.pop(mod, None)

        from database import Database
        from auth import hash_password
        db = Database()
        ph, salt = hash_password(ADMIN_PW)
        db.create_user("admin", ph, salt, "admin")

        # Seed a handful of items to exercise search + pagination + low-stock.
        # add_item signature: barcode, item_name, category, quantity,
        #                     minimum_stock, notes, barcode_out="",
        #                     brand="", storage_location="", ...
        db.add_item("1000", "Peanut butter", "Pantry",
                    quantity=12, minimum_stock=5, notes="",
                    brand="Skippy", storage_location="Section 1, Shelf A")
        db.add_item("1001", "Canned corn", "Canned",
                    quantity=2, minimum_stock=6, notes="",
                    brand="Del Monte", storage_location="Section 2, Shelf B")
        db.add_item("1002", "Cereal", "Breakfast",
                    quantity=8, minimum_stock=0, notes="",
                    brand="Cheerios", storage_location="Section 1, Shelf C")

        from app import create_app
        self.app = create_app()
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

    def tearDown(self):
        self._tmp.cleanup()

    # ------------------------------------------------------------------
    def _login(self):
        return self.client.post(
            "/login",
            data={"username": "admin", "password": ADMIN_PW},
            follow_redirects=False,
        )

    # ------------------------------------------------------------------
    def test_list_requires_auth(self):
        r = self.client.get("/inventory/")
        self.assertEqual(r.status_code, 302)
        self.assertIn("/login", r.headers["Location"])

    def test_list_shows_all_seeded_items(self):
        self._login()
        body = self.client.get("/inventory/").data.decode("utf-8")
        self.assertIn("Peanut butter", body)
        self.assertIn("Canned corn",   body)
        self.assertIn("Cereal",        body)
        # Count + label rendered across a <span>, so match with a regex.
        self.assertRegex(body, r">\s*3\s*<[^>]+>\s*items? tracked")

    def test_list_search_filters_results(self):
        self._login()
        body = self.client.get("/inventory/?q=corn").data.decode("utf-8")
        self.assertIn("Canned corn", body)
        self.assertNotIn("Peanut butter", body)
        self.assertNotIn("Cereal", body)

    def test_low_stock_item_gets_low_badge(self):
        """Canned corn: quantity=2, min=6 -> should render the LOW badge."""
        self._login()
        body = self.client.get("/inventory/").data.decode("utf-8")
        # The row containing Canned corn should also contain the badge.
        self.assertRegex(body, r"Canned corn(?:.|\n)*?Low")

    def test_detail_page_shows_every_field(self):
        self._login()

        # Find the seeded item's id.
        from database import Database
        db = Database()
        item = next(i for i in db.get_all_items() if i["item_name"] == "Peanut butter")

        body = self.client.get(f"/inventory/{item['id']}").data.decode("utf-8")
        self.assertIn("Peanut butter",         body)
        self.assertIn("Skippy",                 body)
        self.assertIn("Section 1, Shelf A",     body)
        self.assertIn("Pantry",                 body)
        # Not-low: badge should NOT appear
        self.assertNotIn("Low stock", body)

    def test_detail_404_for_missing_item(self):
        self._login()
        r = self.client.get("/inventory/99999")
        self.assertEqual(r.status_code, 404)

    def test_pagination_kicks_in_over_25_items(self):
        """Page size is 25; seed a 26th item and confirm two pages exist."""
        from database import Database
        db = Database()
        for i in range(30):
            db.add_item(f"P{i:04d}", f"PadItem{i:03d}", "Filler",
                        quantity=1, minimum_stock=0, notes="")

        self._login()
        body_p1 = self.client.get("/inventory/").data.decode("utf-8")
        self.assertIn("Page 1 of",   body_p1)
        self.assertIn("PadItem000",  body_p1)

        body_p2 = self.client.get("/inventory/?page=2").data.decode("utf-8")
        self.assertIn("Page 2 of",   body_p2)
        # PadItem000 is on page 1 (alphabetical); should NOT appear on page 2.
        self.assertNotIn("PadItem000", body_p2)


if __name__ == "__main__":
    unittest.main()
