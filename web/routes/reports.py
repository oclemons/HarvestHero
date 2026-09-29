"""Administrator-only weight ledger and month reconciliation."""

import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from decorators import admin_required
from routes.inventory import _parse_unit_weight

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
                               pending=db.get_pending_weight_movements()), 400
    return render_template("reports/weights.html", summary=summary, month=month,
                           pending=db.get_pending_weight_movements())


@bp.route("/weights/<int:movement_id>/resolve", methods=["POST"])
@login_required
@admin_required
def resolve_weight(movement_id: int):
    from database import Database
    measured, error = _parse_unit_weight((request.form.get("measured_lb") or "").strip())
    if error or measured is None:
        flash(error or "Enter a measured weight in pounds.", "error")
    else:
        try:
            Database().resolve_movement_weight(movement_id, measured,
                                               request.form.get("reason") or "",
                                               current_user.username)
            flash("Weight reconciled. Monthly and visitor totals have been updated.", "success")
        except ValueError as exc:
            flash(str(exc), "error")
    return redirect(url_for("reports.weights", month=request.form.get("month") or ""))
