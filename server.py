"""
server.py
---------
Run this on the HOST (server) PC on your local network.

    python server.py

All other PCs set config.json to:
    { "mode": "client", "server_url": "http://<THIS_PC_IP>:5000" }

Find this PC's IP on Windows:  ipconfig
Find this PC's IP on Mac/Linux: ifconfig  or  ip addr
"""

import functools
import hmac
import json
import os
import secrets

from flask import Flask, g, jsonify, request

from database import Database

app = Flask(__name__)

# Load config for port
from paths import USER_DIR
_cfg_path = os.path.join(USER_DIR, "config.json")
_cfg = {}
if os.path.exists(_cfg_path):
    with open(_cfg_path) as _f:
        _cfg = json.load(_f)

HOST = _cfg.get("server_host", "0.0.0.0")
PORT = int(_cfg.get("server_port", 5000))

db = Database()


def _ensure_token(key: str) -> str:
    """Return the persistent API token for `key`, creating one if it doesn't
    exist. Two tokens are stored: `api_token` (staff-level, day-to-day
    scanning) and `admin_api_token` (grants everything staff can do PLUS
    admin operations like user management)."""
    token = db.get_app_setting(key)
    if not token:
        token = secrets.token_urlsafe(32)
        db.set_app_setting(key, token)
    return token


STAFF_TOKEN = _ensure_token("api_token")
ADMIN_TOKEN = _ensure_token("admin_api_token")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def ok(data=None):
    return jsonify({"ok": True, "data": data})


def err(msg, status=400):
    return jsonify({"ok": False, "error": msg}), status


def _int_arg(name: str, default: int, low: int | None = None,
             high: int | None = None) -> int:
    """Parse an integer query parameter defensively.

    Non-numeric or out-of-range values fall back to `default` instead of
    letting int() raise ValueError and returning a 500 to the client.
    """
    raw = request.args.get(name)
    if raw is None or raw == "":
        return default
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return default
    if low is not None and value < low:
        return low
    if high is not None and value > high:
        return high
    return value


# ---------------------------------------------------------------------------
# Authentication + CSRF protection
# ---------------------------------------------------------------------------
#
# The HarvestHero API is a JSON-only service consumed by the desktop client
# (api_client.py). Browsers should never talk to it. We defend against CSRF
# with three overlapping controls:
#
#   1. Bearer token auth on every endpoint (already required below).
#   2. State-changing verbs must send JSON, not form data. Browsers can
#      forge a form POST cross-origin, but not application/json.
#   3. All non-health requests must carry X-Requested-With: HarvestHero.
#      This forces browsers to preflight the request, which our missing
#      CORS headers will then block.
#
# All three fail closed.
#
# ---------------------------------------------------------------------------

_UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
_XRW_HEADER    = "X-Requested-With"
_XRW_EXPECTED  = "HarvestHero"


@app.before_request
def enforce_auth_and_csrf():
    """Reject unauthenticated or CSRF-suspicious requests.

    Sets g.role to "admin" or "staff" based on which token was
    presented. Endpoints decorated with @admin_required will reject
    anything that isn't "admin".
    """
    if request.path == "/api/health":
        return None

    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return err("Unauthorized — provide a valid Authorization: Bearer <token> header", 401)

    presented = auth[7:]
    if hmac.compare_digest(presented, ADMIN_TOKEN):
        g.role = "admin"
    elif hmac.compare_digest(presented, STAFF_TOKEN):
        g.role = "staff"
    else:
        return err("Unauthorized — provide a valid Authorization: Bearer <token> header", 401)

    if request.headers.get(_XRW_HEADER, "") != _XRW_EXPECTED:
        return err("Forbidden — missing or invalid X-Requested-With header", 403)

    if request.method in _UNSAFE_METHODS:
        ctype = (request.headers.get("Content-Type") or "").split(";", 1)[0].strip().lower()
        if ctype and ctype != "application/json":
            return err("Unsupported Media Type — Content-Type must be application/json", 415)


def admin_required(fn):
    """Reject non-admin callers with 403. Applied to endpoints that
    would let a staff-token holder escalate privileges or destroy data
    (user management, item deletion, activity-log wipe, etc.)."""

    @functools.wraps(fn)
    def _wrapped(*args, **kwargs):
        if getattr(g, "role", None) != "admin":
            return err("Forbidden — admin token required for this operation", 403)
        return fn(*args, **kwargs)

    return _wrapped


@app.after_request
def no_cors(resp):
    """Strip any implicit CORS allowances; browsers should never be able to
    reach this API cross-origin."""
    resp.headers["Vary"] = "Origin"
    return resp


@app.get("/api/health")
def api_health():
    return ok("healthy")


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

@app.get("/api/user")
def api_get_user():
    username = request.args.get("username", "")
    return ok(db.get_user(username))


@app.get("/api/users")
def api_get_all_users():
    return ok(db.get_all_users())


@app.post("/api/users")
@admin_required
def api_create_user():
    d = request.get_json()
    success, msg = db.create_user(
        d["username"], d["password_hash"], d["salt"], d["role"]
    )
    return ok(msg) if success else err(msg)


@app.put("/api/users/<int:uid>/role")
@admin_required
def api_update_role(uid):
    d = request.get_json()
    db.update_user_role(uid, d["role"])
    return ok()


@app.put("/api/users/<int:uid>/password")
@admin_required
def api_update_password(uid):
    d = request.get_json()
    db.update_user_password(uid, d["password_hash"], d["salt"])
    return ok()


@app.put("/api/users/<int:uid>/active")
@admin_required
def api_set_active(uid):
    d = request.get_json()
    db.set_user_active(uid, d["active"])
    return ok()


@app.post("/api/users/full")
@admin_required
def api_create_user_full():
    d = request.get_json()
    success, msg = db.create_user_full(
        d["username"], d["password_hash"], d["salt"], d["role"],
        d.get("full_name", ""), d.get("created_by", ""),
    )
    return ok(msg) if success else err(msg)


@app.put("/api/users/<int:uid>/fullname")
@admin_required
def api_update_fullname(uid):
    d = request.get_json()
    db.update_user_full_name(uid, d["full_name"])
    return ok()


@app.put("/api/users/lastlogin")
def api_update_lastlogin():
    d = request.get_json()
    db.update_last_login(d["username"])
    return ok()


@app.put("/api/users/<int:uid>/tour")
def api_set_tour(uid):
    db.set_tour_complete(uid)
    return ok()


# ---------------------------------------------------------------------------
# Inventory items
# ---------------------------------------------------------------------------

@app.get("/api/items")
def api_get_items():
    search = request.args.get("search", "")
    return ok(db.get_all_items(search))


@app.get("/api/items/<int:item_id>")
def api_get_item_by_id(item_id):
    return ok(db.get_item_by_id(item_id))


@app.get("/api/items/barcode/<barcode>")
def api_get_by_barcode(barcode):
    return ok(db.get_item_by_barcode(barcode))


@app.get("/api/items/anybarcode/<barcode>")
def api_get_by_any_barcode(barcode):
    item, direction = db.get_item_by_any_barcode(barcode)
    return ok({"item": item, "direction": direction})


@app.get("/api/items/lowstock")
def api_low_stock():
    return ok(db.get_low_stock_items())


@app.get("/api/items/lowstockcount")
def api_low_stock_count():
    return ok(db.get_low_stock_count())


@app.get("/api/items/outofstock")
def api_out_of_stock():
    return ok(db.get_out_of_stock_items())


@app.post("/api/items")
@admin_required
def api_add_item():
    d = request.get_json()
    success, msg = db.add_item(
        d["barcode"], d["item_name"], d["category"],
        d["quantity"], d["minimum_stock"], d["notes"],
        d.get("barcode_out", ""),
        brand=d.get("brand", ""),
        storage_location=d.get("storage_location", ""),
        shelf_life_days=int(d.get("shelf_life_days", 0) or 0),
        expiration_date=d.get("expiration_date", ""),
        nutrition_data=d.get("nutrition_data", "{}"),
    )
    return ok(msg) if success else err(msg)


@app.put("/api/items/<int:item_id>/extended")
@admin_required
def api_update_item_extended(item_id):
    d = request.get_json()
    db.update_item_extended(
        item_id,
        brand=d.get("brand", ""),
        storage_location=d.get("storage_location", ""),
        shelf_life_days=int(d.get("shelf_life_days", 0) or 0),
        expiration_date=d.get("expiration_date", ""),
        nutrition_data=d.get("nutrition_data", "{}"),
    )
    return ok()


@app.get("/api/items/expiring")
def api_expiring():
    days = _int_arg("days", default=30, low=0, high=3650)
    return ok(db.get_expiring_items(days))


@app.get("/api/items/expired")
def api_expired():
    return ok(db.get_expired_items())


@app.get("/api/stats")
def api_stats():
    return ok(db.get_stats())


@app.put("/api/items/<int:item_id>")
@admin_required
def api_update_item(item_id):
    d = request.get_json()
    db.update_item(
        item_id, d["item_name"], d["category"],
        d["minimum_stock"], d["notes"],
        d.get("barcode_out", ""),
    )
    return ok()


@app.put("/api/items/<int:item_id>/stock")
@admin_required
def api_set_stock(item_id):
    d = request.get_json()
    db.set_stock(item_id, d["quantity"])
    return ok()


@app.patch("/api/items/adjust")
def api_adjust_stock():
    # Staff-allowed: scan-in / scan-out call this with delta ±1.
    d = request.get_json()
    db.adjust_stock(d["barcode"], d["delta"])
    return ok()


@app.delete("/api/items/<int:item_id>")
@admin_required
def api_delete_item(item_id):
    db.delete_item(item_id)
    return ok()


# ---------------------------------------------------------------------------
# Transactions
# ---------------------------------------------------------------------------

@app.post("/api/transactions")
def api_add_transaction():
    d = request.get_json()
    db.add_transaction(
        d["transaction_type"], d["barcode"], d["item_name"],
        d["category"], d["quantity"], d["recipient"],
        d["username"], d.get("notes", ""),
    )
    return ok()


@app.get("/api/transactions")
def api_get_transactions():
    return ok(db.get_transactions(
        request.args.get("search", ""),
        request.args.get("trans_type", ""),
        request.args.get("date_from", ""),
        request.args.get("date_to", ""),
        request.args.get("recipient", ""),
    ))


@app.get("/api/transactions/recent")
def api_recent_transactions():
    limit = _int_arg("limit", default=20, low=1, high=1000)
    return ok(db.get_recent_transactions(limit))


# ---------------------------------------------------------------------------
# App settings
# ---------------------------------------------------------------------------

@app.get("/api/settings")
def api_get_setting():
    return ok(db.get_app_setting(request.args.get("key", "")))


@app.put("/api/settings")
@admin_required
def api_set_setting():
    d = request.get_json()
    db.set_app_setting(d["key"], d["value"])
    return ok()


# ---------------------------------------------------------------------------
# Activity log
# ---------------------------------------------------------------------------

@app.post("/api/activity")
def api_log_activity():
    d = request.get_json()
    db.log_activity(d["username"], d["action"], d.get("detail", ""))
    return ok()


@app.get("/api/activity")
def api_get_activity():
    limit = _int_arg("limit", default=100, low=1, high=5000)
    return ok(db.get_activity_log(limit))


@app.post("/api/activity/clear")
@admin_required
def api_clear_activity():
    d = request.get_json(silent=True) or {}
    older_than_days = d.get("older_than_days")
    deleted = db.clear_activity_log(older_than_days)
    return ok({"deleted": deleted})


# ---------------------------------------------------------------------------
# Shopping list
# ---------------------------------------------------------------------------

@app.get("/api/shopping-list")
def api_get_shopping_list():
    return ok(db.get_shopping_list())


@app.post("/api/shopping-list/update")
def api_update_shopping_list():
    d = request.get_json()
    db.update_shopping_list_quantity(d["id"], d["quantity"])
    return ok()


@app.post("/api/shopping-list/remove")
def api_remove_shopping_list_item():
    d = request.get_json()
    db.remove_shopping_list_item(d["id"])
    return ok()


@app.post("/api/shopping-list/clear")
def api_clear_shopping_list():
    db.clear_shopping_list()
    return ok()


# ---------------------------------------------------------------------------
# Pantry clients (student profiles) — distinct from machine-registration
# "/api/clients" routes below.
# ---------------------------------------------------------------------------

@app.post("/api/pantry-clients")
def api_create_pantry_client():
    d = request.get_json()
    new_id = db.create_pantry_client(
        d["first_name"], d["last_name"], d.get("student_id", ""),
        d.get("email", ""), d.get("phone", ""), d.get("semester", ""),
        d.get("enrollment_status", "full_time"),
        d.get("household_size", 1), d.get("notes", ""),
        int(d.get("waiver_signed", 0) or 0),
        int(d.get("locker_waiver_signed", 0) or 0),
    )
    return ok({"id": new_id})


@app.post("/api/pantry-clients/<int:client_id>/update")
def api_update_pantry_client(client_id):
    d = request.get_json()
    db.update_pantry_client(
        client_id, d["first_name"], d["last_name"], d.get("student_id", ""),
        d.get("email", ""), d.get("phone", ""), d.get("semester", ""),
        d.get("enrollment_status", "full_time"),
        d.get("household_size", 1), d.get("notes", ""),
        int(d.get("waiver_signed", 0) or 0),
        int(d.get("locker_waiver_signed", 0) or 0),
    )
    return ok()


@app.post("/api/pantry-clients/<int:client_id>/active")
@admin_required
def api_set_pantry_client_active(client_id):
    d = request.get_json()
    db.set_pantry_client_active(client_id, bool(d.get("active", True)))
    return ok()


@app.get("/api/pantry-clients")
def api_get_all_pantry_clients():
    search = request.args.get("search", "")
    return ok(db.get_all_pantry_clients(search))


@app.get("/api/pantry-clients/<int:client_id>")
def api_get_pantry_client(client_id):
    return ok(db.get_pantry_client(client_id))


@app.post("/api/pantry-clients/<int:client_id>/visits")
def api_record_pantry_visit(client_id):
    d = request.get_json()
    new_id = db.record_pantry_visit(
        client_id, d["pounds_received"], d.get("recorded_by", ""),
        d.get("notes", ""))
    return ok({"id": new_id})


@app.get("/api/pantry-clients/<int:client_id>/visits")
def api_get_client_visits(client_id):
    return ok(db.get_client_visits(client_id))


@app.get("/api/pantry-clients/<int:client_id>/visit-count")
def api_get_visit_count_since(client_id):
    since = request.args.get("since", "")
    return ok(db.get_visit_count_since(client_id, since))


@app.get("/api/pantry-clients/<int:client_id>/visit-stats")
def api_get_client_visit_stats(client_id):
    return ok(db.get_client_visit_stats(client_id))


@app.get("/api/visits/recent")
def api_get_recent_pantry_visits():
    limit = _int_arg("limit", default=20, low=1, high=1000)
    return ok(db.get_recent_pantry_visits(limit))


# ---------------------------------------------------------------------------
# Client registration
# ---------------------------------------------------------------------------

@app.post("/api/clients")
def api_upsert_client():
    d = request.get_json()
    db.upsert_client(
        d["machine_id"],
        d.get("hostname", ""),
        d.get("ip_address", ""),
    )
    return ok()


@app.get("/api/clients")
def api_get_clients():
    return ok(db.get_all_clients())


@app.put("/api/clients/<machine_id>/approve")
@admin_required
def api_approve_client(machine_id):
    d = request.get_json()
    db.set_client_approved(
        machine_id, d["approved"], d.get("approved_by", "")
    )
    return ok()


@app.get("/api/clients/<machine_id>/approved")
def api_is_client_approved(machine_id):
    return ok(db.is_client_approved(machine_id))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 65)
    print("  Inventory Control Center — LAN Server")
    print(f"  Listening on  http://{HOST}:{PORT}")
    print()
    print("  There are TWO tokens. Give each client PC exactly one, based")
    print("  on the role of the user who will sit in front of it.")
    print()
    print(f"  Staff token (scanning, transactions, view inventory):")
    print(f"    {STAFF_TOKEN}")
    print()
    print(f"  Admin token (everything staff can do PLUS user management,")
    print(f"  add/edit/delete inventory, settings, client approvals):")
    print(f"    {ADMIN_TOKEN}")
    print()
    print("  Windows: run  ipconfig  in a terminal.")
    print("  Mac/Linux: run  ifconfig  or  ip addr")
    print("=" * 65)
    app.run(host=HOST, port=PORT, debug=False)
