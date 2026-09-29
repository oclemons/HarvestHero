"""Dashboard with inventory health and monthly weight metrics."""

from __future__ import annotations

import datetime

from flask import Blueprint, render_template
from flask_login import current_user, login_required

from database import Database


bp = Blueprint("dashboard", __name__)

_db = Database()


@bp.route("/app")
@login_required
def home():
    items    = _db.get_all_items()
    low      = _db.get_low_stock_items()
    stats = {
        "total_items": len(items),
        "low_stock": len(low),
    }
    month_summary = None
    if current_user.is_admin:
        stats["active_users"] = sum(1 for u in _db.get_all_users() if u.get("is_active"))
        activity = _db.get_recent_movements(8)
        month = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m")
        try:
            month_summary = _db.get_monthly_weight_report(month)
        except ValueError:
            pass
    else:
        activity = _db.get_recent_transactions_by_user(current_user.username, 5)
    return render_template("dashboard.html", user=current_user, stats=stats,
                           activity=activity, month_summary=month_summary)
