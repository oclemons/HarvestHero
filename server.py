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

import json
import os

from flask import Flask, jsonify, request

from database import Database

app = Flask(__name__)

# Load config for port
_cfg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
_cfg = {}
if os.path.exists(_cfg_path):
    with open(_cfg_path) as _f:
        _cfg = json.load(_f)

HOST = _cfg.get("server_host", "0.0.0.0")
PORT = int(_cfg.get("server_port", 5000))

db = Database()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def ok(data=None):
    return jsonify({"ok": True, "data": data})


def err(msg, status=400):
    return jsonify({"ok": False, "error": msg}), status


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
def api_create_user():
    d = request.get_json()
    success, msg = db.create_user(
        d["username"], d["password_hash"], d["salt"], d["role"]
    )
    return ok(msg) if success else err(msg)


@app.put("/api/users/<int:uid>/role")
def api_update_role(uid):
    d = request.get_json()
    db.update_user_role(uid, d["role"])
    return ok()


@app.put("/api/users/<int:uid>/password")
def api_update_password(uid):
    d = request.get_json()
    db.update_user_password(uid, d["password_hash"], d["salt"])
    return ok()


@app.put("/api/users/<int:uid>/active")
def api_set_active(uid):
    d = request.get_json()
    db.set_user_active(uid, d["active"])
    return ok()


@app.post("/api/users/full")
def api_create_user_full():
    d = request.get_json()
    success, msg = db.create_user_full(
        d["username"], d["password_hash"], d["salt"], d["role"],
        d.get("full_name", ""), d.get("created_by", ""),
    )
    return ok(msg) if success else err(msg)


@app.put("/api/users/<int:uid>/fullname")
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
    )
    return ok(msg) if success else err(msg)


@app.put("/api/items/<int:item_id>/extended")
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
    days = int(request.args.get("days", 30))
    return ok(db.get_expiring_items(days))


@app.get("/api/items/expired")
def api_expired():
    return ok(db.get_expired_items())


@app.get("/api/stats")
def api_stats():
    return ok(db.get_stats())


@app.put("/api/items/<int:item_id>")
def api_update_item(item_id):
    d = request.get_json()
    db.update_item(
        item_id, d["item_name"], d["category"],
        d["minimum_stock"], d["notes"],
        d.get("barcode_out", ""),
    )
    return ok()


@app.put("/api/items/<int:item_id>/stock")
def api_set_stock(item_id):
    d = request.get_json()
    db.set_stock(item_id, d["quantity"])
    return ok()


@app.patch("/api/items/adjust")
def api_adjust_stock():
    d = request.get_json()
    db.adjust_stock(d["barcode"], d["delta"])
    return ok()


@app.delete("/api/items/<int:item_id>")
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
    limit = int(request.args.get("limit", 20))
    return ok(db.get_recent_transactions(limit))


# ---------------------------------------------------------------------------
# App settings
# ---------------------------------------------------------------------------

@app.get("/api/settings")
def api_get_setting():
    return ok(db.get_app_setting(request.args.get("key", "")))


@app.put("/api/settings")
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
    limit = int(request.args.get("limit", 100))
    return ok(db.get_activity_log(limit))


@app.post("/api/activity/clear")
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
    )
    return ok()


@app.post("/api/pantry-clients/<int:client_id>/active")
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
    limit = int(request.args.get("limit", 20))
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
    print("=" * 55)
    print("  Inventory Control Center — LAN Server")
    print(f"  Listening on  http://{HOST}:{PORT}")
    print()
    print("  Share your local IP with client PCs.")
    print("  Windows: run  ipconfig  in a terminal.")
    print("  Mac/Linux: run  ifconfig  or  ip addr")
    print("=" * 55)
    app.run(host=HOST, port=PORT, debug=False)
