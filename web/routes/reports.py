"""Administrator-only weight ledger, activity log, and month summaries."""

import datetime
from decimal import Decimal, InvalidOperation

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from decorators import admin_required

bp = Blueprint("reports", __name__, url_prefix="/reports")


@bp.route("/weights")
@login_required
@admin_required
def weights():
    from database import Database
    month = request.args.get("month") or datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m")
    db = Database()
    try:
        summary = db.get_monthly_weight_report(month)
    except ValueError as error:
        flash(str(error), "error")
        return render_template("reports/weights.html", summary=None, month=month,
                               service=None), 400
    service = db.get_monthly_service_summary(month) if current_app.config.get("CLIENT_RECORDS_ENABLED") else None
    return render_template("reports/weights.html", summary=summary, month=month,
                           service=service)


@bp.route("/activity")
@login_required
@admin_required
def activity():
    from database import Database
    db = Database()
    action_filter = request.args.get("action", "").strip()
    user_filter = request.args.get("user", "").strip()
    entries = db.get_activity_log(500)
    if action_filter:
        entries = [e for e in entries if e["action"] == action_filter]
    if user_filter:
        entries = [e for e in entries if e["username"] == user_filter]
    actions = sorted({e["action"] for e in db.get_activity_log(500)})
    users = sorted({e["username"] for e in db.get_activity_log(500)})
    return render_template("reports/activity.html", entries=entries, actions=actions,
                           users=users, action_filter=action_filter, user_filter=user_filter)


@bp.route("/sessions")
@login_required
@admin_required
def sessions():
    from database import Database
    db = Database()
    conn = db._connect()
    carts = conn.execute(
        "SELECT c.id, c.direction, c.status, c.completed_at, c.session_weight_milli_lb, "
        "c.owner_id, u.username AS owner_name "
        "FROM pantry_carts c JOIN users u ON u.id = c.owner_id "
        "WHERE c.status = 'COMPLETED' ORDER BY c.completed_at DESC LIMIT 100",
    ).fetchall()
    conn.close()
    return render_template("reports/sessions.html", carts=[dict(c) for c in carts])


@bp.route("/sessions/<cart_id>/weight", methods=["POST"])
@login_required
@admin_required
def correct_weight(cart_id: str):
    from database import Database
    raw = (request.form.get("weight_lb") or "").strip()
    reason = (request.form.get("reason") or "").strip()
    weight = _parse_weight(raw)
    if weight is None:
        flash("Enter a valid weight in pounds.", "error")
    elif not reason:
        flash("Enter a reason for this correction.", "error")
    else:
        try:
            Database().update_session_weight(cart_id, weight, reason, current_user.username)
            flash("Session weight corrected.", "success")
        except ValueError as error:
            flash(str(error), "error")
    return redirect(url_for("reports.sessions"))


def _parse_weight(raw: str | None) -> int | None:
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
