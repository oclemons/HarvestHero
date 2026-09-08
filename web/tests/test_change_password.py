"""Integration tests for the change-password route.

Uses Flask's test client so no gunicorn is involved. Each test builds a
fresh scratch USER_DIR + seed admin, boots the app factory, and drives
the route through HTTP.
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest

# repo root and web/ both on sys.path
_HERE = os.path.dirname(os.path.abspath(__file__))
_WEB  = os.path.dirname(_HERE)
_ROOT = os.path.dirname(_WEB)
for p in (_ROOT, _WEB):
    if p not in sys.path:
        sys.path.insert(0, p)


SEED_PW = "SeededAdmin!123"
NEW_PW  = "PantryRotate!456"


class ChangePasswordFlow(unittest.TestCase):

    def setUp(self):
        # Fresh persistent-dir per test so state doesn't leak.
        self._tmp = tempfile.TemporaryDirectory()
        os.environ["HARVESTHERO_DEV_DIR"] = self._tmp.name
        os.environ["HARVESTHERO_SECRET_KEY"] = "test-secret-abcdefghijklmnop"
        os.environ["HARVESTHERO_COOKIE_SECURE"] = "0"

        # We reset the cached paths / db modules so each test gets a
        # fresh Database() bound to the new HARVESTHERO_DEV_DIR.
        for mod in ("paths", "database", "auth", "app", "extensions",
                    "routes.auth", "routes.dashboard", "routes.account"):
            sys.modules.pop(mod, None)

        # Seed the admin.
        from database import Database
        from auth import hash_password
        db = Database()
        ph, salt = hash_password(SEED_PW)
        ok, _ = db.create_user("admin", ph, salt, "admin")
        assert ok

        from app import create_app
        self.app = create_app()
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

    def tearDown(self):
        self._tmp.cleanup()

    # ------------------------------------------------------------------
    def _login(self, username="admin", password=SEED_PW):
        return self.client.post(
            "/login",
            data={"username": username, "password": password},
            follow_redirects=False,
        )

    def _change(self, current, new_, confirm):
        return self.client.post(
            "/account/password",
            data={"current_password": current,
                  "new_password": new_,
                  "confirm_password": confirm},
            follow_redirects=False,
        )

    def _settings_body(self):
        return self.client.get("/account/settings").data.decode("utf-8")

    # ------------------------------------------------------------------
    def test_login_and_settings_page(self):
        r = self._login()
        self.assertEqual(r.status_code, 302)
        body = self._settings_body()
        self.assertIn("Change password", body)
        self.assertIn("Update password", body)

    def test_wrong_current_password_rejected(self):
        self._login()
        self._change("WRONG", "SomethingNew!7", "SomethingNew!7")
        self.assertIn("Current password is incorrect", self._settings_body())

    def test_mismatched_confirmation_rejected(self):
        self._login()
        self._change(SEED_PW, "SomethingNew!7", "DifferentValue!7")
        self.assertIn("do not match", self._settings_body())

    def test_weak_new_password_rejected(self):
        self._login()
        self._change(SEED_PW, "short", "short")
        self.assertIn("at least 8 characters", self._settings_body())

    def test_reusing_current_password_rejected(self):
        self._login()
        self._change(SEED_PW, SEED_PW, SEED_PW)
        self.assertIn("different from the current", self._settings_body())

    def test_valid_change_updates_password(self):
        self._login()
        self._change(SEED_PW, NEW_PW, NEW_PW)
        self.assertIn("Password changed", self._settings_body())

        # Log out and log back in with the new password.
        self.client.get("/logout")

        # Old password no longer works.
        r_old = self._login(password=SEED_PW)
        # If auth fails Flask re-renders the login form with a flash;
        # a successful login redirects (302). Failure returns 200.
        self.assertEqual(r_old.status_code, 200)
        self.assertIn(b"Invalid username or password", r_old.data)

        # New password works.
        r_new = self._login(password=NEW_PW)
        self.assertEqual(r_new.status_code, 302)

    def test_change_requires_auth(self):
        """Unauthenticated POST /account/password redirects to login."""
        r = self._change(SEED_PW, NEW_PW, NEW_PW)
        self.assertEqual(r.status_code, 302)
        self.assertIn("/login", r.headers["Location"])


if __name__ == "__main__":
    unittest.main()
