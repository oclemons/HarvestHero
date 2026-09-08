"""Inventory list + item detail.

Phase 1b: read-only. Add / edit / delete arrive in Phase 1c.

The list view leans on ``Database.get_all_items(search)`` — the same
query the desktop app uses — so the two frontends can never disagree
about which items exist. Filtering happens in SQL via the shared query;
pagination happens in Python since the current dataset is small and
adding SQL-level LIMIT/OFFSET would mean touching database.py.
"""

from __future__ import annotations

from math import ceil

from flask import Blueprint, abort, render_template, request
from flask_login import login_required

from database import Database


bp = Blueprint("inventory", __name__, url_prefix="/inventory")

_db = Database()

# How many items to show per page in the list view. Keeps the initial
# HTML tiny (< 100 rows) even for pantries that grow to thousands.
_PAGE_SIZE = 25


@bp.route("/")
@login_required
def list_items():
    search = (request.args.get("q") or "").strip()

    # get_all_items handles empty-string search fine (returns everything).
    all_items = _db.get_all_items(search) or []

    total_matches = len(all_items)
    total_pages   = max(1, ceil(total_matches / _PAGE_SIZE))

    try:
        page = max(1, int(request.args.get("page", "1")))
    except ValueError:
        page = 1
    page = min(page, total_pages)

    start = (page - 1) * _PAGE_SIZE
    end   = start + _PAGE_SIZE
    page_items = all_items[start:end]

    return render_template(
        "inventory/list.html",
        items=page_items,
        search=search,
        page=page,
        total_pages=total_pages,
        total_matches=total_matches,
        page_size=_PAGE_SIZE,
        low_stock_ids=_low_stock_id_set(),
    )


@bp.route("/<int:item_id>")
@login_required
def detail(item_id: int):
    item = _db.get_item_by_id(item_id)
    if not item:
        abort(404)
    return render_template("inventory/detail.html",
                           item=item,
                           is_low=_is_low_stock(item))


# ─────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────

def _low_stock_id_set() -> set[int]:
    """IDs of every item currently at/below its minimum stock threshold.

    Used to badge rows on the list view without doing an N+1 database
    hit per row. Cached per request implicitly by not caching at all —
    a single call to get_low_stock_items is cheap on this dataset."""
    try:
        return {row["id"] for row in _db.get_low_stock_items() or []}
    except Exception:
        return set()


def _is_low_stock(item: dict) -> bool:
    """Match the SQL definition in database.get_low_stock_items:
    minimum_stock > 0 AND current_quantity < minimum_stock."""
    try:
        qty = int(item.get("current_quantity") or 0)
        min_stock = int(item.get("minimum_stock") or 0)
        return min_stock > 0 and qty < min_stock
    except (TypeError, ValueError):
        return False
