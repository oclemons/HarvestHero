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
        self.app.config["WTF_CSRF_ENABLED"] = False
        self.app.config["RATELIMIT_ENABLED"] = False
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

    def _adjust_data(self, quantity):
        from database import Database
        stock = Database().get_item_shelf_stock(self._row()["id"])[0]
        return {"quantity": quantity, "shelf_id": stock["shelf_id"],
                "expected_quantity": stock["quantity"], "reason": "Cycle count"}

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
                             data=self._adjust_data("42"),
                             follow_redirects=False)
        self.assertEqual(r.status_code, 302)
        self.assertEqual(self._qty(), 42)

    def test_negative_quantity_rejected(self):
        self._login()
        self.client.post(f"/inventory/{self._row()['id']}/adjust",
                         data=self._adjust_data("-5"))
        self.assertEqual(self._qty(), 10)  # unchanged

    def test_non_numeric_quantity_rejected(self):
        self._login()
        self.client.post(f"/inventory/{self._row()['id']}/adjust",
                         data=self._adjust_data("many"))
        self.assertEqual(self._qty(), 10)

    def test_same_value_is_a_noop(self):
        self._login()
        row = self._row()
        self.client.post(f"/inventory/{row['id']}/adjust",
                         data=self._adjust_data(str(self._qty())))
        self.assertEqual(self._qty(), 10)
        # An 'nothing changed' info flash appears on the detail redirect.
        body = self.client.get(f"/inventory/{row['id']}").data.decode("utf-8")
        self.assertIn("nothing changed", body)

    def test_zero_is_allowed(self):
        self._login()
        self.client.post(f"/inventory/{self._row()['id']}/adjust",
                         data=self._adjust_data("0"))
        self.assertEqual(self._qty(), 0)

    def test_stale_shelf_count_is_rejected(self):
        self._login()
        row = self._row()
        old_form = self._adjust_data("12")
        self.client.post(f"/inventory/{row['id']}/adjust", data=old_form)
        self.client.post(f"/inventory/{row['id']}/adjust", data=old_form)
        self.assertEqual(self._qty(), 12)

    def test_transfer_does_not_change_total(self):
        from database import Database
        db = Database()
        section_id = db.create_pantry_section("Dry goods")
        target = db.create_pantry_shelf(section_id, "Overflow", is_overflow=True)
        source = db.get_item_shelf_stock(self._row()["id"])[0]["shelf_id"]
        self._login()
        response = self.client.post(f"/inventory/{self._row()['id']}/transfer", data={
            "source_id": source, "destination_id": target, "quantity": "4",
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self._qty(), 10)
        stock = {entry["shelf_id"]: entry["quantity"] for entry in db.get_item_shelf_stock(self._row()["id"])}
        self.assertEqual(stock, {source: 6, target: 4})

    def test_detail_page_shows_adjust_form(self):
        self._login()
        body = self.client.get(f"/inventory/{self._row()['id']}").data.decode("utf-8")
        self.assertIn("count", body)
        self.assertIn("Correction reason", body)
        self.assertIn('name="quantity"', body)


if __name__ == "__main__":
    unittest.main()
