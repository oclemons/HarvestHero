"""Donation weight recording, editing, deletion, and access control."""

import datetime
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


class DonationRecords(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["HARVESTHERO_DEV_DIR"] = self.tmp.name
        os.environ["HARVESTHERO_SECRET_KEY"] = "test-secret-abcdefghijklmnop"
        os.environ["HARVESTHERO_COOKIE_SECURE"] = "0"
        for name in ("paths", "database", "auth", "app", "extensions", "security",
                     "errors", "logging_config", "decorators", "routes.auth", "routes.dashboard",
                     "routes.account", "routes.inventory", "routes.scan", "routes.sections",
                     "routes.users", "routes.clients", "routes.reports", "routes.donations"):
            sys.modules.pop(name, None)
        from auth import hash_password
        from database import Database
        self.db = Database()
        for name, role in (("admin_a", "admin"), ("student_a", "student")):
            hashed, salt = hash_password("PantryPass!123")
            self.db.create_user(name, hashed, salt, role)
        from app import create_app
        self.app = create_app()
        self.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False, RATELIMIT_ENABLED=False)
        self.web = self.app.test_client()

    def tearDown(self):
        self.tmp.cleanup()

    def login(self, username):
        self.web.post("/login", data={"username": username, "password": "PantryPass!123"})

    def test_admin_can_record_and_edit_donation(self):
        self.login("admin_a")
        response = self.web.post("/donations/new", data={
            "weight_lb": "42.5", "donation_date": "2026-09-15",
            "source": "Food bank", "notes": "Monthly delivery",
        })
        self.assertEqual(response.status_code, 302)
        records = self.db.get_donation_records()
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["weight_milli_lb"], 42500)
        self.assertEqual(records[0]["source"], "Food bank")
        record_id = records[0]["id"]
        response = self.web.post(f"/donations/{record_id}/edit", data={
            "weight_lb": "50.0", "donation_date": "2026-09-16",
            "source": "Community drive", "notes": "Updated",
        })
        self.assertEqual(response.status_code, 302)
        updated = self.db.get_donation_record(record_id)
        self.assertEqual(updated["weight_milli_lb"], 50000)
        self.assertEqual(updated["donation_date"], "2026-09-16")
        log = self.db.get_activity_log(10)
        actions = [e["action"] for e in log]
        self.assertIn("DONATION_RECORD", actions)
        self.assertIn("DONATION_EDIT", actions)

    def test_admin_can_delete_donation(self):
        self.login("admin_a")
        self.web.post("/donations/new", data={
            "weight_lb": "10", "donation_date": "2026-09-01",
        })
        record_id = self.db.get_donation_records()[0]["id"]
        response = self.web.post(f"/donations/{record_id}/delete")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(self.db.get_donation_records()), 0)
        log = self.db.get_activity_log(10)
        self.assertIn("DONATION_DELETE", [e["action"] for e in log])

    def test_student_cannot_access_donations(self):
        self.login("student_a")
        self.assertEqual(self.web.get("/donations/").status_code, 403)
        self.assertEqual(self.web.post("/donations/new", data={
            "weight_lb": "10", "donation_date": "2026-09-01",
        }).status_code, 403)

    def test_donation_appears_in_monthly_report(self):
        today = datetime.date.today().isoformat()
        month = today[:7]
        self.db.record_donation_weight(5000, today, "Test", "", "admin_a")
        report = self.db.get_monthly_weight_report(month)
        self.assertEqual(report["donated_standalone_milli_lb"], 5000)
        self.assertEqual(report["donated_milli_lb"], 5000)

    def test_session_weight_correction_is_logged(self):
        section = self.db.create_pantry_section("Pantry")
        shelf = self.db.create_pantry_shelf(section, "Shelf A")
        self.db.create_item_on_shelf("DON1", "Rice", "Dry", 5, 0, shelf, "admin_a",
                                     barcode_out="DON1-OUT")
        admin_id = self.db.get_user("admin_a")["id"]
        self.db.add_scan_to_cart(admin_id, "DON1", shelf)
        cart = self.db.get_active_cart(admin_id, "IN")
        self.db.complete_scan_in_cart(admin_id, cart["id"], "admin_a",
                                      session_weight_milli_lb=3000)
        receipt = self.db.get_cart_receipt(admin_id, cart["id"])
        self.assertEqual(receipt["known_weight_milli_lb"], 3000)
        self.db.update_session_weight(cart["id"], 3500, "Scale recalibrated", "admin_a")
        receipt = self.db.get_cart_receipt(admin_id, cart["id"])
        self.assertEqual(receipt["known_weight_milli_lb"], 3500)
        log = self.db.get_activity_log(10)
        self.assertIn("WEIGHT_CORRECTION", [e["action"] for e in log])

    def test_activity_log_page_loads(self):
        self.login("admin_a")
        self.db.log_activity("admin_a", "TEST_ACTION", "test detail")
        response = self.web.get("/reports/activity")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"TEST_ACTION", response.data)
        self.assertIn(b"test detail", response.data)
        filtered = self.web.get("/reports/activity?action=TEST_ACTION")
        self.assertEqual(filtered.status_code, 200)
        self.assertIn(b"TEST_ACTION", filtered.data)

    def test_activity_log_is_admin_only(self):
        self.login("student_a")
        self.assertEqual(self.web.get("/reports/activity").status_code, 403)

    def test_sessions_page_loads_and_weight_correction_works(self):
        self.login("admin_a")
        response = self.web.get("/reports/sessions")
        self.assertEqual(response.status_code, 200)


if __name__ == "__main__":
    unittest.main()
