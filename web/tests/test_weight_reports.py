"""UTC month-end accounting and weight reconciliation."""

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


class WeightReports(unittest.TestCase):
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
        for name, role in (("admin_a", "admin"), ("student_a", "student")):
            hashed, salt = hash_password("PantryPass!123")
            self.db.create_user(name, hashed, salt, role)
        self.admin_id = self.db.get_user("admin_a")["id"]
        section = self.db.create_pantry_section("Pantry")
        self.shelf_id = self.db.create_pantry_shelf(section, "Shelf A")
        self.item_id = self.db.create_item_on_shelf(
            "RICE1", "Rice", "Dry", 10, 2, self.shelf_id, "admin_a", 500,
            barcode_out="RICE1-OUT",
        )
        from app import create_app
        self.app = create_app()
        self.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False, RATELIMIT_ENABLED=False,
                               CLIENT_RECORDS_ENABLED=True)
        self.web = self.app.test_client()
        self.month = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m")

    def tearDown(self):
        self.tmp.cleanup()

    def login(self, username):
        self.web.post("/login", data={"username": username, "password": "PantryPass!123"})

    def test_month_reports_donated_distributed_and_pending_sessions(self):
        client_id = self.db.register_pantry_client(
            "S123", "Avery", "Rivera", "2003-04-05", "Spring 2028",
            "full_time", "admin_a",
        )
        expiry = (datetime.date.today() + datetime.timedelta(days=100)).isoformat()
        self.db.verify_client_term(client_id, "Fall 2026", expiry, "admin_a")
        for _ in range(2):
            self.db.add_scan_to_cart(self.admin_id, "RICE1", self.shelf_id)
        in_cart = self.db.get_active_cart(self.admin_id, "IN")
        self.db.complete_scan_in_cart(self.admin_id, in_cart["id"], "admin_a",
                                      session_weight_milli_lb=2000)
        self.db.start_scan_out_cart(self.admin_id, client_id)
        for _ in range(3):
            self.db.add_scan_out_to_cart(self.admin_id, "RICE1-OUT", self.shelf_id)
        out_cart = self.db.get_active_cart(self.admin_id, "OUT")
        self.db.complete_scan_out_cart(self.admin_id, out_cart["id"], "admin_a",
                                       session_weight_milli_lb=1500)
        totals = self.db.get_monthly_weight_report(self.month)
        self.assertEqual(
            (totals["donated_milli_lb"], totals["distributed_milli_lb"],
             totals["pending_sessions"], totals["history_available"]),
            (2000, 1500, 0, True),
        )

    def test_shelf_transfer_does_not_change_monthly_weight_report(self):
        self.db.add_scan_to_cart(self.admin_id, "RICE1", self.shelf_id)
        in_cart = self.db.get_active_cart(self.admin_id, "IN")
        self.db.complete_scan_in_cart(self.admin_id, in_cart["id"], "admin_a",
                                      session_weight_milli_lb=5000)
        overflow = self.db.create_pantry_shelf(
            self.db.get_pantry_layout()[0]["id"], "Overflow", is_overflow=True,
        )
        self.db.transfer_shelf_stock(self.item_id, self.shelf_id, overflow, 2, "admin_a")
        totals = self.db.get_monthly_weight_report(self.month)
        self.assertEqual(totals["donated_milli_lb"], 5000)
        self.assertEqual(totals["distributed_milli_lb"], 0)
        self.assertEqual(totals["pending_sessions"], 0)
        self.assertTrue(totals["history_available"])

    def test_missing_session_weight_is_pending_and_weighted_session_updates_client_history(self):
        client_id = self.db.register_pantry_client(
            "S124", "Alex", "Rivera", "2003-04-05", "Spring 2028",
            "full_time", "admin_a",
        )
        expiry = (datetime.date.today() + datetime.timedelta(days=100)).isoformat()
        self.db.verify_client_term(client_id, "Fall 2026", expiry, "admin_a")
        self.db.start_scan_out_cart(self.admin_id, client_id)
        self.db.add_scan_out_to_cart(self.admin_id, "RICE1-OUT", self.shelf_id)
        cart = self.db.get_active_cart(self.admin_id, "OUT")
        self.db.complete_scan_out_cart(self.admin_id, cart["id"], "admin_a")
        before = self.db.get_monthly_weight_report(self.month)
        self.assertEqual(before["pending_sessions"], 1)
        self.assertEqual(before["distributed_milli_lb"], 0)
        self.assertEqual(self.db.get_client_weight_summary(client_id)["pending_visits"], 1)
        self.assertEqual(self.db.get_client_weight_summary(client_id)["known_weight_milli_lb"], 0)
        self.db.start_scan_out_cart(self.admin_id, client_id)
        self.db.add_scan_out_to_cart(self.admin_id, "RICE1-OUT", self.shelf_id)
        weighted_cart = self.db.get_active_cart(self.admin_id, "OUT")
        self.db.complete_scan_out_cart(self.admin_id, weighted_cart["id"], "admin_a",
                                       session_weight_milli_lb=375)
        self.assertEqual(self.db.get_client_weight_summary(client_id)["known_weight_milli_lb"], 375)
        self.assertEqual(self.db.get_client_weight_summary(client_id)["pending_visits"], 1)
        pounds_received = [v["pounds_received"] for v in self.db.get_client_visits(client_id)]
        self.assertIn(0.375, pounds_received)
        totals = self.db.get_monthly_weight_report(self.month)
        self.assertEqual(totals["distributed_milli_lb"], 375)
        self.assertEqual(totals["pending_sessions"], 1)

    def test_weight_report_is_admin_only(self):
        self.login("student_a")
        self.assertEqual(self.web.get("/reports/weights").status_code, 403)
        self.assertNotIn(b"/reports/", self.web.get("/app").data)
        self.web.get("/logout")
        self.login("admin_a")
        self.assertEqual(self.web.get("/reports/weights").status_code, 200)
        self.assertIn(b"Pounds, month by month", self.web.get("/reports/weights").data)


if __name__ == "__main__":
    unittest.main()
