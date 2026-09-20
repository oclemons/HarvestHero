"""Prove CSRF protection actually blocks tokenless POSTs.

Every other test in this suite runs with WTF_CSRF_ENABLED=False so
they don't have to fetch a token before each POST. This file flips
that switch back on and demonstrates that:

  1. A POST without a token is rejected (400) — the guarantee that
     matters in production.
  2. A POST that first fetches the form and reuses the returned
     token succeeds — the guarantee that legitimate users are not
     locked out.

If this file starts failing, Flask-WTF is misconfigured and the
whole app becomes vulnerable to CSRF on every write route.
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


PW = "AdminPass!123"


class CsrfEnforced(unittest.TestCase):

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
        ph, salt = hash_password(PW)
        db.create_user("admin", ph, salt, "admin")

        from app import create_app
        self.app = create_app()
        self.app.config["TESTING"] = True
        # Deliberately DO NOT disable CSRF here — that's the point
        # of this test file. Verify the default is on.
        self.assertTrue(self.app.config["WTF_CSRF_ENABLED"])
        self.client = self.app.test_client()

    def tearDown(self):
        self._tmp.cleanup()

    # ─────────────────────────────────────────────────────────

    def _grab_csrf_token(self, path: str) -> str:
        body = self.client.get(path).data.decode("utf-8")
        m = re.search(
            r'name="csrf_token"\s+value="([^"]+)"',
            body,
        )
        self.assertIsNotNone(
            m,
            f"csrf_token hidden input missing from {path} — did the "
            f"template lose {{ csrf_token() }}?",
        )
        return m.group(1)

    # ─── T1. tokenless login POST is rejected ────────────────
    def test_login_post_without_token_is_400(self):
        r = self.client.post(
            "/login",
            data={"username": "admin", "password": PW},
        )
        self.assertEqual(r.status_code, 400)

    # ─── T2. login POST with the token succeeds ──────────────
    def test_login_post_with_token_succeeds(self):
        token = self._grab_csrf_token("/login")
        r = self.client.post(
            "/login",
            data={
                "username": "admin",
                "password": PW,
                "csrf_token": token,
            },
        )
        self.assertEqual(r.status_code, 302)

    # ─── T3. tokenless admin write is rejected ───────────────
    def test_add_item_post_without_token_is_400(self):
        # Log in first (using the token flow so we're authenticated).
        token = self._grab_csrf_token("/login")
        self.client.post(
            "/login",
            data={"username": "admin", "password": PW,
                  "csrf_token": token},
        )
        # Now try to POST a new item WITHOUT a CSRF token.
        r = self.client.post("/inventory/new", data={
            "barcode":          "CSRF1",
            "item_name":        "Should not save",
            "current_quantity": "1",
            "minimum_stock":    "0",
        })
        self.assertEqual(r.status_code, 400)

        # Verify nothing was persisted.
        from database import Database
        self.assertIsNone(Database().get_item_by_barcode("CSRF1"))


if __name__ == "__main__":
    unittest.main()
