"""Unit tests for update_config.load()."""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))

import update_config as uc  # noqa: E402


class LoadDefaults(unittest.TestCase):
    def test_bad_paths_fall_back_to_defaults(self):
        with mock.patch.object(uc, "_bundled_config_path", return_value="/no/such/a.json"), \
             mock.patch.object(uc, "_user_config_path",    return_value="/no/such/b.json"):
            cfg = uc.load()
        self.assertEqual(cfg["auto_update"], True)
        self.assertEqual(cfg["check_on_startup"], True)
        self.assertEqual(cfg["check_interval_hours"], 6)
        self.assertEqual(cfg["notify_user"], True)
        self.assertEqual(cfg["download_timeout"], 300)

    def test_malformed_json_falls_back_to_defaults(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "update_config.json")
            with open(p, "w") as f:
                f.write("this is not json {")
            with mock.patch.object(uc, "_bundled_config_path", return_value=p), \
                 mock.patch.object(uc, "_user_config_path",    return_value="/no/such.json"):
                cfg = uc.load()
        self.assertEqual(cfg, uc.DEFAULTS)


class LoadOverrides(unittest.TestCase):
    def test_bundled_overrides_defaults(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "update_config.json")
            with open(p, "w") as f:
                json.dump({"check_interval_hours": 24, "auto_update": False}, f)
            with mock.patch.object(uc, "_bundled_config_path", return_value=p), \
                 mock.patch.object(uc, "_user_config_path",    return_value="/no/such.json"):
                cfg = uc.load()
        self.assertFalse(cfg["auto_update"])
        self.assertEqual(cfg["check_interval_hours"], 24)
        # Non-overridden keys retain defaults
        self.assertTrue(cfg["check_on_startup"])

    def test_user_override_beats_bundled(self):
        with tempfile.TemporaryDirectory() as d:
            b = os.path.join(d, "bundled.json")
            u = os.path.join(d, "user.json")
            with open(b, "w") as f:
                json.dump({"check_interval_hours": 24}, f)
            with open(u, "w") as f:
                json.dump({"check_interval_hours": 1}, f)
            with mock.patch.object(uc, "_bundled_config_path", return_value=b), \
                 mock.patch.object(uc, "_user_config_path",    return_value=u):
                cfg = uc.load()
        self.assertEqual(cfg["check_interval_hours"], 1)


class SanitisesBadValues(unittest.TestCase):
    def _load_with(self, overrides):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "bundled.json")
            with open(p, "w") as f:
                json.dump(overrides, f)
            with mock.patch.object(uc, "_bundled_config_path", return_value=p), \
                 mock.patch.object(uc, "_user_config_path",    return_value="/no/such.json"):
                return uc.load()

    def test_negative_interval_becomes_zero(self):
        cfg = self._load_with({"check_interval_hours": -10})
        self.assertEqual(cfg["check_interval_hours"], 0)

    def test_non_numeric_interval_falls_back(self):
        cfg = self._load_with({"check_interval_hours": "sometime"})
        self.assertEqual(cfg["check_interval_hours"], 6)

    def test_zero_interval_kept_zero(self):
        cfg = self._load_with({"check_interval_hours": 0})
        self.assertEqual(cfg["check_interval_hours"], 0)  # disables recurring check

    def test_low_download_timeout_gets_clamped(self):
        cfg = self._load_with({"download_timeout": 5})
        self.assertGreaterEqual(cfg["download_timeout"], 30)


if __name__ == "__main__":
    unittest.main()
