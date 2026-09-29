"""Administrator-only pantry-client intake and semester verification."""

import csv
import io
import json

from flask import Blueprint, Response, abort, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from auth import verify_password
from decorators import admin_required
from extensions import limiter

bp = Blueprint("clients", __name__, url_prefix="/clients")


@bp.before_request
def _require_policy():
    if (current_user.is_authenticated and current_user.is_admin and
            not current_app.config.get("CLIENT_RECORDS_ENABLED", False)):
        abort(503)


def _safe_cell(value):
    text = "" if value is None else str(value)
    leading = text.lstrip(" \t\r\n")
    if text.startswith(("\t", "\r", "\n")) or (leading and leading[0] in "=+-@"):
        return "'" + text
    return text


def _csv_download(headers, rows, filename):
    output = io.StringIO(newline="")
    writer = csv.writer(output, quoting=csv.QUOTE_ALL)
    writer.writerow(headers)
    writer.writerows([_safe_cell(value) for value in row] for row in rows)
    return Response(output.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": f"attachment; filename={filename}",
                             "Cache-Control": "private, no-store"})


def _authorize_export(db):
    actor = db.get_user(current_user.username)
    if not actor or not verify_password(request.form.get("admin_password") or "",
                                        actor["password_hash"], actor["salt"]):
        abort(403)


@bp.route("/exports")
@login_required
@admin_required
def exports():
    return render_template("clients/exports.html")


@bp.route("/exports/customers.csv", methods=["POST"])
@login_required
@admin_required
@limiter.limit("10 per 15 minutes", methods=["POST"])
def export_customers():
    from database import Database
    db = Database()
    _authorize_export(db)
    fields = ("student_id", "first_name", "last_name", "birth_date",
              "expected_graduation_semester", "enrollment_status", "is_active",
              "verified_term", "verified_until", "verification_status", "created_at")
    records = db.get_client_export_rows()
    db.log_activity(current_user.username, "CLIENT_EXPORT", f"type=customers rows={len(records)}")
    return _csv_download(fields, ([record[field] for field in fields] for record in records),
                         "pantry-customers.csv")


@bp.route("/exports/visits.csv", methods=["POST"])
@login_required
@admin_required
@limiter.limit("10 per 15 minutes", methods=["POST"])
def export_visits():
    from database import Database
    db = Database()
    _authorize_export(db)
    fields = ("visit_id", "student_id", "first_name", "last_name", "visit_date",
              "known_pounds", "pending_weight_lines", "weight_complete", "visit_status",
              "lifetime_known_pounds", "lifetime_pending_visits", "recorded_by", "items")
    records = db.get_visit_export_rows()
    totals = {record["client_id"]: db.get_client_weight_summary(record["client_id"])
              for record in records}
    rows = []
    for record in records:
        try:
            items = json.loads(record["items_json"] or "[]")
            item_summary = "; ".join(
                f"{item.get('item_name', 'Item')} x{item.get('quantity', 0)}"
                f"{' (undone)' if item.get('undone') else ''}"
                for item in items if isinstance(item, dict)
            )
        except (ValueError, TypeError):
            item_summary = "Item detail unavailable"
        known = record["known_weight_milli_lb"]
        if known is None and record["pounds_received"] is not None:
            known = round(record["pounds_received"] * 1000)
        summary = totals[record["client_id"]]
        rows.append((record["visit_id"], record["student_id"], record["first_name"],
                     record["last_name"], record["visit_date"],
                     f"{known / 1000:.3f}" if known is not None else "",
                     record["pending_weight_lines"], record["weight_complete"],
                     "void" if record["is_void"] else "recorded",
                     f"{summary['known_weight_milli_lb'] / 1000:.3f}",
                     summary["pending_visits"], record["recorded_by"], item_summary))
    db.log_activity(current_user.username, "CLIENT_EXPORT", f"type=visits rows={len(rows)}")
    return _csv_download(fields, rows, "pantry-visits.csv")


@bp.route("/exports/monthly.csv", methods=["POST"])
@login_required
@admin_required
@limiter.limit("10 per 15 minutes", methods=["POST"])
def export_monthly():
    from database import Database
    db = Database()
    _authorize_export(db)
    fields = ("month_utc", "opening_pounds", "initial_stock_pounds", "donated_pounds",
              "distributed_pounds", "adjustment_pounds", "closing_pounds", "pending_lines")
    rows = []
    for month in db.get_report_months():
        report = db.get_monthly_weight_report(month)
        rows.append((month, *(f"{report[key] / 1000:.3f}" for key in (
            "opening_milli_lb", "opening_baseline_milli_lb", "donated_milli_lb",
            "distributed_milli_lb", "adjustment_milli_lb", "closing_milli_lb")),
            report["pending_lines"]))
    db.log_activity(current_user.username, "CLIENT_EXPORT", f"type=monthly rows={len(rows)}")
    return _csv_download(fields, rows, "pantry-monthly-pounds.csv")


@bp.route("/")
@login_required
@admin_required
def index():
    from database import Database
    Database().log_activity(current_user.username, "CLIENT_LIST", "")
    return render_template("clients/list.html", clients=Database().list_private_clients())


@bp.route("/new", methods=["GET", "POST"])
@login_required
@admin_required
def new():
    if request.method == "GET":
        return render_template("clients/form.html", values={})
    from database import Database
    values = request.form
    try:
        client_id = Database().register_pantry_client(
            values.get("student_id") or "", values.get("first_name") or "",
            values.get("last_name") or "", values.get("birth_date") or "",
            values.get("graduation_semester") or "", values.get("enrollment_status") or "",
            current_user.username,
        )
    except ValueError as error:
        flash(str(error), "error")
        return render_template("clients/form.html", values=values), 400
    flash("Client registered. Verify current-semester enrollment before checkout.", "success")
    return redirect(url_for("clients.detail", client_id=client_id))


@bp.route("/<int:client_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def edit(client_id: int):
    from database import Database
    db = Database()
    client = db.get_pantry_client(client_id)
    if not client:
        abort(404)
    if request.method == "GET":
        db.log_activity(current_user.username, "CLIENT_VIEW", f"client={client_id}")
        return render_template("clients/form.html", values=dict(client, graduation_semester=client["expected_graduation_semester"]),
                               client_id=client_id)
    values = request.form
    try:
        db.update_registered_client(
            client_id, values.get("student_id") or "", values.get("first_name") or "",
            values.get("last_name") or "", values.get("birth_date") or "",
            values.get("graduation_semester") or "", values.get("enrollment_status") or "",
            current_user.username,
        )
    except ValueError as error:
        flash(str(error), "error")
        return render_template("clients/form.html", values=values, client_id=client_id), 400
    flash("Client record updated. Reverify enrollment if identity details changed.", "success")
    return redirect(url_for("clients.detail", client_id=client_id))


@bp.route("/<int:client_id>")
@login_required
@admin_required
def detail(client_id: int):
    from database import Database
    db = Database()
    client = db.get_pantry_client(client_id)
    if not client:
        abort(404)
    db.log_activity(current_user.username, "CLIENT_VIEW", f"client={client_id}")
    return render_template("clients/detail.html", client=client,
                           eligibility=db.get_client_eligibility(client_id),
                           eligible=db.is_client_eligible(client_id),
                           visits=db.get_client_visits(client_id),
                           stats=db.get_client_weight_summary(client_id))


@bp.route("/<int:client_id>/status", methods=["POST"])
@login_required
@admin_required
def status(client_id: int):
    from database import Database
    desired = request.form.get("active")
    if desired not in ("0", "1"):
        abort(400)
    try:
        Database().set_client_record_active(client_id, desired == "1", current_user.username)
        flash("Client status updated. Verify the semester again before checkout if reactivated.", "success")
    except ValueError as error:
        flash(str(error), "error")
    return redirect(url_for("clients.detail", client_id=client_id))


@bp.route("/<int:client_id>/revoke", methods=["POST"])
@login_required
@admin_required
def revoke(client_id: int):
    from database import Database
    try:
        Database().revoke_client_term(client_id, current_user.username)
        flash("Semester verification revoked; checkout is blocked.", "success")
    except ValueError as error:
        flash(str(error), "error")
    return redirect(url_for("clients.detail", client_id=client_id))


@bp.route("/<int:client_id>/verify", methods=["POST"])
@login_required
@admin_required
def verify(client_id: int):
    from database import Database
    if request.form.get("confirmed_enrollment") != "on":
        flash("Confirm you checked current enrollment with the school before verifying.", "error")
        return redirect(url_for("clients.detail", client_id=client_id))
    try:
        Database().verify_client_term(
            client_id, request.form.get("term") or "",
            request.form.get("verified_until") or "", current_user.username,
        )
    except ValueError as error:
        flash(str(error), "error")
        return redirect(url_for("clients.detail", client_id=client_id))
    flash("Semester eligibility recorded. Reverify when it expires.", "success")
    return redirect(url_for("clients.detail", client_id=client_id))
