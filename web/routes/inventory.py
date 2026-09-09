"""Inventory list + item detail + add + edit + delete + adjust.

Phase 1c-i: add. 1c-ii: edit. 1c-iii: delete. 1c-iv: adjust
quantity (single-field inline form on the detail page).
Barcode scan is a separate later commit.

The list view leans on ``Database.get_all_items(search)`` — the same
query the desktop app uses — so the two frontends can never disagree
about which items exist. Filtering happens in SQL via the shared query;
pagination happens in Python since the current dataset is small and
adding SQL-level LIMIT/OFFSET would mean touching database.py.
"""

from __future__ import annotations

from math import ceil

from flask import (
    Blueprint, abort, flash, redirect, render_template, request, url_for,
)
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
# Add a new item
# ─────────────────────────────────────────────────────────────────

@bp.route("/new", methods=["GET", "POST"])
@login_required
def new():
    """Show the add-item form (GET) or create one (POST).

    Role gating: none for now. When user management lands in a later
    phase we'll add @admin_required. Today, any authenticated user
    (i.e. anyone with a password from the admin) can add an item.
    """
    if request.method == "GET":
        return render_template("inventory/form.html",
                               mode="new", item=_blank_item())

    data, err = _parse_form(request.form)
    if err:
        flash(err, "error")
        return render_template("inventory/form.html",
                               mode="new", item=data), 400

    ok, msg = _db.add_item(
        barcode          = data["barcode"],
        item_name        = data["item_name"],
        category         = data["category"],
        quantity         = data["current_quantity"],
        minimum_stock    = data["minimum_stock"],
        notes            = data["notes"],
        barcode_out      = data["barcode_out"],
        brand            = data["brand"],
        storage_location = data["storage_location"],
    )
    if not ok:
        flash(msg, "error")
        return render_template("inventory/form.html",
                               mode="new", item=data), 400

    flash(f"Added '{data['item_name']}' to inventory.", "success")
    row = _db.get_item_by_barcode(data["barcode"])
    if row:
        return redirect(url_for("inventory.detail", item_id=row["id"]))
    return redirect(url_for("inventory.list_items"))


# ─────────────────────────────────────────────────────────────────
# Edit an existing item
# ─────────────────────────────────────────────────────────────────

@bp.route("/<int:item_id>/edit", methods=["GET", "POST"])
@login_required
def edit(item_id: int):
    """Show the edit form (GET) or save changes (POST).

    ``barcode`` is intentionally not editable — changing the primary
    barcode of an existing item would silently orphan any barcode
    labels already printed for it. If the barcode is truly wrong,
    delete + re-add is the safer path.

    Quantity IS editable here (it goes through set_stock). For daily
    increment/decrement, phase 1c-v's Scan page is the intended tool.
    """
    row = _db.get_item_by_id(item_id)
    if not row:
        abort(404)

    if request.method == "GET":
        return render_template("inventory/form.html",
                               mode="edit", item=row)

    data, err = _parse_form(request.form, editing=True,
                            existing_barcode=row["barcode"])
    if err:
        flash(err, "error")
        # Preserve the submitted values so the user's typing isn't lost.
        # Add id + readonly barcode back in so the template's Cancel /
        # Back links still resolve.
        preserved = dict(data)
        preserved["id"]      = row["id"]
        preserved["barcode"] = row["barcode"]
        return render_template("inventory/form.html",
                               mode="edit", item=preserved), 400

    # 1. Core fields via update_item (item_name, category,
    #    minimum_stock, notes, barcode_out)
    _db.update_item(
        item_id       = item_id,
        item_name     = data["item_name"],
        category      = data["category"],
        minimum_stock = data["minimum_stock"],
        notes         = data["notes"],
        barcode_out   = data["barcode_out"],
    )
    # 2. Extended fields via update_item_extended (brand,
    #    storage_location, ...). Only brand + storage_location are
    #    exposed on this form; the rest stay at their existing values.
    _db.update_item_extended(
        item_id          = item_id,
        brand            = data["brand"],
        storage_location = data["storage_location"],
    )
    # 3. Quantity change if it moved.
    if int(data["current_quantity"]) != int(row.get("current_quantity") or 0):
        _db.set_stock(item_id, data["current_quantity"])

    flash(f"Saved changes to '{data['item_name']}'.", "success")
    return redirect(url_for("inventory.detail", item_id=item_id))


# ─────────────────────────────────────────────────────────────────
# Delete an item
# ─────────────────────────────────────────────────────────────────

@bp.route("/<int:item_id>/delete", methods=["POST"])
@login_required
def delete(item_id: int):
    """Hard delete. The template pairs this with a JS confirm() so a
    stray click can't destroy inventory; the two guards together are
    good enough for MVP.

    POST-only intentionally — GET would let a link in an email or an
    open redirect trigger a delete just by being fetched. The
    template submits via a small inline <form>.
    """
    row = _db.get_item_by_id(item_id)
    if not row:
        abort(404)
    name = row["item_name"]
    _db.delete_item(item_id)
    flash(f"Deleted '{name}'.", "success")
    return redirect(url_for("inventory.list_items"))


# ─────────────────────────────────────────────────────────────────
# Directly set an item's quantity
# ─────────────────────────────────────────────────────────────────

@bp.route("/<int:item_id>/adjust", methods=["POST"])
@login_required
def adjust(item_id: int):
    """Set current_quantity to whatever the form field says.

    Purpose: correcting a mistake without walking through the full
    Edit form. For daily +1/-1 the Scan page (1c-v) is the tool.

    Refuses negative values silently — flash the error and redirect
    back to the detail page so the user sees what went wrong.
    """
    row = _db.get_item_by_id(item_id)
    if not row:
        abort(404)

    raw = (request.form.get("quantity") or "").strip()
    try:
        new_qty = int(raw)
        if new_qty < 0:
            raise ValueError("negative")
    except ValueError:
        flash("Quantity must be a non-negative whole number.", "error")
        return redirect(url_for("inventory.detail", item_id=item_id))

    if new_qty == int(row.get("current_quantity") or 0):
        flash("Quantity was already at that value; nothing changed.", "info")
        return redirect(url_for("inventory.detail", item_id=item_id))

    _db.set_stock(item_id, new_qty)
    flash(f"Quantity set to {new_qty}.", "success")
    return redirect(url_for("inventory.detail", item_id=item_id))


# ─────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────

def _blank_item() -> dict:
    """Empty-form defaults so the template can iterate a consistent shape."""
    return {
        "barcode": "", "barcode_out": "",
        "item_name": "", "brand": "", "category": "",
        "current_quantity": 0, "minimum_stock": 0,
        "storage_location": "", "notes": "",
    }


def _parse_form(form, *, editing: bool = False,
                existing_barcode: str | None = None
                ) -> tuple[dict, str | None]:
    """Return ``(cleaned_data, error_or_None)``.

    On failure the cleaned dict is still returned in the shape the
    template expects, so the user's typing is not lost when we
    re-render the form with a flashed error.

    In edit mode the ``barcode`` field is force-set to the existing
    value; the form renders it as read-only but a malicious client
    could still submit a different value, so we ignore that field
    server-side rather than trust the input.
    """
    data = {
        "barcode":          (form.get("barcode") or "").strip(),
        "barcode_out":      (form.get("barcode_out") or "").strip(),
        "item_name":        (form.get("item_name") or "").strip(),
        "brand":            (form.get("brand") or "").strip(),
        "category":         (form.get("category") or "").strip(),
        "storage_location": (form.get("storage_location") or "").strip(),
        "notes":            (form.get("notes") or "").strip(),
    }
    if editing and existing_barcode is not None:
        data["barcode"] = existing_barcode
    for numeric in ("current_quantity", "minimum_stock"):
        raw = (form.get(numeric) or "").strip()
        try:
            data[numeric] = max(0, int(raw)) if raw else 0
        except ValueError:
            return data, (
                f"{numeric.replace('_', ' ').capitalize()} must be a whole "
                f"number, got '{raw}'."
            )
    if not data["barcode"]:
        return data, "Barcode is required."
    if not data["item_name"]:
        return data, "Item name is required."
    return data, None


# ─────────────────────────────────────────────────────────────────
# List-page helpers (unchanged from Phase 1b)
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
