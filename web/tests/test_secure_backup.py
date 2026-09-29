"""Backup encryption, tamper detection and isolated schema-restore drill."""

import json
import os
import shutil
import sys
import tempfile
from types import SimpleNamespace
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for location in (str(ROOT), str(ROOT / "web")):
    if location not in sys.path:
        sys.path.insert(0, location)

from tools.secure_backup import backup_live, create_key, encrypt_backup, verify_restore


class SecureBackup(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self.tmp.name)
        os.environ["HARVESTHERO_DEV_DIR"] = self.tmp.name
        for name in ("paths", "database"):
            sys.modules.pop(name, None)
        from database import Database
        self.db_path = self.folder / "inventory.db"
        db = Database(str(self.db_path))
        db.add_item("RICE", "Rice", "Dry", 4, 1, "")
        db.register_pantry_client("S123", "Avery", "Rivera", "2003-04-05",
                                  "Spring 2028", "full_time", "admin")
        self.private = self.folder / "backup.private"
        self.public = self.folder / "backup.public"
        self.encrypted = self.folder / "backup.hhb"
        create_key(self.private, self.public)

    def tearDown(self):
        self.tmp.cleanup()

    def test_encrypted_backup_restores_and_migrates_without_losing_rows(self):
        encrypt_backup(self.db_path, self.public, self.encrypted)
        self.assertNotIn(b"Avery", self.encrypted.read_bytes())
        self.assertEqual(verify_restore(self.encrypted, self.private)["inventory_items"], 1)
        self.assertEqual(verify_restore(self.encrypted, self.private)["pantry_clients"], 1)
        self.assertEqual(self.db_path.stat().st_size > 0, True)

    def test_manual_live_backup_downloads_only_ciphertext_and_verifies_it(self):
        encrypt_backup(self.db_path, self.public, self.encrypted)
        destination = self.folder / "off-fly"
        destination.mkdir(mode=0o700)
        calls = []

        def pretend_fly(command, **kwargs):
            calls.append(command)
            if command[:3] == ["flyctl", "machine", "list"]:
                return SimpleNamespace(stdout=json.dumps([{"id": "test-machine", "state": "suspended"}]))
            if command[:4] == ["flyctl", "ssh", "sftp", "get"]:
                shutil.copyfile(self.encrypted, command[5])
            return SimpleNamespace(stdout="")

        output, counts = backup_live("pantry-test", self.public, self.private, destination,
                                     run_command=pretend_fly)
        self.assertEqual(counts["inventory_items"], 1)
        self.assertEqual(counts["pantry_clients"], 1)
        self.assertNotIn(b"Avery", output.read_bytes())
        self.assertEqual(output.stat().st_mode & 0o777, 0o600)
        self.assertTrue(any(command[:3] == ["flyctl", "machine", "start"] for command in calls))
        self.assertTrue(any(command[:4] == ["flyctl", "ssh", "sftp", "get"] for command in calls))
        self.assertTrue(any(command[:4] == ["flyctl", "ssh", "sftp", "put"] and
                            "/tmp/hh_secure_backup_" in command[5] for command in calls))
        self.assertFalse(any(str(self.private) in " ".join(command) for command in calls))

    def test_modified_ciphertext_cannot_be_restored(self):
        encrypt_backup(self.db_path, self.public, self.encrypted)
        blob = bytearray(self.encrypted.read_bytes())
        blob[-18] ^= 1
        self.encrypted.write_bytes(blob)
        with self.assertRaises(Exception):
            verify_restore(self.encrypted, self.private)

    def test_existing_private_key_is_never_overwritten(self):
        original = self.private.read_bytes()
        with self.assertRaises(ValueError):
            create_key(self.private, self.public)
        self.assertEqual(self.private.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
