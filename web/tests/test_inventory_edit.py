"""Integration tests for GET/POST /inventory/<id>/edit (Phase 1c-ii)."""

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


PW = "AdminPass!123"


class EditItem(unittest.TestCase):

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
        ph, salt = hash_password(PW); db.create_user("admin", ph, salt, "admin")
        db.add_item("EDIT1", "Original name", "OldCat",
                    quantity=5, minimum_stock=2, notes="original",
                    brand="OldBrand", storage_location="Section 1, Shelf A")

        from app import create_app
        self.app = create_app()
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

    def tearDown(self):
        self._tmp.cleanup()

    def _login(self):
        return self.client.post(
            "/login", data={"username": "admin", "password": PW},
            follow_redirects=False,
        )

    def _row(self):
        from database import Database
        return Database().get_item_by_barcode("EDIT1")

    # ─────────────────────────────────────────────────────────

    def test_get_requires_auth(self):
        r = self.client.get(f"/inventory/{self._row()['id']}/edit")
        self.assertEqual(r.status_code, 302)
        self.assertIn("/login", r.headers["Location"])

    def test_get_renders_form_prefilled(self):
        self._login()
        r = self.client.get(f"/inventory/{self._row()['id']}/edit")
        self.assertEqual(r.status_code, 200)
        body = r.data.decode("utf-8")
        self.assertIn("Edit item", body)
        self.assertIn('value="Original name"', body)
        self.assertIn('value="OldBrand"',      body)
        # Barcode field is read-only in edit mode
        self.assertIn("readonly", body)

    def test_edit_404_for_unknown_id(self):
        self._login()
        r = self.client.get("/inventory/99999/edit")
        self.assertEqual(r.status_code, 404)

    def test_happy_path_updates_all_fields(self):
        self._login()
        row = self._row()
        r = self.client.post(f"/inventory/{row['id']}/edit", data={
            "barcode": "EDIT1",   # readonly on the form; ignored server-side
            "item_name": "Renamed item",
            "brand": "NewBrand",
            "category": "NewCat",
            "current_quantity": "9",
            "minimum_stock": "4",
            "storage_location": "Section 9, Shelf Z",
            "notes": "edited",
        }, follow_redirects=False)
        self.assertEqual(r.status_code, 302)

        new_row = self._row()
        self.assertEqual(new_row["item_name"],        "Renamed item")
        self.assertEqual(new_row["brand"],            "NewBrand")
        self.assertEqual(new_row["category"],         "NewCat")
        self.assertEqual(int(new_row["current_quantity"]), 9)
        self.assertEqual(int(new_row["minimum_stock"]),    4)
        self.assertEqual(new_row["storage_location"], "Section 9, Shelf Z")
        self.assertEqual(new_row["notes"],            "edited")
        # Barcode still the original — client can't rewrite it.
        self.assertEqual(new_row["barcode"], "EDIT1")

    def test_missing_item_name_rejected(self):
        self._login()
        row = self._row()
        r = self.client.post(f"/inventory/{row['id']}/edit", data={
            "barcode": "EDIT1",
            "item_name": "",   # blanked
            "current_quantity": "5", "minimum_stock": "0",
        })
        self.assertEqual(r.status_code, 400)
        self.assertIn(b"Item name is required", r.data)
        # Item on disk is unchanged.
        self.assertEqual(self._row()["item_name"], "Original name")

    def test_client_cannot_rewrite_barcode_on_post(self):
        """Even if a malicious client submits a different barcode field,
        the server keeps the original."""
        self._login()
        row = self._row()
        self.client.post(f"/inventory/{row['id']}/edit", data={
            "barcode": "HAX9999",
            "item_name": "Renamed",
            "current_quantity": "5", "minimum_stock": "0",
        }, follow_redirects=False)
        self.assertEqual(self._row()["barcode"], "EDIT1")

    def test_detail_page_shows_edit_button(self):
        self._login()
        row = self._row()
        body = self.client.get(f"/inventory/{row['id']}").data.decode("utf-8")
        self.assertIn("Edit item", body)


if __name__ == "__main__":
    unittest.main()
