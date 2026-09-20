"""Prove the error handlers work and never leak sensitive info."""

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


class ErrorHandlers(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        os.environ["HARVESTHERO_DEV_DIR"] = self._tmp.name
        os.environ["HARVESTHERO_SECRET_KEY"] = "test-secret-abcdefghijklmnop"
        os.environ["HARVESTHERO_COOKIE_SECURE"] = "0"
        for mod in ("paths", "database", "auth", "app", "extensions",
                    "security", "errors", "logging_config",
                    "routes.auth", "routes.dashboard",
                    "routes.account", "routes.inventory"):
            sys.modules.pop(mod, None)
        from app import create_app
        self.app = create_app()
        self.app.config["TESTING"] = True
        # PROPAGATE_EXCEPTIONS must be False for our 500 handler
        # to actually run in tests (Flask defaults it True when
        # TESTING is on, so exceptions bubble to the caller).
        self.app.config["PROPAGATE_EXCEPTIONS"] = False
        self.app.config["WTF_CSRF_ENABLED"] = False
        self.app.config["RATELIMIT_ENABLED"] = False

        # Register a route that always raises so we can exercise the
        # 500 handler.
        @self.app.route("/__boom__")
        def _boom():
            raise RuntimeError("SECRET_SAUCE_should_not_leak")

        self.client = self.app.test_client()

    def tearDown(self):
        self._tmp.cleanup()

    # ─── 404 renders friendly page ─────────────────────────────

    def test_404_renders_generic_page(self):
        r = self.client.get("/no/such/path/exists")
        self.assertEqual(r.status_code, 404)
        body = r.data.decode("utf-8")
        self.assertIn("Page not found", body)
        self.assertIn("404", body)

    # ─── 405 renders friendly page ─────────────────────────────

    def test_405_renders_generic_page(self):
        # GET on a POST-only route -> 405
        r = self.client.get("/inventory/1/delete")
        self.assertEqual(r.status_code, 405)
        self.assertIn(b"Method not allowed", r.data)

    # ─── 500 doesn't leak the exception message or a traceback ─

    def test_500_hides_exception_details(self):
        r = self.client.get("/__boom__")
        self.assertEqual(r.status_code, 500)
        body = r.data.decode("utf-8")

        # Friendly page shown.
        self.assertIn("Something went wrong", body)

        # None of these forbidden strings appears in the response:
        for leak in (
            "SECRET_SAUCE_should_not_leak",   # exception message
            "Traceback",                       # stack trace header
            "RuntimeError",                    # exception class
            "raise RuntimeError",              # source line
            "__boom__",                        # internal route path
            ".py",                             # file path fragment
            "File \"",                         # traceback file marker
        ):
            self.assertNotIn(leak, body,
                             f"500 response leaked {leak!r}")


if __name__ == "__main__":
    unittest.main()
