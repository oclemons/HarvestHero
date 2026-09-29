"""Backup encryption, tamper detection and isolated schema-restore drill."""

import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for location in (str(ROOT), str(ROOT / "web")):
    if location not in sys.path:
        sys.path.insert(0, location)

from tools.secure_backup import create_key, encrypt_backup, verify_restore


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
