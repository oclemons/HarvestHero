"""Sensitive Admin CSV exports stay gated, reauthenticated and spreadsheet-safe."""

import csv
import datetime
import io
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WEB = ROOT / "web"
for location in (str(ROOT), str(WEB)):
    if location not in sys.path:
        sys.path.insert(0, location)


class ClientExports(unittest.TestCase):
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
        self.client_id = self.db.register_pantry_client(
            "0001234567", "=FORMULA", "Rivera", "2003-04-05", "Spring 2028",
            "full_time", "admin",
        )
        from app import create_app
        self.app = create_app()
        self.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False, RATELIMIT_ENABLED=False,
                               CLIENT_RECORDS_ENABLED=True)
        self.web = self.app.test_client()

    def tearDown(self):
        self.tmp.cleanup()

    def login(self, username):
        self.web.post("/login", data={"username": username, "password": "PantryPass!123"})

    def test_customer_export_requires_admin_password_and_escapes_formulas(self):
        self.login("admin")
        self.assertEqual(self.web.get("/clients/exports").status_code, 200)
        denied = self.web.post("/clients/exports/customers.csv", data={"admin_password": "wrong"})
        self.assertEqual(denied.status_code, 403)
        self.assertNotIn(b"2003-04-05", denied.data)
        response = self.web.post("/clients/exports/customers.csv", data={
            "admin_password": "PantryPass!123",
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Cache-Control"], "private, no-store")
        rows = list(csv.DictReader(io.StringIO(response.get_data(as_text=True))))
        self.assertEqual(rows[0]["student_id"], "0001234567")
        self.assertEqual(rows[0]["first_name"], "'=FORMULA")
        self.assertEqual(rows[0]["birth_date"], "2003-04-05")
        self.assertNotIn("password_hash", response.get_data(as_text=True))

    def test_student_and_policy_gate_cannot_export(self):
        self.login("helper")
        self.assertEqual(self.web.get("/clients/exports").status_code, 403)
        self.assertEqual(self.web.post("/clients/exports/customers.csv").status_code, 403)
        self.web.get("/logout")
        self.login("admin")
        self.app.config["CLIENT_RECORDS_ENABLED"] = False
        self.assertEqual(self.web.get("/clients/exports").status_code, 503)
        self.assertEqual(self.web.post("/clients/exports/visits.csv", data={
            "admin_password": "PantryPass!123",
        }).status_code, 503)

    def test_visit_and_month_exports_include_weight_and_pending_status(self):
        section = self.db.create_pantry_section("Pantry")
        shelf = self.db.create_pantry_shelf(section, "Shelf A")
        self.db.create_item_on_shelf("RICE1", "Rice", "Dry", 3, 1, shelf, "admin", 500,
                                     barcode_out="RICE1-OUT")
        expiry = (datetime.date.today() + datetime.timedelta(days=50)).isoformat()
        self.db.verify_client_term(self.client_id, "Fall 2026", expiry, "admin")
        admin_id = self.db.get_user("admin")["id"]
        self.db.start_scan_out_cart(admin_id, self.client_id)
        self.db.add_scan_out_to_cart(admin_id, "RICE1-OUT", shelf)
        cart = self.db.get_active_cart(admin_id, "OUT")
        self.db.complete_scan_out_cart(admin_id, cart["id"], "admin")
        self.login("admin")
        response = self.web.post("/clients/exports/visits.csv", data={
            "admin_password": "PantryPass!123",
        })
        self.assertEqual(response.status_code, 200)
        row = list(csv.DictReader(io.StringIO(response.get_data(as_text=True))))[0]
        self.assertEqual(row["known_pounds"], "0.500")
        self.assertEqual(row["lifetime_known_pounds"], "0.500")
        self.assertEqual(row["pending_weight_lines"], "0")
        monthly = self.web.post("/clients/exports/monthly.csv", data={
            "admin_password": "PantryPass!123",
        })
        self.assertEqual(monthly.status_code, 200)
        self.assertIn("distributed_pounds", monthly.get_data(as_text=True))


if __name__ == "__main__":
    unittest.main()
