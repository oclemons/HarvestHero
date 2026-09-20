"""Prove the JSON request logger emits well-formed lines and never
logs secret fields."""

from __future__ import annotations

import io
import json
import logging
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


class RequestLogging(unittest.TestCase):

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
        self.app.config["WTF_CSRF_ENABLED"] = False
        self.app.config["RATELIMIT_ENABLED"] = False

        # Redirect the JSON formatter's stream to a StringIO we can
        # read back after the request completes. install_logging()
        # attached its handler to the root logger.
        self._buf = io.StringIO()
        root = logging.getLogger()
        for h in list(root.handlers):
            h.stream = self._buf

        self.client = self.app.test_client()

    def tearDown(self):
        self._tmp.cleanup()

    def _log_lines(self):
        raw = self._buf.getvalue().strip().splitlines()
        return [json.loads(line) for line in raw if line.strip()]

    def _request_lines(self):
        return [l for l in self._log_lines() if l.get("event") == "request"]

    # ─────────────────────────────────────────────────────────

    def test_request_log_is_valid_json_with_expected_fields(self):
        self.client.get("/login")
        lines = self._request_lines()
        self.assertTrue(lines, "no request log line emitted")
        entry = lines[-1]
        for k in ("ts", "level", "logger", "event",
                  "method", "path", "status", "duration_ms", "user"):
            self.assertIn(k, entry)
        self.assertEqual(entry["method"], "GET")
        self.assertEqual(entry["path"],   "/login")
        self.assertEqual(entry["status"], 200)
        self.assertIsNone(entry["user"])   # not logged in

    def test_healthz_is_not_logged(self):
        """Fly.io polls /healthz every 15s; we skip it to prevent
        the log stream from being 90% probe noise."""
        self.client.get("/healthz")
        for entry in self._request_lines():
            self.assertNotEqual(
                entry["path"], "/healthz",
                "healthz probe was logged — fix logging_config.py",
            )

    def test_post_body_never_appears_in_log(self):
        """A POST with sensitive form data. The form values must
        never end up in the log line."""
        self.client.post("/login", data={
            "username": "admin",
            "password": "thisPasswordMustNotAppearInLogs!!",
        })
        raw = self._buf.getvalue()
        self.assertNotIn("thisPasswordMustNotAppearInLogs", raw,
                         "password leaked into request log")


if __name__ == "__main__":
    unittest.main()
