"""Placeholder dashboard — real content lands in Phase 1.

Kept intentionally thin so the whole web-app scaffold can be deployed
and demoed before any real feature is built. Deleting this file will
break the auth flow's post-login redirect; expand it into a real
dashboard rather than removing it.
"""

from __future__ import annotations

from flask import Blueprint, render_template
from flask_login import current_user, login_required

from database import Database


bp = Blueprint("dashboard", __name__)

_db = Database()


@bp.route("/app")
@login_required
def home():
    # Cheap counts so the dashboard has a pulse from day one.
    items    = _db.get_all_items()
    low      = _db.get_low_stock_items()
    users    = _db.get_all_users()
    stats = {
        "total_items":  len(items),
        "low_stock":    len(low),
        "active_users": sum(1 for u in users if u.get("is_active")),
    }
    return render_template("dashboard.html", user=current_user, stats=stats)
