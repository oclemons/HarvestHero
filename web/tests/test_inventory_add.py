"""Integration tests for GET/POST /inventory/new (Phase 1c-i)."""

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


class AddItem(unittest.TestCase):

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

        from app import create_app
        self.app = create_app()
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

    def tearDown(self):
        self._tmp.cleanup()

    def _login(self):
        return self.client.post(
            "/login",
            data={"username": "admin", "password": ADMIN_PW},
            follow_redirects=False,
        )

    # ─────────────────────────────────────────────────────────

    def test_get_requires_auth(self):
        r = self.client.get("/inventory/new")
        self.assertEqual(r.status_code, 302)
        self.assertIn("/login", r.headers["Location"])

    def test_get_renders_the_form(self):
        self._login()
        r = self.client.get("/inventory/new")
        self.assertEqual(r.status_code, 200)
        body = r.data.decode("utf-8")
        self.assertIn("Add a new item", body)
        self.assertIn('name="barcode"', body)
        self.assertIn('name="item_name"', body)

    def test_happy_path_creates_item(self):
        self._login()
        r = self.client.post("/inventory/new", data={
            "barcode": "ADD9001",
            "item_name": "Rice (long grain)",
            "brand": "Uncle Ben's",
            "category": "Grain",
            "current_quantity": "12",
            "minimum_stock": "5",
            "storage_location": "Section 3, Shelf A",
            "notes": "",
        }, follow_redirects=False)
        self.assertEqual(r.status_code, 302)  # -> detail

        from database import Database
        row = Database().get_item_by_barcode("ADD9001")
        self.assertIsNotNone(row)
        self.assertEqual(row["item_name"], "Rice (long grain)")
        self.assertEqual(int(row["current_quantity"]), 12)
        self.assertEqual(int(row["minimum_stock"]), 5)
        self.assertEqual(row["storage_location"], "Section 3, Shelf A")

    def test_missing_barcode_is_rejected(self):
        self._login()
        r = self.client.post("/inventory/new", data={
            "barcode": "",  # empty
            "item_name": "Nameless",
            "current_quantity": "1", "minimum_stock": "0",
        })
        self.assertEqual(r.status_code, 400)
        self.assertIn(b"Barcode is required", r.data)

    def test_missing_item_name_is_rejected(self):
        self._login()
        r = self.client.post("/inventory/new", data={
            "barcode": "BAD1",
            "item_name": "",
            "current_quantity": "1", "minimum_stock": "0",
        })
        self.assertEqual(r.status_code, 400)
        self.assertIn(b"Item name is required", r.data)

    def test_duplicate_barcode_is_rejected(self):
        # Pre-seed one item, then try to add another with the same barcode.
        from database import Database
        Database().add_item("DUPE1", "Existing", "Cat",
                            quantity=1, minimum_stock=0, notes="")

        self._login()
        r = self.client.post("/inventory/new", data={
            "barcode": "DUPE1",
            "item_name": "Trying to overwrite",
            "current_quantity": "1", "minimum_stock": "0",
        })
        self.assertEqual(r.status_code, 400)
        self.assertIn(b"already used", r.data)

    def test_non_numeric_quantity_is_rejected(self):
        self._login()
        r = self.client.post("/inventory/new", data={
            "barcode": "BAD2", "item_name": "Item",
            "current_quantity": "not a number",
            "minimum_stock": "0",
        })
        self.assertEqual(r.status_code, 400)
        self.assertIn(b"must be a whole number", r.data)


if __name__ == "__main__":
    unittest.main()
