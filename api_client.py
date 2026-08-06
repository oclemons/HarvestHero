"""
api_client.py
-------------
Drop-in replacement for Database that talks to server.py over HTTP.
Implements the same public interface so the rest of the app is unchanged.
"""

from typing import Optional

import requests


class ConnectionError(Exception):
    pass


class ApiClient:
    def __init__(self, server_url: str, api_key: str = ""):
        self.base = server_url.rstrip("/")
        self._session = requests.Session()
        if api_key:
            self._session.headers.update({"Authorization": f"Bearer {api_key}"})

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get(self, path: str, params: dict = None):
        try:
            r = self._session.get(self.base + path, params=params, timeout=6)
            self._check_status(r)
            return r.json().get("data")
        except requests.exceptions.ConnectionError:
            raise ConnectionError(
                f"Cannot reach server at {self.base}.\n"
                "Check that server.py is running on the host PC and config.json has the correct IP."
            )

    def _post(self, path: str, payload: dict = None):
        try:
            r = self._session.post(self.base + path, json=payload or {}, timeout=6)
            self._check_status(r)
            body = r.json()
            if not body.get("ok"):
                return False, body.get("error", "Unknown error")
            return True, body.get("data", "")
        except requests.exceptions.ConnectionError:
            raise ConnectionError(f"Cannot reach server at {self.base}.")

    def _put(self, path: str, payload: dict = None):
        try:
            r = self._session.put(self.base + path, json=payload or {}, timeout=6)
            self._check_status(r)
        except requests.exceptions.ConnectionError:
            raise ConnectionError(f"Cannot reach server at {self.base}.")

    def _patch(self, path: str, payload: dict = None):
        try:
            r = self._session.patch(self.base + path, json=payload or {}, timeout=6)
            self._check_status(r)
        except requests.exceptions.ConnectionError:
            raise ConnectionError(f"Cannot reach server at {self.base}.")

    def _delete(self, path: str):
        try:
            r = self._session.delete(self.base + path, timeout=6)
            self._check_status(r)
        except requests.exceptions.ConnectionError:
            raise ConnectionError(f"Cannot reach server at {self.base}.")

    def _check_status(self, r):
        if r.status_code == 401:
            raise ConnectionError("Invalid or missing API token.")
        r.raise_for_status()

    # ------------------------------------------------------------------
    # User operations
    # ------------------------------------------------------------------

    def create_user(self, username, password_hash, salt, role):
        return self._post("/api/users", {
            "username": username, "password_hash": password_hash,
            "salt": salt, "role": role,
        })

    def create_user_full(self, username, password_hash, salt, role,
                         full_name="", created_by=""):
        return self._post("/api/users/full", {
            "username": username, "password_hash": password_hash,
            "salt": salt, "role": role,
            "full_name": full_name, "created_by": created_by,
        })

    def get_user(self, username: str):
        return self._get("/api/user", {"username": username})

    def get_all_users(self):
        return self._get("/api/users") or []

    def update_user_role(self, user_id: int, role: str):
        self._put(f"/api/users/{user_id}/role", {"role": role})

    def update_user_password(self, user_id: int, password_hash: str, salt: str):
        self._put(f"/api/users/{user_id}/password",
                  {"password_hash": password_hash, "salt": salt})

    def set_user_active(self, user_id: int, active: bool):
        self._put(f"/api/users/{user_id}/active", {"active": active})

    def update_user_full_name(self, user_id: int, full_name: str):
        self._put(f"/api/users/{user_id}/fullname", {"full_name": full_name})

    def update_last_login(self, username: str):
        self._put("/api/users/lastlogin", {"username": username})

    def set_tour_complete(self, user_id: int):
        self._put(f"/api/users/{user_id}/tour", {})

    # ------------------------------------------------------------------
    # Inventory operations
    # ------------------------------------------------------------------

    def add_item(self, barcode, item_name, category, quantity,
                 minimum_stock, notes, barcode_out="",
                 brand="", storage_location="",
                 shelf_life_days=0, expiration_date="", nutrition_data="{}"):
        return self._post("/api/items", {
            "barcode": barcode, "item_name": item_name, "category": category,
            "quantity": quantity, "minimum_stock": minimum_stock,
            "notes": notes, "barcode_out": barcode_out,
            "brand": brand, "storage_location": storage_location,
            "shelf_life_days": shelf_life_days,
            "expiration_date": expiration_date,
        })

    def get_item_by_barcode(self, barcode: str):
        return self._get(f"/api/items/barcode/{barcode}")

    def get_item_by_any_barcode(self, barcode: str):
        result = self._get(f"/api/items/anybarcode/{barcode}")
        if result:
            return result.get("item"), result.get("direction")
        return None, None

    def get_all_items(self, search: str = ""):
        return self._get("/api/items", {"search": search}) or []

    def update_item(self, item_id, item_name, category,
                    minimum_stock, notes, barcode_out=""):
        self._put(f"/api/items/{item_id}", {
            "item_name": item_name, "category": category,
            "minimum_stock": minimum_stock, "notes": notes,
            "barcode_out": barcode_out,
        })

    def update_item_extended(self, item_id, brand="", storage_location="",
                             shelf_life_days=0, expiration_date="",
                             nutrition_data="{}"):
        self._put(f"/api/items/{item_id}/extended", {
            "brand": brand, "storage_location": storage_location,
            "shelf_life_days": shelf_life_days,
            "expiration_date": expiration_date,
            "nutrition_data": nutrition_data,
        })

    def set_stock(self, item_id: int, quantity: int):
        self._put(f"/api/items/{item_id}/stock", {"quantity": quantity})

    def adjust_stock(self, barcode: str, delta: int):
        self._patch("/api/items/adjust", {"barcode": barcode, "delta": delta})

    def delete_item(self, item_id: int):
        self._delete(f"/api/items/{item_id}")

    def get_low_stock_count(self) -> int:
        return self._get("/api/items/lowstockcount") or 0

    def get_low_stock_items(self):
        return self._get("/api/items/lowstock") or []

    def get_out_of_stock_items(self):
        return self._get("/api/items/outofstock") or []

    def get_expiring_items(self, days: int = 30):
        return self._get("/api/items/expiring", {"days": days}) or []

    def get_expired_items(self):
        return self._get("/api/items/expired") or []

    def get_stats(self) -> dict:
        return self._get("/api/stats") or {}

    def get_recent_transactions(self, limit: int = 20):
        return self._get("/api/transactions/recent", {"limit": limit}) or []

    # ------------------------------------------------------------------
    # Transaction operations
    # ------------------------------------------------------------------

    def add_transaction(self, transaction_type, barcode, item_name,
                        category, quantity, recipient, username, notes=""):
        self._post("/api/transactions", {
            "transaction_type": transaction_type, "barcode": barcode,
            "item_name": item_name, "category": category, "quantity": quantity,
            "recipient": recipient, "username": username, "notes": notes,
        })

    def get_transactions(self, search="", trans_type="",
                         date_from="", date_to="", recipient=""):
        return self._get("/api/transactions", {
            "search": search, "trans_type": trans_type,
            "date_from": date_from, "date_to": date_to,
            "recipient": recipient,
        }) or []

    # ------------------------------------------------------------------
    # App settings
    # ------------------------------------------------------------------

    def get_app_setting(self, key: str):
        return self._get("/api/settings", {"key": key})

    def set_app_setting(self, key: str, value: str):
        self._put("/api/settings", {"key": key, "value": value})

    # ------------------------------------------------------------------
    # Activity log
    # ------------------------------------------------------------------

    def log_activity(self, username: str, action: str, detail: str = ""):
        self._post("/api/activity", {
            "username": username, "action": action, "detail": detail,
        })

    def get_activity_log(self, limit: int = 100):
        return self._get("/api/activity", {"limit": limit}) or []

    def clear_activity_log(self, older_than_days: int = None):
        payload = {}
        if older_than_days is not None:
            payload["older_than_days"] = older_than_days
        ok, data = self._post("/api/activity/clear", payload)
        return (data or {}).get("deleted", 0) if ok else 0

    # ------------------------------------------------------------------
    # Shopping list
    # ------------------------------------------------------------------

    def get_shopping_list(self):
        return self._get("/api/shopping-list") or []

    def update_shopping_list_quantity(self, item_id: int, quantity: int):
        self._post("/api/shopping-list/update",
                    {"id": item_id, "quantity": quantity})

    def remove_shopping_list_item(self, item_id: int):
        self._post("/api/shopping-list/remove", {"id": item_id})

    def clear_shopping_list(self):
        self._post("/api/shopping-list/clear", {})

    # ------------------------------------------------------------------
    # Pantry clients (student profiles)
    # ------------------------------------------------------------------

    def create_pantry_client(self, first_name, last_name, student_id="",
                              email="", phone="", semester="",
                              enrollment_status="full_time",
                              household_size=1, notes=""):
        ok, data = self._post("/api/pantry-clients", {
            "first_name": first_name, "last_name": last_name,
            "student_id": student_id, "email": email, "phone": phone,
            "semester": semester, "enrollment_status": enrollment_status,
            "household_size": household_size, "notes": notes,
        })
        return (data or {}).get("id") if ok else None

    def update_pantry_client(self, client_id, first_name, last_name,
                              student_id="", email="", phone="", semester="",
                              enrollment_status="full_time",
                              household_size=1, notes=""):
        self._post(f"/api/pantry-clients/{client_id}/update", {
            "first_name": first_name, "last_name": last_name,
            "student_id": student_id, "email": email, "phone": phone,
            "semester": semester, "enrollment_status": enrollment_status,
            "household_size": household_size, "notes": notes,
        })

    def set_pantry_client_active(self, client_id: int, active: bool):
        self._post(f"/api/pantry-clients/{client_id}/active", {"active": active})

    def get_all_pantry_clients(self, search: str = ""):
        return self._get("/api/pantry-clients", {"search": search}) or []

    def get_pantry_client(self, client_id: int):
        return self._get(f"/api/pantry-clients/{client_id}")

    # ------------------------------------------------------------------
    # Pantry visits
    # ------------------------------------------------------------------

    def record_pantry_visit(self, client_id, pounds_received,
                            recorded_by, notes=""):
        ok, data = self._post(f"/api/pantry-clients/{client_id}/visits", {
            "pounds_received": pounds_received,
            "recorded_by": recorded_by, "notes": notes,
        })
        return (data or {}).get("id") if ok else None

    def get_client_visits(self, client_id: int):
        return self._get(f"/api/pantry-clients/{client_id}/visits") or []

    def get_visit_count_since(self, client_id: int, since_iso_date: str) -> int:
        return self._get(f"/api/pantry-clients/{client_id}/visit-count",
                          {"since": since_iso_date}) or 0

    def get_client_visit_stats(self, client_id: int) -> dict:
        return self._get(f"/api/pantry-clients/{client_id}/visit-stats") or {
            "total_visits": 0, "total_pounds": 0, "last_visit": None}

    def get_recent_pantry_visits(self, limit: int = 20):
        return self._get("/api/visits/recent", {"limit": limit}) or []

    # ------------------------------------------------------------------
    # Client registration (managed server-side; stubs for client mode)
    # ------------------------------------------------------------------

    def upsert_client(self, machine_id: str, hostname: str = "",
                      ip_address: str = ""):
        return self._post("/api/clients", {
            "machine_id": machine_id,
            "hostname": hostname,
            "ip_address": ip_address,
        })

    def get_all_clients(self):
        return self._get("/api/clients") or []

    def set_client_approved(self, machine_id: str, approved: bool,
                            approved_by: str = ""):
        self._put(f"/api/clients/{machine_id}/approve", {
            "approved": approved, "approved_by": approved_by,
        })

    def is_client_approved(self, machine_id: str) -> bool:
        result = self._get(f"/api/clients/{machine_id}/approved")
        return bool(result)
