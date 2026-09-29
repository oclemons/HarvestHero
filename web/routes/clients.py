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

CUSTOMER_FIELDS = (
    ("student_id", "Student ID", True),
    ("first_name", "First name", True),
    ("last_name", "Last name", True),
    ("birth_date", "Birth date", True),
    ("expected_graduation_semester", "Expected graduation", False),
    ("enrollment_status", "Full/part-time status", False),
    ("household_size", "Household size", False),
    ("allergies", "Allergies", True),
    ("religious_restrictions", "Religious food restrictions", True),
    ("is_active", "Active account", False),
    ("verified_term", "Verified term", False),
    ("verified_until", "Verification expiry", False),
    ("verification_status", "Verification status", False),
    ("created_at", "Account created", False),
)
VISIT_FIELDS = (
    ("visit_id", "Visit reference", False),
    ("student_id", "Student ID", True),
    ("first_name", "First name", True),
    ("last_name", "Last name", True),
    ("visit_date", "Visit date", False),
    ("verified_term", "Verified semester", False),
    ("fulfillment_type", "Locker or in-person", False),
    ("known_pounds", "Known pounds received", False),
    ("pending_weight_lines", "Pending weight lines", False),
    ("weight_complete", "Weight complete", False),
    ("visit_status", "Visit status", False),
    ("lifetime_known_pounds", "Lifetime known pounds", False),
    ("lifetime_pending_visits", "Lifetime pending visits", False),
    ("recorded_by", "Admin who recorded visit", True),
    ("items", "Food item details", True),
)
MONTH_FIELDS = (
    ("month_utc", "Month (UTC)", False),
    ("opening_pounds", "Opening pounds", False),
    ("donated_pounds", "Donated pounds", False),
    ("distributed_pounds", "Distributed pounds", False),
    ("pending_lines", "Pending-weight sessions", False),
    ("service_visits", "Pantry visits", False),
    ("service_known_pounds", "Known pounds received by clients", False),
    ("service_pending_visits", "Visits with pending weight", False),
    ("inventory_history_available", "Inventory history available", False),
)


@bp.after_request
def _private_response(response):
    response.headers["Cache-Control"] = "private, no-store"
    return response


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


def _selected_fields(options):
    requested = request.form.getlist("fields")
    available = {name: sensitive for name, _, sensitive in options}
    if (not requested or len(requested) != len(set(requested)) or
            any(name not in available for name in requested)):
        abort(400, "Choose only the report columns shown on the form.")
    if (any(available[name] for name in requested) and
            request.form.get("acknowledge_sensitive") != "on"):
        abort(400, "Confirm sensitive-data handling before exporting those columns.")
    return tuple(name for name, _, _ in options if name in requested)


@bp.route("/exports")
@login_required
@admin_required
def exports():
    return render_template("clients/exports.html", customer_fields=CUSTOMER_FIELDS,
                           visit_fields=VISIT_FIELDS, month_fields=MONTH_FIELDS)


@bp.route("/exports/customers.csv", methods=["POST"])
@login_required
@admin_required
@limiter.limit("10 per 15 minutes", methods=["POST"])
def export_customers():
    from database import Database
    db = Database()
    _authorize_export(db)
    fields = _selected_fields(CUSTOMER_FIELDS)
    records = db.get_client_export_rows()
    db.log_activity(current_user.username, "CLIENT_EXPORT",
                    f"type=customers rows={len(records)} columns={','.join(fields)}")
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
    fields = _selected_fields(VISIT_FIELDS)
    term = (request.form.get("term") or "").strip()
    fulfillment = request.form.get("fulfillment_type") or ""
    if len(term) > 40 or fulfillment not in ("", "in_person", "locker"):
        abort(400, "Choose a valid visit term and fulfillment type.")
    records = [record for record in db.get_visit_export_rows()
               if (not term or record["verified_term"] == term)
               and (not fulfillment or record["fulfillment_type"] == fulfillment)]
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
        values = dict(record)
        values.update(
            known_pounds=f"{known / 1000:.3f}" if known is not None else "",
            visit_status="void" if record["is_void"] else "recorded",
            lifetime_known_pounds=f"{summary['known_weight_milli_lb'] / 1000:.3f}",
            lifetime_pending_visits=summary["pending_visits"], items=item_summary,
        )
        rows.append(tuple(values[field] for field in fields))
    db.log_activity(current_user.username, "CLIENT_EXPORT",
                    f"type=visits rows={len(rows)} columns={','.join(fields)}")
    return _csv_download(fields, rows, "pantry-visits.csv")


@bp.route("/exports/monthly.csv", methods=["POST"])
@login_required
@admin_required
@limiter.limit("10 per 15 minutes", methods=["POST"])
def export_monthly():
    from database import Database
    db = Database()
    _authorize_export(db)
    fields = _selected_fields(MONTH_FIELDS)
    requested_month = (request.form.get("month") or "").strip()
    if requested_month:
        try:
            db.get_monthly_weight_report(requested_month)
        except ValueError:
            abort(400, "Enter a valid reporting month.")
    rows = []
    for month in ([requested_month] if requested_month else db.get_report_months()):
        report = db.get_monthly_weight_report(month)
        service = db.get_monthly_service_summary(month)
        if not report["history_available"] and not service["visits"]:
            continue
        values = {"month_utc": month, "pending_lines": report.get("pending_sessions", 0),
                  "service_visits": service["visits"],
                  "service_known_pounds": f"{service['known_weight_milli_lb'] / 1000:.3f}",
                  "service_pending_visits": service["pending_visits"],
                  "inventory_history_available": int(report["history_available"]),
                  "donated_pounds": f"{report['donated_milli_lb'] / 1000:.3f}",
                  "distributed_pounds": f"{report['distributed_milli_lb'] / 1000:.3f}",
                  "opening_pounds": "0.000", "initial_stock_pounds": "0.000",
                  "adjustment_pounds": "0.000", "closing_pounds": "0.000"}
        rows.append(tuple(values[field] for field in fields))
    db.log_activity(current_user.username, "CLIENT_EXPORT",
                    f"type=monthly rows={len(rows)} columns={','.join(fields)}")
    return _csv_download(fields, rows, "pantry-monthly-pounds.csv")


@bp.route("/retention")
@login_required
@admin_required
def retention():
    from database import Database
    db = Database()
    db.log_activity(current_user.username, "CLIENT_RETENTION_REVIEW", "")
    return render_template("clients/retention.html",
                           candidates=db.get_retention_candidates(days_ahead=30))


@bp.route("/<int:client_id>/retention/remove", methods=["POST"])
@login_required
@admin_required
@limiter.limit("5 per 15 minutes", methods=["POST"])
def remove_due_client(client_id: int):
    from database import Database
    db = Database()
    _authorize_export(db)
    if request.form.get("confirmed_removal") != "on":
        abort(400)
    try:
        db.remove_client_identity(client_id, request.form.get("student_id") or "",
                                  current_user.username)
    except ValueError as error:
        flash(str(error), "error")
        return render_template("clients/retention.html",
                               candidates=db.get_retention_candidates(days_ahead=30)), 400
    flash("Due client record removed. Only organization-level monthly totals remain.", "success")
    return redirect(url_for("clients.retention"))


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
            current_user.username, household_size=int(values.get("household_size") or 1),
            allergies=values.get("allergies") or "",
            religious_restrictions=values.get("religious_restrictions") or "",
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
            household_size=int(values.get("household_size") or client["household_size"] or 1),
            allergies=values.get("allergies", client["allergies"] or ""),
            religious_restrictions=values.get(
                "religious_restrictions", client["religious_restrictions"] or ""
            ),
        )
    except ValueError as error:
        flash(str(error), "error")
        return render_template("clients/form.html", values=values, client_id=client_id), 400
    flash("Client record updated. Reverify enrollment if ID, birth date or full/part-time status changed.", "success")
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
                           allowance=db.get_client_visit_allowance(client_id),
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
