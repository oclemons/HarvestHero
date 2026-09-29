"""Admin distribution must verify enrollment and commit visits with stock atomically."""

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


class ScanOut(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["HARVESTHERO_DEV_DIR"] = self.tmp.name
        os.environ["HARVESTHERO_SECRET_KEY"] = "test-secret-abcdefghijklmnop"
        os.environ["HARVESTHERO_COOKIE_SECURE"] = "0"
        for name in ("paths", "database", "auth", "app", "extensions", "security",
                     "errors", "logging_config", "decorators", "routes.auth", "routes.dashboard",
                     "routes.account", "routes.inventory", "routes.scan", "routes.sections",
                     "routes.users", "routes.clients"):
            sys.modules.pop(name, None)
        from auth import hash_password
        from database import Database
        self.db = Database()
        for name, role in (("admin_a", "admin"), ("student_a", "student")):
            hashed, salt = hash_password("PantryPass!123")
            self.db.create_user(name, hashed, salt, role)
        self.admin_id = self.db.get_user("admin_a")["id"]
        section = self.db.create_pantry_section("Dry goods")
        self.shelf_id = self.db.create_pantry_shelf(section, "Shelf 1")
        self.item_id = self.db.create_item_on_shelf(
            "RICE1", "Rice", "Dry", 5, 2, self.shelf_id, "admin_a", 625,
            barcode_out="RICE1-OUT",
        )
        self.unknown_id = self.db.create_item_on_shelf(
            "BEANS1", "Beans", "Dry", 2, 0, self.shelf_id, "admin_a",
        )
        self.client_id = self.db.register_pantry_client(
            "0001234567", "Avery", "Rivera", "2003-04-05", "Fall 2028",
            "full_time", "admin_a",
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

    def verify(self):
        expiry = (datetime.date.today() + datetime.timedelta(days=100)).isoformat()
        self.db.verify_client_term(self.client_id, "Fall 2026", expiry, "admin_a")

    def test_student_cannot_see_or_submit_distribution(self):
        self.verify()
        self.login("student_a")
        self.assertEqual(self.web.get("/scan/out").status_code, 403)
        self.assertEqual(self.web.post("/scan/out/start", data={"client_id": self.client_id}).status_code, 403)
        self.assertEqual(self.web.post("/scan/out/add", data={
            "barcode": "RICE1-OUT", "shelf_id": self.shelf_id,
        }).status_code, 403)
        self.assertEqual(self.web.post("/scan/out/complete", data={"cart_id": "forged"}).status_code, 403)
        self.assertEqual(self.web.get("/scan/out/receipt/forged").status_code, 403)
        self.assertEqual(self.web.post("/scan/out/weight/1", data={
            "measured_lb": "1", "reason": "Forged",
        }).status_code, 403)
        self.assertNotIn(b"/scan/out", self.web.get("/app").data)

    def test_unverified_client_cannot_start_cart(self):
        self.login("admin_a")
        response = self.web.post("/scan/out/start", data={"client_id": self.client_id},
                                 follow_redirects=True)
        self.assertIn(b"verify", response.data.lower())
        self.assertIsNone(self.db.get_active_cart(self.admin_id, "OUT"))

    def test_scan_out_start_requires_csrf(self):
        self.verify()
        self.login("admin_a")
        self.app.config["WTF_CSRF_ENABLED"] = True
        self.assertEqual(self.web.post("/scan/out/start", data={
            "client_id": self.client_id,
        }).status_code, 400)
        self.assertIsNone(self.db.get_active_cart(self.admin_id, "OUT"))

    def test_checkout_twice_and_lifetime_weight_across_visits(self):
        self.verify()
        self.login("admin_a")
        self.assertEqual(self.web.post("/scan/out/start", data={
            "client_id": self.client_id,
        }).status_code, 302)
        for _ in range(2):
            self.web.post("/scan/out/add", data={
                "barcode": "RICE1-OUT", "shelf_id": self.shelf_id,
            })
        self.assertEqual(self.db.get_item_by_id(self.item_id)["current_quantity"], 5)
        cart = self.db.get_active_cart(self.admin_id, "OUT")
        response = self.web.post("/scan/out/complete", data={"cart_id": cart["id"]})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.db.get_item_by_id(self.item_id)["current_quantity"], 3)
        first = self.db.complete_scan_out_cart(self.admin_id, cart["id"], "admin_a")
        self.assertEqual(first["known_weight_milli_lb"], 1250)
        self.assertEqual(self.db.get_client_weight_summary(self.client_id)["total_visits"], 1)
        self.web.post("/scan/out/start", data={"client_id": self.client_id})
        self.web.post("/scan/out/add", data={"barcode": "RICE1-OUT", "shelf_id": self.shelf_id})
        second = self.db.get_active_cart(self.admin_id, "OUT")
        self.web.post("/scan/out/complete", data={"cart_id": second["id"]})
        stats = self.db.get_client_weight_summary(self.client_id)
        self.assertEqual((stats["total_visits"], stats["known_weight_milli_lb"]), (2, 1875))

    def test_stock_changed_while_cart_open_cannot_partially_check_out(self):
        self.verify()
        self.db.start_scan_out_cart(self.admin_id, self.client_id)
        for _ in range(3):
            self.db.add_scan_out_to_cart(self.admin_id, "RICE1-OUT", self.shelf_id)
        cart = self.db.get_active_cart(self.admin_id, "OUT")
        self.db.adjust_shelf_stock(self.item_id, self.shelf_id, -4, "admin_a", "Cycle count")
        with self.assertRaises(ValueError):
            self.db.complete_scan_out_cart(self.admin_id, cart["id"], "admin_a")
        self.assertEqual(self.db.get_client_weight_summary(self.client_id)["total_visits"], 0)
        self.assertEqual(self.db.get_item_by_id(self.item_id)["current_quantity"], 1)
        self.assertEqual(self.db.get_active_cart(self.admin_id, "OUT")["id"], cart["id"])

    def test_eligibility_revoked_while_cart_open_blocks_checkout(self):
        self.verify()
        self.db.start_scan_out_cart(self.admin_id, self.client_id)
        self.db.add_scan_out_to_cart(self.admin_id, "RICE1-OUT", self.shelf_id)
        cart = self.db.get_active_cart(self.admin_id, "OUT")
        self.db.revoke_client_term(self.client_id, "admin_a")
        with self.assertRaises(ValueError):
            self.db.complete_scan_out_cart(self.admin_id, cart["id"], "admin_a")
        self.assertEqual(self.db.get_client_weight_summary(self.client_id)["total_visits"], 0)
        self.assertEqual(self.db.get_item_by_id(self.item_id)["current_quantity"], 5)

    def test_failure_on_second_line_rolls_back_visit_and_first_line(self):
        self.verify()
        self.db.start_scan_out_cart(self.admin_id, self.client_id)
        self.db.add_scan_out_to_cart(self.admin_id, "RICE1-OUT", self.shelf_id)
        self.db.add_scan_out_to_cart(self.admin_id, "BEANS1", self.shelf_id)
        cart = self.db.get_active_cart(self.admin_id, "OUT")
        conn = self.db._connect()
        conn.execute("CREATE TRIGGER fail_second BEFORE INSERT ON inventory_movements "
                     "WHEN NEW.direction='OUT' AND NEW.item_id={} "
                     "BEGIN SELECT RAISE(ABORT, 'failure'); END".format(self.unknown_id))
        conn.commit()
        conn.close()
        with self.assertRaises(Exception):
            self.db.complete_scan_out_cart(self.admin_id, cart["id"], "admin_a")
        self.assertEqual(self.db.get_client_weight_summary(self.client_id)["total_visits"], 0)
        self.assertEqual(self.db.get_item_by_id(self.item_id)["current_quantity"], 5)
        self.assertEqual(self.db.get_item_by_id(self.unknown_id)["current_quantity"], 2)
        self.assertEqual(self.db.get_active_cart(self.admin_id, "OUT")["id"], cart["id"])

    def test_missing_weight_marks_visit_incomplete_not_zero(self):
        self.verify()
        self.db.start_scan_out_cart(self.admin_id, self.client_id)
        self.db.add_scan_out_to_cart(self.admin_id, "BEANS1", self.shelf_id)
        cart = self.db.get_active_cart(self.admin_id, "OUT")
        receipt = self.db.complete_scan_out_cart(self.admin_id, cart["id"], "admin_a")
        self.assertEqual(receipt["pending_lines"], 1)
        visit = self.db.get_client_visits(self.client_id)[0]
        self.assertIsNone(visit["pounds_received"])
        self.assertEqual(visit["weight_complete"], 0)
        self.assertEqual(self.db.get_client_weight_summary(self.client_id)["pending_visits"], 1)


if __name__ == "__main__":
    unittest.main()
