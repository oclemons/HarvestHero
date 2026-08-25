"""Offline unit tests for update_manager.UpdateManager.

Verifies the pieces of the auto-update flow that we can't test on a
live GitHub Release from inside the release workflow itself:
  * version comparison (semver-ish)
  * asset-picking from a release JSON blob
  * SHA-256 verification against a sidecar

Run:
    python -m pytest tests/test_update_manager.py -q
or:
    python -m unittest tests.test_update_manager -v
"""

from __future__ import annotations

import hashlib
import io
import os
import sys
import tempfile
import unittest
from unittest import mock

# Make the repo importable when running as `python -m unittest tests...`
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))

import update_manager as um  # noqa: E402


def _make_release(version: str, with_installer: bool = True,
                  with_checksum: bool = True):
    assets = []
    if with_installer:
        assets.append({
            "name": f"HarvestHeroSetup-{version}.exe",
            "browser_download_url": f"https://example.test/HarvestHeroSetup-{version}.exe",
        })
    if with_checksum:
        assets.append({
            "name": f"HarvestHeroSetup-{version}.exe.sha256",
            "browser_download_url": f"https://example.test/HarvestHeroSetup-{version}.exe.sha256",
        })
    return {
        "tag_name": f"v{version}",
        "body": f"release notes for {version}",
        "html_url": f"https://example.test/rel/{version}",
        "assets": assets,
    }


class _FakeResponse:
    def __init__(self, *, json_obj=None, text=None, content=None):
        self._json = json_obj
        self.text = text or ""
        self._content = content or b""
        self.headers = {"content-length": str(len(self._content))}
        self.status_code = 200

    def raise_for_status(self): return
    def json(self): return self._json
    def iter_content(self, chunk_size=8192):
        buf = io.BytesIO(self._content)
        while True:
            c = buf.read(chunk_size)
            if not c:
                break
            yield c
    def __enter__(self): return self
    def __exit__(self, *a): return False


class VersionCompare(unittest.TestCase):
    def setUp(self):
        self.mgr = um.UpdateManager()

    def test_less_than(self):
        self.assertEqual(self.mgr._compare_versions("2.0.3", "2.1.0"), -1)
        self.assertEqual(self.mgr._compare_versions("2.1.0", "2.10.0"), -1)
        self.assertEqual(self.mgr._compare_versions("v2.0.3", "2.1.0"), -1)

    def test_greater_than(self):
        self.assertEqual(self.mgr._compare_versions("2.1.0", "2.0.9"), 1)
        self.assertEqual(self.mgr._compare_versions("3.0.0", "2.99.99"), 1)

    def test_equal(self):
        self.assertEqual(self.mgr._compare_versions("2.1.0", "2.1.0"), 0)
        self.assertEqual(self.mgr._compare_versions("v2.1.0", "2.1.0"), 0)


class AssetPicking(unittest.TestCase):
    def setUp(self):
        self.mgr = um.UpdateManager()
        # Force current_version so releases look "newer".
        self.mgr.current_version = "0.0.1"

    def _run_check(self, release):
        with mock.patch.object(um.requests, "get",
                               return_value=_FakeResponse(json_obj=release)):
            return self.mgr.check_for_updates()

    def test_finds_installer_and_checksum(self):
        has, ver, _ = self._run_check(_make_release("2.1.0"))
        self.assertTrue(has)
        self.assertEqual(ver, "2.1.0")
        self.assertTrue(self.mgr.installer_url.endswith("HarvestHeroSetup-2.1.0.exe"))
        self.assertTrue(self.mgr.checksum_url.endswith(".exe.sha256"))

    def test_no_installer_asset_is_no_update(self):
        has, ver, _ = self._run_check(_make_release("2.1.0", with_installer=False))
        self.assertTrue(has)  # newer tag still means "update available"
        self.assertEqual(ver, "2.1.0")
        self.assertIsNone(self.mgr.installer_url)

    def test_older_release_is_not_update(self):
        self.mgr.current_version = "5.0.0"
        has, ver, _ = self._run_check(_make_release("2.1.0"))
        self.assertFalse(has)
        self.assertIsNone(ver)


class Sha256Verification(unittest.TestCase):
    def setUp(self):
        self.mgr = um.UpdateManager()
        self.mgr.current_version = "0.0.1"

    def _mock_get(self, expected_content: bytes, sha_text: str):
        def _get(url, *args, **kwargs):
            if url.endswith(".sha256"):
                return _FakeResponse(text=sha_text)
            return _FakeResponse(content=expected_content)
        return _get

    def test_matching_checksum_accepts_download(self):
        payload = b"this is a fake installer" * 500
        sha = hashlib.sha256(payload).hexdigest()
        self.mgr.installer_url = "https://example.test/HarvestHeroSetup-2.1.0.exe"
        self.mgr.checksum_url = "https://example.test/HarvestHeroSetup-2.1.0.exe.sha256"
        self.mgr.latest_version = "2.1.0"

        with mock.patch.object(um.requests, "get",
                               side_effect=self._mock_get(payload, f"{sha} *setup.exe")):
            ok, path_or_err = self.mgr.download_installer()
        self.assertTrue(ok, path_or_err)
        self.assertTrue(os.path.isfile(path_or_err))
        os.remove(path_or_err)

    def test_bad_checksum_rejects_download(self):
        payload = b"tampered installer bytes"
        wrong_sha = "0" * 64
        self.mgr.installer_url = "https://example.test/HarvestHeroSetup-2.1.0.exe"
        self.mgr.checksum_url = "https://example.test/HarvestHeroSetup-2.1.0.exe.sha256"
        self.mgr.latest_version = "2.1.0"

        with mock.patch.object(um.requests, "get",
                               side_effect=self._mock_get(payload, wrong_sha)):
            ok, msg = self.mgr.download_installer()
        self.assertFalse(ok)
        self.assertIn("SHA-256", msg)

    def test_missing_checksum_rejects_download(self):
        self.mgr.installer_url = "https://example.test/HarvestHeroSetup-2.1.0.exe"
        self.mgr.checksum_url = None
        self.mgr.latest_version = "2.1.0"

        with mock.patch.object(um.requests, "get",
                               return_value=_FakeResponse(content=b"whatever")):
            ok, msg = self.mgr.download_installer()
        self.assertFalse(ok)
        self.assertIn("checksum", msg.lower())


class SourceInstallCannotSelfUpgrade(unittest.TestCase):
    def test_apply_update_refuses_when_not_frozen_windows(self):
        mgr = um.UpdateManager()
        mgr.latest_version = "2.1.0"
        ok, msg = mgr.apply_update("/tmp/whatever.exe")
        self.assertFalse(ok)
        self.assertIn("developer build", msg.lower())


if __name__ == "__main__":
    unittest.main()
