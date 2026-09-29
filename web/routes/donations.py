"""Standalone donation weight recording and management."""

import datetime
from decimal import Decimal, InvalidOperation

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from decorators import admin_required

bp = Blueprint("donations", __name__, url_prefix="/donations")


@bp.route("/")
@login_required
@admin_required
def index():
    from database import Database
    records = Database().get_donation_records()
    return render_template("donations/index.html", records=records)


@bp.route("/new", methods=["GET", "POST"])
@login_required
@admin_required
def new():
    if request.method == "GET":
        return render_template("donations/form.html", mode="new", record={
            "donation_date": datetime.date.today().isoformat(),
            "source": "", "notes": "", "weight_lb": "",
        })
    weight = _parse_weight(request.form.get("weight_lb"))
    if weight is None:
        flash("Enter a valid weight in pounds (e.g. 42.5).", "error")
        return render_template("donations/form.html", mode="new", record=request.form), 400
    from database import Database
    try:
        Database().record_donation_weight(
            weight, request.form.get("donation_date", ""),
            request.form.get("source", ""), request.form.get("notes", ""),
            current_user.username,
        )
    except ValueError as error:
        flash(str(error), "error")
        return render_template("donations/form.html", mode="new", record=request.form), 400
    flash("Donation weight recorded.", "success")
    return redirect(url_for("donations.index"))


@bp.route("/<int:record_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def edit(record_id: int):
    from database import Database
    db = Database()
    record = db.get_donation_record(record_id)
    if not record:
        abort(404)
    if request.method == "GET":
        record["weight_lb"] = f"{record['weight_milli_lb'] / 1000:.3f}"
        return render_template("donations/form.html", mode="edit", record=record)
    weight = _parse_weight(request.form.get("weight_lb"))
    if weight is None:
        flash("Enter a valid weight in pounds.", "error")
        return render_template("donations/form.html", mode="edit", record=record), 400
    try:
        db.update_donation_record(
            record_id, weight, request.form.get("donation_date", ""),
            request.form.get("source", ""), request.form.get("notes", ""),
            current_user.username,
        )
    except ValueError as error:
        flash(str(error), "error")
        return render_template("donations/form.html", mode="edit", record=record), 400
    flash("Donation record updated.", "success")
    return redirect(url_for("donations.index"))


@bp.route("/<int:record_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete(record_id: int):
    from database import Database
    try:
        Database().delete_donation_record(record_id, current_user.username)
        flash("Donation record deleted.", "info")
    except ValueError as error:
        flash(str(error), "error")
    return redirect(url_for("donations.index"))


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
