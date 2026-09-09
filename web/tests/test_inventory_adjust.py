"""Integration tests for POST /inventory/<id>/adjust (Phase 1c-iv)."""

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


class AdjustQuantity(unittest.TestCase):

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
        db.add_item("ADJ1", "Some item", "Cat",
                    quantity=10, minimum_stock=0, notes="")

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
        return Database().get_item_by_barcode("ADJ1")

    def _qty(self):
        return int(self._row()["current_quantity"])

    # ─────────────────────────────────────────────────────────

    def test_requires_auth(self):
        r = self.client.post(f"/inventory/{self._row()['id']}/adjust",
                             data={"quantity": "99"},
                             follow_redirects=False)
        self.assertEqual(r.status_code, 302)
        self.assertIn("/login", r.headers["Location"])
        self.assertEqual(self._qty(), 10)

    def test_get_not_allowed(self):
        self._login()
        r = self.client.get(f"/inventory/{self._row()['id']}/adjust")
        self.assertEqual(r.status_code, 405)

    def test_404_for_unknown_id(self):
        self._login()
        r = self.client.post("/inventory/99999/adjust",
                             data={"quantity": "5"},
                             follow_redirects=False)
        self.assertEqual(r.status_code, 404)

    def test_happy_path_sets_new_quantity(self):
        self._login()
        row = self._row()
        r = self.client.post(f"/inventory/{row['id']}/adjust",
                             data={"quantity": "42"},
                             follow_redirects=False)
        self.assertEqual(r.status_code, 302)
        self.assertEqual(self._qty(), 42)

    def test_negative_quantity_rejected(self):
        self._login()
        self.client.post(f"/inventory/{self._row()['id']}/adjust",
                         data={"quantity": "-5"})
        self.assertEqual(self._qty(), 10)  # unchanged

    def test_non_numeric_quantity_rejected(self):
        self._login()
        self.client.post(f"/inventory/{self._row()['id']}/adjust",
                         data={"quantity": "many"})
        self.assertEqual(self._qty(), 10)

    def test_same_value_is_a_noop(self):
        self._login()
        row = self._row()
        self.client.post(f"/inventory/{row['id']}/adjust",
                         data={"quantity": str(self._qty())})
        self.assertEqual(self._qty(), 10)
        # An 'nothing changed' info flash appears on the detail redirect.
        body = self.client.get(f"/inventory/{row['id']}").data.decode("utf-8")
        self.assertIn("nothing changed", body)

    def test_zero_is_allowed(self):
        self._login()
        self.client.post(f"/inventory/{self._row()['id']}/adjust",
                         data={"quantity": "0"})
        self.assertEqual(self._qty(), 0)

    def test_detail_page_shows_adjust_form(self):
        self._login()
        body = self.client.get(f"/inventory/{self._row()['id']}").data.decode("utf-8")
        self.assertIn("Set quantity to", body)
        self.assertIn('name="quantity"', body)


if __name__ == "__main__":
    unittest.main()
