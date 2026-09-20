"""Prove the login rate limit actually returns 429 after the cap."""

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


class RateLimitEnforced(unittest.TestCase):

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
        from app import create_app
        self.app = create_app()
        self.app.config["TESTING"] = True
        # Deliberately keep RATELIMIT_ENABLED at its True default —
        # that's the point of this file.
        self.assertTrue(self.app.config["RATELIMIT_ENABLED"])
        self.app.config["WTF_CSRF_ENABLED"] = False
        self.client = self.app.test_client()

    def tearDown(self):
        self._tmp.cleanup()

    def test_login_returns_429_after_the_11th_attempt(self):
        """10 per 5 minutes on POST /login. 11th attempt from the same
        IP must be rejected with 429 regardless of credentials."""
        for i in range(10):
            r = self.client.post(
                "/login",
                data={"username": "nobody", "password": "wrong"},
            )
            self.assertIn(r.status_code, (200, 302),
                          f"attempt {i + 1} unexpectedly got {r.status_code}")
        # 11th call must be limited.
        r = self.client.post(
            "/login",
            data={"username": "nobody", "password": "wrong"},
        )
        self.assertEqual(r.status_code, 429)


if __name__ == "__main__":
    unittest.main()
