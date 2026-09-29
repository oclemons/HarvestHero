"""Admin-reviewed inventory catalog import must never invent stock or trust uploaded rows."""

import io
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WEB = ROOT / "web"
for location in (str(ROOT), str(WEB)):
    if location not in sys.path:
        sys.path.insert(0, location)

CSV = ("barcode,barcode_out,item_name,category,current_quantity,storage_location\n"
       "S01-S1-001,S01-S1-001-OUT,Rice,Section 1,99,\"Section 1, Shelf 1\"\n"
       "S01-S1-002,S01-S1-002-OUT,Beans,Section 1,12,\"Section 1, Shelf 1\"\n")


class CatalogImport(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["HARVESTHERO_DEV_DIR"] = self.tmp.name
        os.environ["HARVESTHERO_SECRET_KEY"] = "test-secret-abcdefghijklmnop"
        os.environ["HARVESTHERO_COOKIE_SECURE"] = "0"
        for name in ("paths", "database", "auth", "app", "extensions", "security",
                     "errors", "logging_config", "decorators", "routes.auth", "routes.dashboard",
                     "routes.account", "routes.inventory", "routes.scan", "routes.sections",
                     "routes.users", "routes.clients", "routes.reports"):
            sys.modules.pop(name, None)
        from auth import hash_password
        from database import Database
        self.db = Database()
        for username, role in (("admin", "admin"), ("helper", "student")):
            hashed, salt = hash_password("PantryPass!123")
            self.db.create_user(username, hashed, salt, role)
        from app import create_app
        self.app = create_app()
        self.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False, RATELIMIT_ENABLED=False)
        self.client = self.app.test_client()

    def tearDown(self):
        self.tmp.cleanup()

    def login(self, username):
        self.client.post("/login", data={"username": username, "password": "PantryPass!123"})

    def preview(self, contents=CSV):
        response = self.client.post("/inventory/import/preview", data={
            "file": (io.BytesIO(contents.encode("utf-8")), "products.csv"),
        }, content_type="multipart/form-data")
        token = re.search(rb'name="preview_token" value="([^"]+)"', response.data)
        return response, token.group(1).decode() if token else None

    def test_existing_pantry_inventory_is_previewable_without_importing(self):
        from catalog_import import parse_catalog
        contents = (ROOT / "input" / "pantry_inventory.csv").read_bytes()
        rows = parse_catalog(contents)
        self.assertEqual(len(rows), 121)
        self.assertFalse([row for row in rows if row["problem"]])
        self.login("admin")
        response = self.client.post("/inventory/import/preview", data={
            "file": (io.BytesIO(contents), "pantry_inventory.csv"),
        }, content_type="multipart/form-data")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Possible duplicate name", response.data)
        self.assertEqual(self.db.get_all_items(), [])

    def test_reviewed_import_creates_only_zero_stock_and_shelves(self):
        self.login("admin")
        preview, token = self.preview()
        self.assertEqual(preview.status_code, 200)
        self.assertIn(b"Source counts are ignored", preview.data)
        self.assertIsNotNone(token)
        self.assertEqual(self.db.get_all_items(), [])
        confirmed = self.client.post("/inventory/import/confirm", data={
            "preview_token": token, "selected": ["0", "1"],
        })
        self.assertEqual(confirmed.status_code, 302)
        rice = self.db.get_item_by_barcode("S01-S1-001")
        self.assertEqual(rice["current_quantity"], 0)
        self.assertEqual(rice["barcode_out"], "S01-S1-001-OUT")
        self.assertEqual(len(self.db.get_all_items()), 2)
        layout = [section for section in self.db.get_pantry_layout() if not section["system"]]
        self.assertEqual(layout[0]["name"], "Section 1")
        self.assertEqual(layout[0]["shelves"][0]["name"], "Shelf 1")
        self.assertEqual(self.db.get_item_shelf_stock(rice["id"])[0]["quantity"], 0)
        self.assertEqual(self.client.get(f"/inventory/{rice['id']}/labels").status_code, 200)
        self.assertEqual(self.client.get(f"/inventory/{rice['id']}/barcode/out.svg").status_code, 200)
        repeated = self.client.post("/inventory/import/confirm", data={
            "preview_token": token, "selected": ["0", "1"],
        })
        self.assertEqual(repeated.status_code, 400)
        self.assertEqual(len(self.db.get_all_items()), 2)

    def test_signed_preview_cannot_be_changed_or_imported_by_student(self):
        self.login("admin")
        _, token = self.preview()
        self.assertEqual(self.client.post("/inventory/import/confirm", data={
            "preview_token": token + "tamper", "selected": ["0"],
        }).status_code, 400)
        self.assertEqual(self.db.get_all_items(), [])
        self.client.get("/logout")
        self.login("helper")
        self.assertEqual(self.client.get("/inventory/import").status_code, 403)
        self.assertNotIn(b"/inventory/import", self.client.get("/inventory/").data)
        self.assertEqual(self.client.post("/inventory/import/confirm", data={
            "preview_token": token, "selected": ["0"],
        }).status_code, 403)

    def test_import_upload_requires_csrf(self):
        self.login("admin")
        self.app.config["WTF_CSRF_ENABLED"] = True
        response = self.client.post("/inventory/import/preview", data={
            "file": (io.BytesIO(CSV.encode()), "products.csv"),
        }, content_type="multipart/form-data")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.db.get_all_items(), [])

    def test_duplicate_names_are_flagged_before_import(self):
        self.login("admin")
        response, _ = self.preview(CSV.replace("Beans", "Rice"))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Possible duplicate name", response.data)


if __name__ == "__main__":
    unittest.main()
