"""Administrator-only pantry-client intake and semester verification."""

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from decorators import admin_required

bp = Blueprint("clients", __name__, url_prefix="/clients")


@bp.before_request
def _require_policy():
    if (current_user.is_authenticated and current_user.is_admin and
            not current_app.config.get("CLIENT_RECORDS_ENABLED", False)):
        abort(503)


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
