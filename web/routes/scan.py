"""Server-owned intake carts and Admin-only visitor distribution sessions."""

from decimal import Decimal, InvalidOperation
from uuid import uuid4

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required

from decorators import admin_required, student_or_admin_required

bp = Blueprint("scan", __name__, url_prefix="/scan")


@bp.after_request
def _no_store_distribution(response):
    if request.path.startswith("/scan/out"):
        response.headers["Cache-Control"] = "private, no-store"
    return response


@bp.before_request
def _require_policy_for_distribution():
    # Client-visit routes still need CLIENT_RECORDS_ENABLED; but the basic
    # scan-out page and add/remove/complete/cancel work without it.
    if (current_user.is_authenticated and current_user.is_admin and
            not current_app.config.get("CLIENT_RECORDS_ENABLED", False) and
            (request.path == "/scan/out/start" or
             request.path.startswith("/scan/out/undo"))):
        abort(503)


@bp.route("/in")
@login_required
@student_or_admin_required
def scan_in():
    from database import Database
    db = Database()
    return render_template("scan/in.html", sections=db.get_pantry_layout(),
                           selected_shelf_id=session.get("last_intake_shelf"),
                           cart=db.get_active_cart(int(current_user.id), "IN"))


@bp.route("/in/add", methods=["POST"])
@login_required
@student_or_admin_required
def add_in():
    from database import Database
    try:
        shelf_raw = (request.form.get("shelf_id") or "").strip()
        shelf_id = int(shelf_raw) if shelf_raw else None
        Database().add_scan_to_cart(int(current_user.id), request.form.get("barcode") or "",
                                    shelf_id, current_user.username)
        if shelf_id:
            session["last_intake_shelf"] = shelf_id
        return redirect(url_for("scan.scan_in") + "?scanned=ok")
    except ValueError as error:
        flash(str(error), "error")
    return redirect(url_for("scan.scan_in") + "?scanned=fail")


@bp.route("/in/remove/<int:line_id>", methods=["POST"])
@login_required
@student_or_admin_required
def remove_in(line_id: int):
    from database import Database
    try:
        Database().remove_cart_line(int(current_user.id), line_id, username=current_user.username)
    except ValueError as error:
        flash(str(error), "error")
    return redirect(url_for("scan.scan_in"))


@bp.route("/in/complete", methods=["POST"])
@login_required
@student_or_admin_required
def complete_in():
    from database import Database
    db = Database()
    cart_id = request.form.get("cart_id") or ""
    session_weight = _parse_session_weight(request.form.get("session_weight_lb"))
    try:
        receipt = db.complete_scan_in_cart(int(current_user.id), cart_id,
                                           current_user.username, session_weight)
    except ValueError as error:
        flash(str(error), "error")
        return redirect(url_for("scan.scan_in"))
    return redirect(url_for("scan.intake_receipt", cart_id=receipt["id"]))


@bp.route("/in/cancel", methods=["POST"])
@login_required
@student_or_admin_required
def cancel_in():
    from database import Database
    try:
        Database().cancel_scan_cart(int(current_user.id), request.form.get("cart_id") or "",
                                    username=current_user.username)
        flash("Cart cancelled; scanned items were removed from inventory.", "info")
    except ValueError as error:
        flash(str(error), "error")
    return redirect(url_for("scan.scan_in"))


@bp.route("/in/receipt/<cart_id>")
@login_required
@student_or_admin_required
def intake_receipt(cart_id: str):
    from database import Database
    receipt = Database().get_cart_receipt(int(current_user.id), cart_id)
    if not receipt:
        abort(404)
    return render_template("scan/receipt.html", receipt=receipt)


@bp.route("/out")
@login_required
@admin_required
def scan_out():
    from database import Database
    db = Database()
    # Check for a client-visit cart first
    cart = db.get_active_cart(int(current_user.id), "OUT")
    client_records = current_app.config.get("CLIENT_RECORDS_ENABLED", False)
    # If there's a non-client cart (simple scan-out), use it
    client = None
    people = []
    stats = None
    if cart and cart.get("client_id"):
        client = db.get_pantry_client(cart["client_id"])
        stats = db.get_client_weight_summary(cart["client_id"])
    elif not cart and client_records:
        people = db.list_private_clients()
        for person in people:
            person["allowance"] = db.get_client_visit_allowance(person["id"])
            person["eligible"] = person["allowance"]["remaining"] > 0
    return render_template("scan/out.html", cart=cart, client=client, clients=people,
                           scan_token=uuid4().hex, stats=stats,
                           client_records=client_records,
                           sections=db.get_pantry_layout())


@bp.route("/out/start", methods=["POST"])
@login_required
@admin_required
def start_out():
    from database import Database
    try:
        client_id = int(request.form.get("client_id") or "")
        Database().start_scan_out_cart(int(current_user.id), client_id,
                                       request.form.get("mode") or "REVIEW",
                                       request.form.get("fulfillment_type") or "in_person")
    except ValueError as error:
        flash(str(error) if request.form.get("client_id") else "Choose a verified client.", "error")
    return redirect(url_for("scan.scan_out"))


@bp.route("/out/add", methods=["POST"])
@login_required
@admin_required
def add_out():
    from database import Database
    db = Database()
    try:
        shelf_raw = (request.form.get("shelf_id") or "").strip()
        shelf_id = int(shelf_raw) if shelf_raw else None
        cart = db.get_active_cart(int(current_user.id), "OUT")
        if cart and cart.get("client_id"):
            # Client-visit mode
            if cart["mode"] == "IMMEDIATE":
                db.record_immediate_scan_out(
                    int(current_user.id), request.form.get("barcode") or "", shelf_id,
                    current_user.username, request.form.get("scan_token") or "",
                )
                flash("Item scanned out and recorded in this customer's visit.", "success")
            else:
                db.add_scan_out_to_cart(
                    int(current_user.id), request.form.get("barcode") or "", shelf_id
                )
        else:
            # Simple scan-out: no client visit, just deduct stock
            db.scan_out_from_cart(
                int(current_user.id), request.form.get("barcode") or "",
                shelf_id, current_user.username,
            )
            flash("Item scanned out. Stock deducted from shelf.", "success")
        return redirect(url_for("scan.scan_out") + "?scanned=ok")
    except ValueError as error:
        flash(str(error), "error")
    return redirect(url_for("scan.scan_out") + "?scanned=fail")


@bp.route("/out/remove/<int:line_id>", methods=["POST"])
@login_required
@admin_required
def remove_out(line_id: int):
    from database import Database
    db = Database()
    try:
        cart = db.get_active_cart(int(current_user.id), "OUT")
        if cart and cart["mode"] == "IMMEDIATE":
            db.undo_immediate_scan(int(current_user.id), line_id,
                                   request.form.get("reason") or "", current_user.username)
            flash("Scan corrected; stock and visitor pounds were updated.", "success")
        else:
            db.remove_cart_line(int(current_user.id), line_id, "OUT")
    except ValueError as error:
        flash(str(error), "error")
    return redirect(url_for("scan.scan_out"))


@bp.route("/out/undo/<int:movement_id>", methods=["POST"])
@login_required
@admin_required
def undo_out(movement_id: int):
    from database import Database
    db = Database()
    try:
        cart_id = db.undo_immediate_scan(int(current_user.id), movement_id,
                                         request.form.get("reason") or "", current_user.username)
        flash("Scan corrected; stock and visitor pounds were updated.", "success")
    except ValueError as error:
        flash(str(error), "error")
        return redirect(url_for("scan.scan_out"))
    receipt = db.get_cart_receipt(int(current_user.id), cart_id)
    return redirect(url_for("scan.distribution_receipt", cart_id=cart_id)
                    if receipt else url_for("scan.scan_out"))


@bp.route("/out/complete", methods=["POST"])
@login_required
@admin_required
def complete_out():
    from database import Database
    db = Database()
    session_weight = _parse_session_weight(request.form.get("session_weight_lb"))
    cart_id = request.form.get("cart_id") or ""
    try:
        cart = db.get_active_cart(int(current_user.id), "OUT")
        if cart and not cart.get("client_id"):
            # Simple scan-out (no client visit) — just close the cart
            db.complete_simple_scan_out(int(current_user.id), cart_id,
                                        current_user.username, session_weight)
            flash("Scan-out session completed.", "success")
            return redirect(url_for("scan.scan_out"))
        receipt = db.complete_scan_out_cart(
            int(current_user.id), cart_id, current_user.username, session_weight,
        )
    except ValueError as error:
        flash(str(error), "error")
        return redirect(url_for("scan.scan_out"))
    return redirect(url_for("scan.distribution_receipt", cart_id=receipt["id"]))


@bp.route("/out/cancel", methods=["POST"])
@login_required
@admin_required
def cancel_out():
    from database import Database
    try:
        Database().cancel_scan_cart(int(current_user.id), request.form.get("cart_id") or "", "OUT")
        flash("Distribution cart cancelled; no visit or stock changes were recorded.", "info")
    except ValueError as error:
        flash(str(error), "error")
    return redirect(url_for("scan.scan_out"))


@bp.route("/out/receipt/<cart_id>")
@login_required
@admin_required
def distribution_receipt(cart_id: str):
    from database import Database
    receipt = Database().get_cart_receipt(int(current_user.id), cart_id)
    if not receipt or receipt["direction"] != "OUT":
        abort(404)
    stats = (Database().get_client_weight_summary(receipt["client_id"])
             if receipt.get("client_id") else None)
    return render_template("scan/out_receipt.html", receipt=receipt, stats=stats)


def _parse_session_weight(raw: str | None) -> int | None:
    raw = (raw or "").strip()
    if not raw:
        return None
    try:
        value = Decimal(raw)
    except InvalidOperation:
        return None
    if not value.is_finite() or value <= 0 or value > 10000:
        return None
    scaled = value * 1000
    if scaled != scaled.to_integral_value():
        return None
    return int(scaled)
