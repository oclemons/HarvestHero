"""Prove Talisman is emitting the security headers we depend on.

If any of these assertions fail, we've regressed a header that the
browser needs to enforce our security posture. This is cheaper than
scanning production with an external tool because it runs on every
push.
"""

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


class SecurityHeaders(unittest.TestCase):

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
        self.app.config["WTF_CSRF_ENABLED"] = False
        self.app.config["RATELIMIT_ENABLED"] = False
        self.client = self.app.test_client()

    def tearDown(self):
        self._tmp.cleanup()

    def _headers(self, path="/login", https=False):
        # Talisman only emits HSTS on secure requests. In production,
        # Fly.io terminates TLS and forwards X-Forwarded-Proto: https;
        # ProxyFix converts that to a wsgi request with url_scheme=https.
        # Simulate the same for tests that care about HSTS.
        env = {"HTTP_X_FORWARDED_PROTO": "https"} if https else {}
        return self.client.get(path, environ_overrides=env).headers

    # ─── The must-have headers ────────────────────────────────

    def test_hsts_is_set_when_request_is_https(self):
        h = self._headers(https=True)
        self.assertIn("Strict-Transport-Security", h)
        self.assertIn("max-age=", h["Strict-Transport-Security"])
        self.assertIn("includeSubDomains", h["Strict-Transport-Security"])

    def test_frame_options_deny(self):
        self.assertEqual(self._headers()["X-Frame-Options"], "DENY")

    def test_content_type_nosniff(self):
        self.assertEqual(
            self._headers()["X-Content-Type-Options"], "nosniff"
        )

    def test_referrer_policy_strict_origin(self):
        self.assertEqual(
            self._headers()["Referrer-Policy"],
            "strict-origin-when-cross-origin",
        )

    def test_permissions_policy_disables_dangerous_apis(self):
        pp = self._headers()["Permissions-Policy"]
        for feature in ("geolocation", "microphone", "camera",
                        "payment", "usb"):
            self.assertIn(feature, pp)
            self.assertIn(f"{feature}=()", pp)

    # ─── CSP allowlist ────────────────────────────────────────

    def test_csp_contains_expected_directives(self):
        csp = self._headers()["Content-Security-Policy"]
        for directive in ("default-src", "script-src", "style-src",
                          "img-src", "connect-src", "frame-ancestors",
                          "form-action", "base-uri", "object-src"):
            self.assertIn(directive, csp,
                          f"CSP missing {directive}: {csp!r}")
        # frame-ancestors 'none' is the twin of X-Frame-Options: DENY
        self.assertIn("frame-ancestors 'none'", csp)
        # tailwind + htmx CDNs are the only external script sources
        # we currently need. If a template starts loading from a new
        # host, this test fails so we notice.
        self.assertIn("cdn.tailwindcss.com", csp)
        self.assertIn("unpkg.com", csp)


if __name__ == "__main__":
    unittest.main()
