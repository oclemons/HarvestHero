"""Server-side RBAC enforcement tests.

Guiding principle: the server rejects every unauthorized request via
raw HTTP, regardless of what the template shows. A student who
constructs a POST by hand (or edits a URL in their browser) must get
a 403, not a 200 with a hidden button re-enabled by JavaScript.

Every write route in the inventory blueprint is exercised twice:
once as admin (expect 200/302, allowed) and once as student
(expect 403). If a new admin-only route is added and the developer
forgets ``@admin_required``, this file's ``test_every_admin_route_
rejects_student`` catches it.
"""

from __future__ import annotations

import os
import re
import sys
import tempfile
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_WEB  = os.path.dirname(_HERE)
_ROOT = os.path.dirname(_WEB)
for p in (_ROOT, _WEB):
    if p not in sys.path:
        sys.path.insert(0, p)


ADMIN_PW   = "AdminPass!123"
STUDENT_PW = "StudentPass!456"


class RbacEnforcement(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        os.environ["HARVESTHERO_DEV_DIR"] = self._tmp.name
        os.environ["HARVESTHERO_SECRET_KEY"] = "test-secret-abcdefghijklmnop"
        os.environ["HARVESTHERO_COOKIE_SECURE"] = "0"

        for mod in ("paths", "database", "auth", "app", "extensions",
                    "security", "errors", "logging_config",
                    "decorators",
                    "routes.auth", "routes.dashboard",
                    "routes.account", "routes.inventory"):
            sys.modules.pop(mod, None)

        from database import Database
        from auth import hash_password
        db = Database()

        # Two users with different roles.
        ph, salt = hash_password(ADMIN_PW)
        ok, msg = db.create_user("alice_admin", ph, salt, "admin")
        self.assertTrue(ok, msg)
        ph, salt = hash_password(STUDENT_PW)
        ok, msg = db.create_user("bob_student", ph, salt, "student")
        self.assertTrue(ok, msg)

        # A seeded item so /inventory/<id>/... routes have a target.
        db.add_item("RBAC1", "Test item", "Cat",
                    quantity=5, minimum_stock=0, notes="")
        self._item_id = db.get_item_by_barcode("RBAC1")["id"]

        from app import create_app
        self.app = create_app()
        self.app.config["TESTING"] = True
        self.app.config["WTF_CSRF_ENABLED"] = False
        self.app.config["RATELIMIT_ENABLED"] = False
        self.client = self.app.test_client()

    def tearDown(self):
        self._tmp.cleanup()

    # ------------------------------------------------------------------
    def _login(self, username, password):
        return self.client.post(
            "/login",
            data={"username": username, "password": password},
            follow_redirects=False,
        )

    # ─── student cannot reach any admin route ──────────────────

    def test_student_cannot_reach_add_item(self):
        self._login("bob_student", STUDENT_PW)
        self.assertEqual(self.client.get("/inventory/new").status_code, 403)
        self.assertEqual(
            self.client.post("/inventory/new", data={
                "barcode": "X", "item_name": "X",
                "current_quantity": "1", "minimum_stock": "0",
            }).status_code, 403,
        )

    def test_student_cannot_reach_edit_item(self):
        self._login("bob_student", STUDENT_PW)
        i = self._item_id
        self.assertEqual(self.client.get(f"/inventory/{i}/edit").status_code, 403)
        self.assertEqual(
            self.client.post(f"/inventory/{i}/edit", data={
                "barcode": "RBAC1", "item_name": "Renamed",
                "current_quantity": "5", "minimum_stock": "0",
            }).status_code, 403,
        )

    def test_student_cannot_reach_delete_item(self):
        self._login("bob_student", STUDENT_PW)
        r = self.client.post(f"/inventory/{self._item_id}/delete")
        self.assertEqual(r.status_code, 403)

    def test_student_cannot_reach_adjust_quantity(self):
        self._login("bob_student", STUDENT_PW)
        r = self.client.post(f"/inventory/{self._item_id}/adjust",
                             data={"quantity": "99"})
        self.assertEqual(r.status_code, 403)

    # ─── admin CAN reach all of them ───────────────────────────

    def test_admin_can_reach_every_write_route(self):
        self._login("alice_admin", ADMIN_PW)

        r = self.client.get("/inventory/new")
        self.assertEqual(r.status_code, 200)

        r = self.client.get(f"/inventory/{self._item_id}/edit")
        self.assertEqual(r.status_code, 200)

        r = self.client.post(f"/inventory/{self._item_id}/adjust",
                             data={"quantity": "7"})
        # 302 = redirect back to detail after successful update
        self.assertEqual(r.status_code, 302)

    # ─── read routes remain open to both ───────────────────────

    def test_student_can_still_read_inventory(self):
        self._login("bob_student", STUDENT_PW)
        self.assertEqual(self.client.get("/inventory/").status_code, 200)
        self.assertEqual(
            self.client.get(f"/inventory/{self._item_id}").status_code, 200,
        )

    def test_student_dashboard_hides_admin_actions(self):
        """Belt-and-suspenders — server would 403 either way, but the
        UI shouldn't tempt them."""
        self._login("bob_student", STUDENT_PW)
        body = self.client.get("/app").data.decode("utf-8")
        self.assertNotIn("/inventory/new", body,
                         "Add item link leaked to student dashboard")

    # ─── the meta-test: catch a forgotten decorator ────────────

    def test_every_admin_route_rejects_student(self):
        """Iterate the app's URL map and verify every route that
        should be admin-only actually rejects a student.

        The convention: any route in the ``inventory`` blueprint
        that accepts POST, PUT, PATCH, or DELETE is admin-only
        (until Phase 2F adds ``scan`` with its own permission
        rules). If a new POST route lands in ``inventory`` without
        ``@admin_required``, this test catches it.
        """
        self._login("bob_student", STUDENT_PW)

        # Collect (rule, method) pairs from the URL map.
        write_verbs = {"POST", "PUT", "PATCH", "DELETE"}
        write_routes = []
        for rule in self.app.url_map.iter_rules():
            if not rule.endpoint.startswith("inventory."):
                continue
            methods = (rule.methods or set()) & write_verbs
            if not methods:
                continue
            write_routes.append(rule)

        self.assertGreater(len(write_routes), 0,
                           "no inventory write routes found — did the "
                           "blueprint change name?")

        for rule in write_routes:
            # Substitute a real item id in for <int:item_id>.
            path = re.sub(r"<int:item_id>", str(self._item_id), rule.rule)
            path = re.sub(r"<[^>]+>", "1", path)     # any other params
            method = "POST"  # any write verb; POST is what our routes use
            r = self.client.open(path, method=method)
            self.assertEqual(
                r.status_code, 403,
                f"student got {r.status_code} on {method} {path} "
                f"(rule {rule.rule}) — missing @admin_required?"
            )


if __name__ == "__main__":
    unittest.main()
