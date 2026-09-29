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
        for path in ("/clients/", "/clients/new", f"/clients/{client_id}",
                     f"/clients/{client_id}/edit", "/scan/out"):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 503, path)
            self.assertNotIn(b"0001234567", response.data)
        for path in ("/clients/new", f"/clients/{client_id}/verify", "/scan/out/start"):
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

    def test_deactivation_revokes_verification_until_rechecked(self):
        client_id = self.create_client()
        expiry = (datetime.date.today() + datetime.timedelta(days=100)).isoformat()
        self.db.verify_client_term(client_id, "Fall 2026", expiry, "admin_a")
        self.login("admin_a")
        self.client.post(f"/clients/{client_id}/status", data={"active": "0"})
        self.assertFalse(self.db.is_client_eligible(client_id))
        self.client.post(f"/clients/{client_id}/status", data={"active": "1"})
        self.assertFalse(self.db.is_client_eligible(client_id))

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
