"""Client privacy and manual semester-eligibility checks."""

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


class ClientAccess(unittest.TestCase):
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
        from app import create_app
        self.app = create_app()
        self.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False, RATELIMIT_ENABLED=False,
                               CLIENT_RECORDS_ENABLED=True)
        self.client = self.app.test_client()

    def tearDown(self):
        self.tmp.cleanup()

    def login(self, name):
        self.client.post("/login", data={"username": name, "password": "PantryPass!123"})

    def create_client(self):
        return self.db.register_pantry_client(
            "0001234567", "Avery", "Rivera", "2003-04-05", "Fall 2028",
            "full_time", "admin_a",
        )

    def test_client_and_checkout_routes_fail_closed_until_policy_enabled(self):
        client_id = self.create_client()
        self.app.config["CLIENT_RECORDS_ENABLED"] = False
        self.login("admin_a")
        for path in ("/clients/", "/clients/new", "/clients/retention",
                     f"/clients/{client_id}", f"/clients/{client_id}/edit", "/scan/out"):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 503, path)
            self.assertNotIn(b"0001234567", response.data)
        for path in ("/clients/new", f"/clients/{client_id}/verify", "/scan/out/start",
                     "/scan/out/add", "/scan/out/complete", "/scan/out/undo/1",
                     "/clients/exports/customers.csv", f"/clients/{client_id}/retention/remove"):
            self.assertEqual(self.client.post(path, data={"client_id": client_id}).status_code, 503)
        self.assertNotIn(b"/clients/", self.client.get("/app").data)
        self.assertNotIn(b"/scan/out", self.client.get("/app").data)
        self.client.get("/logout")
        self.login("student_a")
        self.assertEqual(self.client.get("/clients/").status_code, 403)
        self.assertEqual(self.client.get("/scan/out").status_code, 403)

    def test_admin_intake_and_semester_verification_are_private(self):
        self.login("admin_a")
        response = self.client.post("/clients/new", data={
            "student_id": "0001234567", "first_name": "Avery", "last_name": "Rivera",
            "birth_date": "2003-04-05", "graduation_semester": "Fall 2028",
            "enrollment_status": "full_time",
        })
        self.assertEqual(response.status_code, 302)
        client_id = self.db.list_private_clients()[0]["id"]
        directory = self.client.get("/clients/").data
        self.assertIn(b"Avery", directory)
        self.assertIn(b"4567", directory)
        self.assertNotIn(b"0001234567", directory)
        self.assertNotIn(b"2003-04-05", directory)
        self.assertFalse(self.db.is_client_eligible(client_id))
        expiry = (datetime.date.today() + datetime.timedelta(days=100)).isoformat()
        self.client.post(f"/clients/{client_id}/verify", data={
            "term": "Fall 2026", "verified_until": expiry,
            "confirmed_enrollment": "on",
        })
        self.assertTrue(self.db.is_client_eligible(client_id))
        self.client.post(f"/clients/{client_id}/revoke")
        self.assertFalse(self.db.is_client_eligible(client_id))
        self.client.get("/logout")
        self.login("student_a")
        self.assertEqual(self.client.get("/clients/").status_code, 403)
        self.assertEqual(self.client.get(f"/clients/{client_id}").status_code, 403)
        self.assertEqual(self.client.post(f"/clients/{client_id}/verify", data={
            "term": "Fall 2026", "verified_until": expiry,
        }).status_code, 403)
        self.assertEqual(self.client.post(f"/clients/{client_id}/revoke").status_code, 403)
        self.assertNotIn(b"Avery", self.client.get("/app").data)

    def test_identity_change_revokes_enrollment(self):
        client_id = self.create_client()
        expiry = (datetime.date.today() + datetime.timedelta(days=100)).isoformat()
        self.db.verify_client_term(client_id, "Fall 2026", expiry, "admin_a")
        self.assertTrue(self.db.is_client_eligible(client_id))
        self.login("admin_a")
        response = self.client.post(f"/clients/{client_id}/edit", data={
            "student_id": "0001239999", "first_name": "Avery", "last_name": "Rivera",
            "birth_date": "2003-04-05", "graduation_semester": "Fall 2028",
            "enrollment_status": "full_time",
        })
        self.assertEqual(response.status_code, 302)
        self.assertFalse(self.db.is_client_eligible(client_id))
        self.client.get("/logout")
        self.login("student_a")
        self.assertEqual(self.client.get(f"/clients/{client_id}/edit").status_code, 403)
        self.assertEqual(self.client.post(f"/clients/{client_id}/edit", data={
            "student_id": "X",
        }).status_code, 403)

    def test_enrollment_type_change_revokes_current_term(self):
        client_id = self.create_client()
        expiry = (datetime.date.today() + datetime.timedelta(days=100)).isoformat()
        self.db.verify_client_term(client_id, "fall 2026", expiry, "admin_a")
        self.assertEqual(self.db.get_client_visit_allowance(client_id)["term"], "Fall 2026")
        self.db.update_registered_client(client_id, "0001234567", "Avery", "Rivera",
                                         "2003-04-05", "Fall 2028", "part_time", "admin_a")
        self.assertFalse(self.db.is_client_eligible(client_id))
        self.db.verify_client_term(client_id, "Fall 2026", expiry, "admin_a")
        self.assertEqual(self.db.get_client_visit_allowance(client_id)["limit"], 2)

    def test_deactivation_revokes_verification_until_rechecked(self):
        client_id = self.create_client()
        expiry = (datetime.date.today() + datetime.timedelta(days=100)).isoformat()
        self.db.verify_client_term(client_id, "Fall 2026", expiry, "admin_a")
        self.login("admin_a")
        self.client.post(f"/clients/{client_id}/status", data={"active": "0"})
        self.assertFalse(self.db.is_client_eligible(client_id))
        self.assertIsNotNone(self.db.get_pantry_client(client_id)["deactivated_at"])
        self.client.post(f"/clients/{client_id}/status", data={"active": "1"})
        self.assertFalse(self.db.is_client_eligible(client_id))
        self.assertIsNone(self.db.get_pantry_client(client_id)["deactivated_at"])

    def test_private_dietary_fields_and_household_size_are_saved_and_admin_only(self):
        self.login("admin_a")
        response = self.client.post("/clients/new", data={
            "student_id": "S999", "first_name": "Sam", "last_name": "Lee",
            "birth_date": "2002-06-01", "graduation_semester": "Spring 2028",
            "enrollment_status": "part_time", "household_size": "4",
            "allergies": "Peanuts", "religious_restrictions": "No pork",
        })
        self.assertEqual(response.status_code, 302)
        client_id = self.db.list_private_clients()[0]["id"]
        client = self.db.get_pantry_client(client_id)
        self.assertEqual((client["household_size"], client["allergies"],
                          client["religious_restrictions"]), (4, "Peanuts", "No pork"))
        detail_response = self.client.get(f"/clients/{client_id}")
        self.assertEqual(detail_response.headers["Cache-Control"], "private, no-store")
        detail = detail_response.data
        self.assertIn(b"Peanuts", detail)
        self.assertIn(b"No pork", detail)
        directory = self.client.get("/clients/").data
        self.assertNotIn(b"Peanuts", directory)
        self.assertNotIn(b"No pork", directory)
        self.client.get("/logout")
        self.login("student_a")
        self.assertEqual(self.client.get(f"/clients/{client_id}").status_code, 403)
        self.assertNotIn(b"Peanuts", self.client.get("/app").data)

    def test_due_visit_client_is_removed_without_losing_organization_totals(self):
        client_id = self.db.register_pantry_client(
            "RET-100", "Avery", "Rivera", "2003-04-05", "Fall 2028",
            "full_time", "admin_a", allergies="Peanuts", religious_restrictions="No pork",
        )
        section = self.db.create_pantry_section("Pantry")
        shelf = self.db.create_pantry_shelf(section, "Shelf A")
        item_id = self.db.create_item_on_shelf("RET-FOOD", "Rice", "Dry", 2, 0, shelf,
                                                "admin_a", 500, barcode_out="RET-FOOD-OUT")
        expiry = (datetime.date.today() + datetime.timedelta(days=100)).isoformat()
        self.db.verify_client_term(client_id, "Fall 2026", expiry, "admin_a")
        admin_id = self.db.get_user("admin_a")["id"]
        cart_id = self.db.start_scan_out_cart(admin_id, client_id, mode="IMMEDIATE")
        movement_id = self.db.record_immediate_scan_out(admin_id, "RET-FOOD-OUT", shelf,
                                                         "admin_a", "retention-scan-1")
        self.db.complete_scan_out_cart(admin_id, cart_id, "admin_a")
        conn = self.db._connect()
        conn.execute("UPDATE pantry_visits SET visit_date = '2024-01-15 12:00:00' "
                     "WHERE client_id = ?", (client_id,))
        conn.commit()
        conn.close()
        self.login("admin_a")
        review = self.client.get("/clients/retention")
        self.assertEqual(review.status_code, 200)
        self.assertIn(b"Avery", review.data)
        self.assertEqual(self.client.post(f"/clients/{client_id}/retention/remove", data={
            "admin_password": "wrong", "student_id": "RET-100", "confirmed_removal": "on",
        }).status_code, 403)
        self.assertIsNotNone(self.db.get_pantry_client(client_id))
        response = self.client.post(f"/clients/{client_id}/retention/remove", data={
            "admin_password": "PantryPass!123", "student_id": "RET-100",
            "confirmed_removal": "on",
        })
        self.assertEqual(response.status_code, 302)
        self.assertIsNone(self.db.get_pantry_client(client_id))
        self.assertEqual(self.db.get_client_visits(client_id), [])
        self.assertEqual(self.db.get_item_by_id(item_id)["current_quantity"], 1)
        totals = self.db.get_monthly_service_summary("2024-01")
        self.assertEqual((totals["visits"], totals["known_weight_milli_lb"]), (1, 500))
        with self.assertRaises(ValueError):
            self.db.remove_client_identity(client_id, "RET-100", "admin_a")
        self.assertEqual(self.db.get_monthly_service_summary("2024-01")["visits"], 1)
        exported = self.client.post("/clients/exports/monthly.csv", data={
            "admin_password": "PantryPass!123", "month": "2024-01",
            "fields": ["month_utc", "service_visits", "service_known_pounds"],
        })
        self.assertEqual(exported.status_code, 200)
        self.assertIn(b'"1","0.500"', exported.data)
        self.assertNotIn(b"RET-100", exported.data)
        self.assertIn(b"Pantry services this month",
                      self.client.get("/reports/weights?month=2024-01").data)
        conn = self.db._connect()
        movement = conn.execute("SELECT client_id, visit_id FROM inventory_movements "
                                "WHERE id = ?", (movement_id,)).fetchone()
        self.assertEqual((movement["client_id"], movement["visit_id"]), (None, None))
        self.assertEqual(conn.execute("PRAGMA foreign_key_check").fetchall(), [])
        conn.close()
        self.client.get("/logout")
        self.login("student_a")
        self.assertEqual(self.client.get("/clients/retention").status_code, 403)

    def test_retention_refuses_early_or_incorrect_confirmation(self):
        client_id = self.create_client()
        self.db.set_client_record_active(client_id, False, "admin_a")
        with self.assertRaises(ValueError):
            self.db.remove_client_identity(client_id, "0001234567", "admin_a")
        conn = self.db._connect()
        conn.execute("UPDATE pantry_clients SET deactivated_at = '2024-01-15' WHERE id = ?",
                     (client_id,))
        conn.commit()
        conn.close()
        self.login("admin_a")
        response = self.client.post(f"/clients/{client_id}/retention/remove", data={
            "admin_password": "PantryPass!123", "student_id": "WRONG",
            "confirmed_removal": "on",
        })
        self.assertEqual(response.status_code, 400)
        self.assertIsNotNone(self.db.get_pantry_client(client_id))
        with self.assertRaises(ValueError):
            self.db.remove_client_identity(client_id, "0001234567", "student_a")
        self.client.get("/logout")
        self.login("student_a")
        self.assertEqual(self.client.post(f"/clients/{client_id}/retention/remove", data={
            "admin_password": "PantryPass!123", "student_id": "0001234567",
            "confirmed_removal": "on",
        }).status_code, 403)
        self.assertIsNotNone(self.db.get_pantry_client(client_id))

    def test_retention_removal_requires_csrf(self):
        client_id = self.create_client()
        self.db.set_client_record_active(client_id, False, "admin_a")
        conn = self.db._connect()
        conn.execute("UPDATE pantry_clients SET deactivated_at = '2024-01-15' WHERE id = ?",
                     (client_id,))
        conn.commit()
        conn.close()
        self.login("admin_a")
        self.app.config["WTF_CSRF_ENABLED"] = True
        response = self.client.post(f"/clients/{client_id}/retention/remove", data={
            "admin_password": "PantryPass!123", "student_id": "0001234567",
            "confirmed_removal": "on",
        })
        self.assertEqual(response.status_code, 400)
        self.assertIsNotNone(self.db.get_pantry_client(client_id))

    def test_retention_removal_rolls_back_if_visit_unlink_fails(self):
        client_id = self.create_client()
        self.db.record_pantry_visit(client_id, 1.25, "admin_a")
        conn = self.db._connect()
        conn.execute("UPDATE pantry_visits SET visit_date = '2024-01-15 12:00:00' "
                     "WHERE client_id = ?", (client_id,))
        conn.execute("CREATE TRIGGER prevent_retention BEFORE DELETE ON pantry_visits "
                     "BEGIN SELECT RAISE(ABORT, 'blocked'); END")
        conn.commit()
        conn.close()
        with self.assertRaises(Exception):
            self.db.remove_client_identity(client_id, "0001234567", "admin_a")
        self.assertIsNotNone(self.db.get_pantry_client(client_id))
        self.assertEqual(len(self.db.get_client_visits(client_id)), 1)
        self.assertEqual(self.db.get_monthly_service_summary("2024-01")["visits"], 1)
        conn = self.db._connect()
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM retired_service_months").fetchone()[0], 0)
        conn.close()

    def test_retention_waits_for_open_distribution_to_finish(self):
        client_id = self.create_client()
        self.db.record_pantry_visit(client_id, 0.5, "admin_a")
        conn = self.db._connect()
        conn.execute("UPDATE pantry_visits SET visit_date = '2024-01-15 12:00:00' "
                     "WHERE client_id = ?", (client_id,))
        conn.commit()
        conn.close()
        expiry = (datetime.date.today() + datetime.timedelta(days=100)).isoformat()
        self.db.verify_client_term(client_id, "Fall 2026", expiry, "admin_a")
        admin_id = self.db.get_user("admin_a")["id"]
        cart_id = self.db.start_scan_out_cart(admin_id, client_id)
        with self.assertRaises(ValueError):
            self.db.remove_client_identity(client_id, "0001234567", "admin_a")
        self.db.cancel_scan_cart(admin_id, cart_id, "OUT")
        self.assertIsNotNone(self.db.get_pantry_client(client_id))

    def test_six_calendar_months_clamp_to_month_end(self):
        client_id = self.create_client()
        self.db.set_client_record_active(client_id, False, "admin_a")
        conn = self.db._connect()
        conn.execute("UPDATE pantry_clients SET deactivated_at = '2025-08-31' WHERE id = ?",
                     (client_id,))
        conn.commit()
        conn.close()
        self.assertEqual(self.db.get_retention_candidates(today=datetime.date(2026, 2, 27)), [])
        due = self.db.get_retention_candidates(today=datetime.date(2026, 2, 28))
        self.assertEqual(due[0]["due_date"], "2026-02-28")

    def test_never_visited_retention_starts_at_deactivation(self):
        client_id = self.create_client()
        self.assertEqual(self.db.get_retention_candidates(today=datetime.date(2030, 1, 1)), [])
        self.db.set_client_record_active(client_id, False, "admin_a")
        conn = self.db._connect()
        conn.execute("UPDATE pantry_clients SET deactivated_at = '2024-01-15' WHERE id = ?",
                     (client_id,))
        conn.commit()
        conn.close()
        due = self.db.get_retention_candidates(today=datetime.date(2024, 7, 15))
        self.assertEqual(due[0]["id"], client_id)
        self.assertEqual(due[0]["due_date"], "2024-07-15")
        self.db.remove_client_identity(client_id, "0001234567", "admin_a",
                                       today=datetime.date(2024, 7, 15))
        self.assertIsNone(self.db.get_pantry_client(client_id))
        self.assertEqual(self.db.get_monthly_service_summary("2024-01")["visits"], 0)

    def test_duplicate_id_and_expired_verification_block_eligibility(self):
        client_id = self.create_client()
        with self.assertRaises(ValueError):
            self.db.register_pantry_client(
                " 0001234567 ", "Other", "Person", "2002-01-01", "Spring 2027",
                "part_time", "admin_a",
            )
        overly_long = (datetime.date.today() + datetime.timedelta(days=400)).isoformat()
        with self.assertRaises(ValueError):
            self.db.verify_client_term(client_id, "Fall 2026", overly_long, "admin_a")
        expiry = (datetime.date.today() + datetime.timedelta(days=10)).isoformat()
        self.db.verify_client_term(client_id, "Fall 2026", expiry, "admin_a")
        conn = self.db._connect()
        conn.execute("UPDATE client_verifications SET verified_until = '2000-01-01'")
        conn.commit()
        conn.close()
        self.assertFalse(self.db.is_client_eligible(client_id))


if __name__ == "__main__":
    unittest.main()
