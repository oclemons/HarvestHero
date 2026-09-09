"""Integration tests for POST /inventory/<id>/delete (Phase 1c-iii)."""

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


class DeleteItem(unittest.TestCase):

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
        db.add_item("DEL1", "Doomed item", "Cat",
                    quantity=3, minimum_stock=0, notes="")

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
        return Database().get_item_by_barcode("DEL1")

    # ─────────────────────────────────────────────────────────

    def test_delete_requires_auth(self):
        r = self.client.post(f"/inventory/{self._row()['id']}/delete",
                             follow_redirects=False)
        self.assertEqual(r.status_code, 302)
        self.assertIn("/login", r.headers["Location"])
        # Item still there because auth blocked it.
        self.assertIsNotNone(self._row())

    def test_get_not_allowed(self):
        """POST-only route — GET should not delete."""
        self._login()
        r = self.client.get(f"/inventory/{self._row()['id']}/delete")
        self.assertEqual(r.status_code, 405)
        # Item still on disk.
        self.assertIsNotNone(self._row())

    def test_delete_404_for_unknown_id(self):
        self._login()
        r = self.client.post("/inventory/99999/delete",
                             follow_redirects=False)
        self.assertEqual(r.status_code, 404)

    def test_happy_path_removes_row_and_redirects_to_list(self):
        self._login()
        row = self._row()
        r = self.client.post(f"/inventory/{row['id']}/delete",
                             follow_redirects=False)
        self.assertEqual(r.status_code, 302)
        self.assertIn("/inventory", r.headers["Location"])

        # Row gone.
        from database import Database
        self.assertIsNone(Database().get_item_by_id(row["id"]))

        # Flash message shows on the redirect target. The single quotes
        # around the item name get HTML-escaped to &#39; by Jinja, so
        # we look for the two ends of the phrase separately.
        body = self.client.get(r.headers["Location"]).data.decode("utf-8")
        self.assertIn("Deleted",      body)
        self.assertIn("Doomed item",  body)

    def test_detail_page_shows_delete_button_with_confirm(self):
        self._login()
        body = self.client.get(f"/inventory/{self._row()['id']}").data.decode("utf-8")
        self.assertIn("Delete item", body)
        # Confirm() call embedded so a bare click can't destroy the row.
        self.assertIn("This cannot be undone", body)


if __name__ == "__main__":
    unittest.main()
