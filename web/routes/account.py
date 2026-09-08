"""Account routes — per-user settings, starting with change password.

Everything here requires an authenticated session. Password writes go
through the same ``auth.hash_password`` / ``database.update_user_password``
that the desktop app uses, so a rotation done in the browser is
immediately effective for both frontends.
"""

from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from auth import (
    MIN_PASSWORD_LENGTH,
    hash_password,
    validate_password_strength,
    verify_password,
)
from database import Database


bp = Blueprint("account", __name__, url_prefix="/account")

_db = Database()


@bp.route("/settings", methods=["GET"])
@login_required
def settings():
    return render_template(
        "account/settings.html",
        user=current_user,
        min_length=MIN_PASSWORD_LENGTH,
    )


@bp.route("/password", methods=["POST"])
@login_required
def change_password():
    current    = request.form.get("current_password") or ""
    new_pw     = request.form.get("new_password")     or ""
    confirm_pw = request.form.get("confirm_password") or ""

    # Reload the user row so we're verifying against the *current* stored
    # hash, not whatever was cached at login.
    row = _db.get_user(current_user.username)
    if not row:
        flash("Account not found.", "error")
        return redirect(url_for("account.settings"))

    # 1. Prove the caller knows the current password. This is our CSRF
    #    mitigation as much as an identity check: even a forged POST
    #    with the session cookie can't rotate the password without also
    #    knowing the current one.
    if not verify_password(current, row["password_hash"], row["salt"]):
        flash("Current password is incorrect.", "error")
        return redirect(url_for("account.settings"))

    # 2. Both new-password fields must match.
    if new_pw != confirm_pw:
        flash("New password and confirmation do not match.", "error")
        return redirect(url_for("account.settings"))

    # 3. Reject trivially weak passwords.
    ok, msg = validate_password_strength(new_pw)
    if not ok:
        flash(msg, "error")
        return redirect(url_for("account.settings"))

    # 4. Reject reusing the current password.
    if verify_password(new_pw, row["password_hash"], row["salt"]):
        flash("New password must be different from the current password.",
              "error")
        return redirect(url_for("account.settings"))

    # 5. Store it. update_user_password returns None; any failure comes
    #    through as an exception (e.g. sqlite locked / bad column).
    new_hash, new_salt = hash_password(new_pw)
    try:
        _db.update_user_password(row["id"], new_hash, new_salt)
    except Exception as exc:  # pragma: no cover — logged for support
        print(f"[account] password update failed for user "
              f"{row['id']}: {exc}")
        flash("Could not save the new password. Try again.", "error")
        return redirect(url_for("account.settings"))

    flash("Password changed. Use it the next time you sign in.", "success")
    return redirect(url_for("account.settings"))
