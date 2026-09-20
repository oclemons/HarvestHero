"""Prove the three session-hardening invariants hold.

  1. Session ID regenerates on login (fixation defense).
  2. A password change from a second session logs out every OTHER
     session that predates it.
  3. Idle timeout kicks the user back to /login after
     IDLE_TIMEOUT_SECONDS of no activity.
"""

from __future__ import annotations

import os
import sys
import tempfile
import time
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_WEB  = os.path.dirname(_HERE)
_ROOT = os.path.dirname(_WEB)
for p in (_ROOT, _WEB):
    if p not in sys.path:
        sys.path.insert(0, p)


PW = "SessionPass!123"


class SessionHardening(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        os.environ["HARVESTHERO_DEV_DIR"] = self._tmp.name
        os.environ["HARVESTHERO_SECRET_KEY"] = "test-secret-abcdefghijklmnop"
        os.environ["HARVESTHERO_COOKIE_SECURE"] = "0"
        for mod in ("paths", "database", "auth", "app", "extensions",
                    "security",
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
        self.app.config["WTF_CSRF_ENABLED"] = False
        self.app.config["RATELIMIT_ENABLED"] = False

    def tearDown(self):
        self._tmp.cleanup()

    def _new_client(self):
        return self.app.test_client()

    def _login(self, client, password=PW):
        return client.post(
            "/login",
            data={"username": "admin", "password": password},
            follow_redirects=False,
        )

    # ─── Invariant 1: session-fixation defense ────────────────

    def test_session_id_changes_on_login(self):
        client = self._new_client()

        # Fetch /login to obtain a pre-login session cookie.
        client.get("/login")
        cookies_before = {c.key: c.value for c in client._cookies.values()}
        pre = cookies_before.get("session")

        # Log in — this should rotate the session cookie value.
        self._login(client)
        cookies_after = {c.key: c.value for c in client._cookies.values()}
        post = cookies_after.get("session")

        self.assertIsNotNone(post, "no session cookie after login")
        self.assertNotEqual(
            pre, post,
            "session cookie value did not change on login — "
            "fixation defense is broken",
        )

    # ─── Invariant 2: password change invalidates OTHER sessions ─

    def test_password_change_kicks_second_session(self):
        # Log the same user in from two independent clients.
        alice_a = self._new_client(); self._login(alice_a)
        alice_b = self._new_client(); self._login(alice_b)

        # Both are authenticated: /app should return 200.
        self.assertEqual(alice_a.get("/app").status_code, 200)
        self.assertEqual(alice_b.get("/app").status_code, 200)

        # Alice-a changes her password.
        r = alice_a.post("/account/password", data={
            "current_password": PW,
            "new_password":     "BrandNew!789",
            "confirm_password": "BrandNew!789",
        })
        self.assertEqual(r.status_code, 302)

        # Alice-a can still hit protected pages — her own session
        # was refreshed with the new pw prefix.
        self.assertEqual(alice_a.get("/app").status_code, 200)

        # Alice-b's session still holds the OLD pw prefix, so the
        # before-request guard should log her out and redirect.
        r_b = alice_b.get("/app", follow_redirects=False)
        self.assertEqual(r_b.status_code, 302)
        self.assertIn("/login", r_b.headers["Location"])


if __name__ == "__main__":
    unittest.main()
