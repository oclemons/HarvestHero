"""Canonical host redirect from Fly.io dev domain to production domain."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
WEB = os.path.join(ROOT, "web")
for location in (ROOT, WEB):
    if location not in sys.path:
        sys.path.insert(0, location)


PW = "AdminPass!123"


class CanonicalHost(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        os.environ["HARVESTHERO_DEV_DIR"] = self._tmp.name
        os.environ["HARVESTHERO_SECRET_KEY"] = "test-secret-abcdefghijklmnop"
        os.environ["HARVESTHERO_COOKIE_SECURE"] = "0"
        os.environ["HARVESTHERO_CANONICAL_HOST"] = "harvestheropantry.com"
        for mod in ("paths", "database", "auth", "config", "app", "extensions",
                    "routes.auth", "routes.dashboard"):
            sys.modules.pop(mod, None)
        from auth import hash_password
        from database import Database
        db = Database()
        ph, salt = hash_password(PW)
        db.create_user("admin", ph, salt, "admin")
        from app import create_app
        self.app = create_app()
        self.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False,
                               RATELIMIT_ENABLED=False)
        self.client = self.app.test_client()

    def tearDown(self):
        self._tmp.cleanup()
        os.environ.pop("HARVESTHERO_CANONICAL_HOST", None)

    def test_fly_dev_redirects_to_canonical(self):
        response = self.client.get("/login", base_url="https://harvest-hero-pantry.fly.dev")
        self.assertEqual(response.status_code, 308)
        self.assertIn("https://harvestheropantry.com/login", response.headers["Location"])

    def test_canonical_host_does_not_redirect(self):
        response = self.client.get("/login", base_url="https://harvestheropantry.com")
        self.assertEqual(response.status_code, 200)

    def test_health_check_is_exempt(self):
        response = self.client.get("/healthz", base_url="https://harvest-hero-pantry.fly.dev")
        self.assertEqual(response.status_code, 200)


if __name__ == "__main__":
    unittest.main()
