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

from decimal import Decimal, InvalidOperation
from math import ceil

from flask import (
    Blueprint, abort, flash, redirect, render_template, request, url_for,
)
from flask_login import current_user, login_required

from database import Database
from decorators import admin_required


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
        locations=_db.get_item_locations([item["id"] for item in page_items]),
    )


@bp.route("/<int:item_id>")
@login_required
def detail(item_id: int):
    item = _db.get_item_by_id(item_id)
    if not item:
        abort(404)
    return render_template("inventory/detail.html", item=item,
                           allocations=_db.get_item_shelf_stock(item_id),
                           sections=_db.get_pantry_layout() if current_user.is_admin else [],
                           is_low=_is_low_stock(item))


# ─────────────────────────────────────────────────────────────────
# Add a new item
# ─────────────────────────────────────────────────────────────────

@bp.route("/new", methods=["GET", "POST"])
@login_required
@admin_required
def new():
    """Show the add-item form (GET) or create one (POST).

    Role gating: none for now. When user management lands in a later
    phase we'll add @admin_required. Today, any authenticated user
    (i.e. anyone with a password from the admin) can add an item.
    """
    sections = _db.get_pantry_layout()
    if request.method == "GET":
        return render_template("inventory/form.html", mode="new", item=_blank_item(),
                               sections=sections)

    data, err = _parse_form(request.form)
    data["shelf_id"] = request.form.get("shelf_id") or ""
    data["unit_weight_lb"] = (request.form.get("unit_weight_lb") or "").strip()
    unit_weight, weight_error = _parse_unit_weight(data["unit_weight_lb"])
    err = err or weight_error
    if not err:
        try:
            shelf_id = int(data["shelf_id"])
        except (ValueError, TypeError):
            err = "Choose a shelf before adding an item."
    if not err:
        try:
            item_id = _db.create_item_on_shelf(
                barcode=data["barcode"], item_name=data["item_name"],
                category=data["category"], quantity=data["current_quantity"],
                minimum_stock=data["minimum_stock"], shelf_id=shelf_id,
                username=current_user.username, unit_weight_milli_lb=unit_weight,
                barcode_out=data["barcode_out"], brand=data["brand"], notes=data["notes"],
            )
        except ValueError as error:
            err = str(error)
    if err:
        flash(err, "error")
        return render_template("inventory/form.html", mode="new", item=data,
                               sections=sections), 400

    flash(f"Added '{data['item_name']}' to inventory.", "success")
    return redirect(url_for("inventory.detail", item_id=item_id))


# ─────────────────────────────────────────────────────────────────
# Edit an existing item
# ─────────────────────────────────────────────────────────────────

@bp.route("/<int:item_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
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
        return render_template("inventory/form.html", mode="edit", item=row)

    data, err = _parse_form(request.form, editing=True,
                            existing_barcode=row["barcode"])
    # 2. Unit weights stay on the catalog row, while shelf quantities
    #    are managed on the item detail page rather than this form.
    data["unit_weight_lb"] = (request.form.get("unit_weight_lb") or "").strip()
    unit_weight, weight_error = _parse_unit_weight(data["unit_weight_lb"])
    err = err or weight_error
    # 3. Quantity changes must name a physical shelf.
    if "current_quantity" in request.form and data["current_quantity"] != row["current_quantity"]:
        err = "Use the item detail page to correct stock on a specific shelf."
    # 1. Update item identity and metadata atomically, preserving
    #    existing expiration and nutrition fields not shown here.
    #    Stock transfers and corrections are separate transactions.
    if not err:
        try:
            _db.update_item_profile(
                item_id, data["item_name"], data["category"], data["minimum_stock"],
                data["notes"], data["barcode_out"], data["brand"], unit_weight,
                current_user.username,
            )
        except ValueError as error:
            err = str(error)
    if err:
        flash(err, "error")
        # Preserve the submitted values so the user's typing isn't lost.
        # Add id + readonly barcode back in so the template's Cancel /
        # Back links still resolve.
        preserved = dict(data)
        preserved["id"]      = row["id"]
        preserved["barcode"] = row["barcode"]
        preserved["current_quantity"] = row["current_quantity"]
        return render_template("inventory/form.html", mode="edit", item=preserved), 400

    flash(f"Saved changes to '{data['item_name']}'.", "success")
    return redirect(url_for("inventory.detail", item_id=item_id))


# ─────────────────────────────────────────────────────────────────
# Delete an item
# ─────────────────────────────────────────────────────────────────

@bp.route("/<int:item_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete(item_id: int):
    """Delete an empty, unused catalog item only after barcode confirmation."""
    if not _db.get_item_by_id(item_id):
        abort(404)
    try:
        name = _db.delete_empty_item(item_id, request.form.get("confirm_barcode") or "",
                                     current_user.username)
    except ValueError as error:
        flash(str(error), "error")
        return redirect(url_for("inventory.detail", item_id=item_id))
    flash(f"Deleted '{name}'.", "success")
    return redirect(url_for("inventory.list_items"))


# ─────────────────────────────────────────────────────────────────
# Directly set an item's quantity
# ─────────────────────────────────────────────────────────────────

@bp.route("/<int:item_id>/adjust", methods=["POST"])
@login_required
@admin_required
def adjust(item_id: int):
    """Correct the on-hand count on one shelf with a reason and stale-form check."""
    row = _db.get_item_by_id(item_id)
    if not row:
        abort(404)

    try:
        shelf_id = int(request.form.get("shelf_id") or "")
        new_qty = int(request.form.get("quantity") or "")
        expected = int(request.form.get("expected_quantity") or "")
        reason = (request.form.get("reason") or "").strip()
        if new_qty < 0 or not reason:
            raise ValueError("Enter a non-negative count and a correction reason.")
        previous = next((entry for entry in _db.get_item_shelf_stock(item_id)
                         if entry["shelf_id"] == shelf_id), None)
        if previous is None:
            raise ValueError("Choose a stocked shelf to correct.")
        if previous["quantity"] != expected:
            raise ValueError("This shelf changed since you opened the page. Refresh and retry.")
        if new_qty == expected:
            flash("Quantity was already at that value; nothing changed.", "info")
            return redirect(url_for("inventory.detail", item_id=item_id))
        _db.adjust_shelf_stock(item_id, shelf_id, new_qty - expected,
                               current_user.username, reason, expected)
    except ValueError as error:
        flash(str(error), "error")
        return redirect(url_for("inventory.detail", item_id=item_id))
    flash(f"Shelf count corrected to {new_qty}.", "success")
    return redirect(url_for("inventory.detail", item_id=item_id))


@bp.route("/<int:item_id>/transfer", methods=["POST"])
@login_required
@admin_required
def transfer(item_id: int):
    if not _db.get_item_by_id(item_id):
        abort(404)
    try:
        _db.transfer_shelf_stock(
            item_id, int(request.form.get("source_id") or ""),
            int(request.form.get("destination_id") or ""),
            int(request.form.get("quantity") or ""), current_user.username,
        )
    except ValueError as error:
        flash(str(error), "error")
        return redirect(url_for("inventory.detail", item_id=item_id))
    flash("Stock moved between shelves; the total on hand is unchanged.", "success")
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
        "storage_location": "", "notes": "", "shelf_id": "",
        "unit_weight_lb": "",
    }


def _parse_unit_weight(raw: str) -> tuple[int | None, str | None]:
    if not raw:
        return None, None
    try:
        value = Decimal(raw)
    except InvalidOperation:
        return None, "Unit weight must be a number in pounds."
    if not value.is_finite() or value <= 0 or value > 10000:
        return None, "Unit weight must be positive and use at most three decimal places."
    scaled = value * 1000
    if scaled != scaled.to_integral_value():
        return None, "Unit weight must be positive and use at most three decimal places."
    return int(scaled), None


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
            data[numeric] = int(raw) if raw else 0
            if not 0 <= data[numeric] <= 1_000_000:
                raise ValueError("out of range")
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
