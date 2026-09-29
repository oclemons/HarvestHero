"""Minimal administrator-managed account provisioning."""

import re

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from auth import hash_password, validate_password_strength, verify_password
from decorators import admin_required
from extensions import limiter

bp = Blueprint("users", __name__, url_prefix="/admin/users")


@bp.route("/", methods=["GET", "POST"])
@login_required
@admin_required
def index():
    from database import Database
    db = Database()
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        full_name = (request.form.get("full_name") or "").strip()
        role = (request.form.get("role") or "").strip()
        password = request.form.get("password") or ""
        confirm_password = request.form.get("confirm_password") or ""
        if not re.fullmatch(r"[A-Za-z0-9_.-]{3,64}", username):
            flash("Username must be 3–64 letters, numbers, dots, dashes or underscores.", "error")
        elif len(full_name) > 120:
            flash("Name must be 120 characters or fewer.", "error")
        elif role not in ("admin", "student"):
            flash("Select an available role.", "error")
        elif password != confirm_password:
            flash("Temporary passwords do not match.", "error")
        else:
            valid, message = validate_password_strength(password)
            if valid:
                hashed, salt = hash_password(password)
                created, message = db.create_user_full(
                    username, hashed, salt, role, full_name, current_user.username
                )
                if created:
                    db.log_activity(current_user.username, "CREATE_USER", username)
                    flash("Account created. Share the temporary password privately and ask the user to change it under Settings.", "success")
                    return redirect(url_for("users.index"))
            flash(message, "error")
        return render_template("admin/users.html", users=db.get_all_users()), 400
    return render_template("admin/users.html", users=db.get_all_users())


@bp.route("/<int:user_id>/reset", methods=["GET", "POST"])
@login_required
@admin_required
@limiter.limit("10 per 15 minutes", methods=["POST"])
def reset_password(user_id: int):
    from database import Database
    db = Database()
    target = db.get_user_by_id(user_id)
    if not target:
        abort(404)
    if target["role"] != "student":
        abort(403)
    if request.method == "GET":
        return render_template("admin/reset_password.html", target=target)
    admin_password = request.form.get("admin_password") or ""
    password = request.form.get("password") or ""
    confirm_password = request.form.get("confirm_password") or ""
    actor = db.get_user(current_user.username)
    if not actor or not verify_password(admin_password, actor["password_hash"], actor["salt"]):
        flash("Your administrator password is incorrect.", "error")
    elif password != confirm_password:
        flash("Temporary passwords do not match.", "error")
    else:
        valid, message = validate_password_strength(password)
        if not valid:
            flash(message, "error")
        elif verify_password(password, target["password_hash"], target["salt"]):
            flash("Use a new password, not the account's current one.", "error")
        else:
            hashed, salt = hash_password(password)
            db.reset_student_password(int(current_user.id), user_id, hashed, salt)
            flash("Student password reset. Share the temporary password privately and ask them to change it under Settings after signing in.", "success")
            return redirect(url_for("users.index"))
    return render_template("admin/reset_password.html", target=target), 400


@bp.route("/<int:user_id>/status", methods=["POST"])
@login_required
@admin_required
def status(user_id: int):
    from database import Database
    desired = request.form.get("active")
    if desired not in ("0", "1"):
        abort(400)
    try:
        Database().manage_user_active(int(current_user.id), user_id, desired == "1")
        flash("Team account access updated.", "success")
    except ValueError as error:
        flash(str(error), "error")
    return redirect(url_for("users.index"))
