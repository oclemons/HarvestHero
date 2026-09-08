"""Sign-in / sign-out routes.

Reuses the desktop app's password verification (``auth.verify_password``)
and user store (``database.Database``) so the two front-ends agree on
who exists and what password works.
"""

from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import UserMixin, login_required, login_user, logout_user

from auth import verify_password
from database import Database

from extensions import login_manager


bp = Blueprint("auth", __name__)

_db = Database()


class User(UserMixin):
    """Flask-Login user shim over the desktop app's user rows."""

    def __init__(self, row: dict):
        self.id       = str(row["id"])
        self.username = row["username"]
        self.role     = row["role"]
        self.is_admin = row.get("role") == "admin"
        self._row     = row


@login_manager.user_loader
def _load_user(user_id: str):
    try:
        uid = int(user_id)
    except (TypeError, ValueError):
        return None
    for u in _db.get_all_users():
        if u["id"] == uid and u.get("is_active"):
            return User(u)
    return None


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        row = _db.get_user(username)
        if row and row.get("is_active") and verify_password(
                password, row["password_hash"], row["salt"]):
            login_user(User(row), remember=False)
            _db.update_last_login(username)
            return redirect(request.args.get("next") or url_for("dashboard.home"))
        flash("Invalid username or password.", "error")
    return render_template("auth/login.html")


@bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Signed out.", "info")
    return redirect(url_for("auth.login"))
