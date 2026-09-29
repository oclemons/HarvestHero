"""Server-owned intake carts and Admin-only visitor distribution sessions."""

from uuid import uuid4

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required

from decorators import admin_required, student_or_admin_required
from routes.inventory import _parse_unit_weight

bp = Blueprint("scan", __name__, url_prefix="/scan")


@bp.before_request
def _require_policy_for_distribution():
    if (request.path.startswith("/scan/out") and current_user.is_authenticated and
            current_user.is_admin and not current_app.config.get("CLIENT_RECORDS_ENABLED", False)):
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
        shelf_id = int(request.form.get("shelf_id") or "")
        Database().add_scan_to_cart(int(current_user.id), request.form.get("barcode") or "",
                                    shelf_id)
        session["last_intake_shelf"] = shelf_id
    except ValueError as error:
        flash(str(error) if request.form.get("shelf_id") else "Choose a destination shelf.", "error")
    return redirect(url_for("scan.scan_in"))


@bp.route("/in/remove/<int:line_id>", methods=["POST"])
@login_required
@student_or_admin_required
def remove_in(line_id: int):
    from database import Database
    try:
        Database().remove_cart_line(int(current_user.id), line_id)
    except ValueError as error:
        flash(str(error), "error")
    return redirect(url_for("scan.scan_in"))


@bp.route("/in/weight/<int:line_id>", methods=["POST"])
@login_required
@admin_required
def weigh_in(line_id: int):
    from database import Database
    measured, error = _parse_unit_weight((request.form.get("measured_lb") or "").strip())
    if error or measured is None:
        flash(error or "Enter measured pounds.", "error")
    else:
        try:
            Database().set_cart_line_weight(int(current_user.id), line_id, measured,
                                            request.form.get("reason") or "", current_user.username)
        except ValueError as exc:
            flash(str(exc), "error")
    return redirect(url_for("scan.scan_in"))


@bp.route("/in/complete", methods=["POST"])
@login_required
@student_or_admin_required
def complete_in():
    from database import Database
    db = Database()
    cart_id = request.form.get("cart_id") or ""
    try:
        receipt = db.complete_scan_in_cart(int(current_user.id), cart_id, current_user.username)
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
        Database().cancel_scan_cart(int(current_user.id), request.form.get("cart_id") or "")
        flash("Cart cancelled; inventory was not changed.", "info")
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
    cart = db.get_active_cart(int(current_user.id), "OUT")
    client = db.get_pantry_client(cart["client_id"]) if cart else None
    people = db.list_private_clients() if not cart else []
    if not cart:
        for person in people:
            person["eligible"] = db.is_client_eligible(person["id"])
    return render_template("scan/out.html", cart=cart, client=client, clients=people,
                           scan_token=uuid4().hex,
                           stats=db.get_client_weight_summary(cart["client_id"]) if cart else None,
                           sections=db.get_pantry_layout())


@bp.route("/out/start", methods=["POST"])
@login_required
@admin_required
def start_out():
    from database import Database
    try:
        client_id = int(request.form.get("client_id") or "")
        Database().start_scan_out_cart(int(current_user.id), client_id,
                                       request.form.get("mode") or "REVIEW")
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
        shelf_id = int(request.form.get("shelf_id") or "")
        cart = db.get_active_cart(int(current_user.id), "OUT")
        if cart and cart["mode"] == "IMMEDIATE":
            measured_raw = (request.form.get("measured_lb") or "").strip()
            measured, error = _parse_unit_weight(measured_raw)
            if error:
                raise ValueError(error)
            db.record_immediate_scan_out(
                int(current_user.id), request.form.get("barcode") or "", shelf_id,
                current_user.username, request.form.get("scan_token") or "",
                measured, request.form.get("reason") or "",
            )
            flash("Item scanned out and recorded in this customer's visit.", "success")
        else:
            db.add_scan_out_to_cart(
                int(current_user.id), request.form.get("barcode") or "", shelf_id
            )
    except ValueError as error:
        flash(str(error) if request.form.get("shelf_id") else "Choose a source shelf.", "error")
    return redirect(url_for("scan.scan_out"))


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


@bp.route("/out/weight/<int:line_id>", methods=["POST"])
@login_required
@admin_required
def weigh_out(line_id: int):
    from database import Database
    cart = Database().get_active_cart(int(current_user.id), "OUT")
    if cart and cart["mode"] == "IMMEDIATE":
        flash("Enter measured weight before scanning, or reconcile it in Pounds afterward.", "error")
        return redirect(url_for("scan.scan_out"))
    measured, error = _parse_unit_weight((request.form.get("measured_lb") or "").strip())
    if error or measured is None:
        flash(error or "Enter measured pounds.", "error")
    else:
        try:
            Database().set_cart_line_weight(int(current_user.id), line_id, measured,
                                            request.form.get("reason") or "",
                                            current_user.username, "OUT")
        except ValueError as exc:
            flash(str(exc), "error")
    return redirect(url_for("scan.scan_out"))


@bp.route("/out/complete", methods=["POST"])
@login_required
@admin_required
def complete_out():
    from database import Database
    try:
        receipt = Database().complete_scan_out_cart(
            int(current_user.id), request.form.get("cart_id") or "", current_user.username
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
    return render_template("scan/out_receipt.html", receipt=receipt,
                           stats=Database().get_client_weight_summary(receipt["client_id"]))
