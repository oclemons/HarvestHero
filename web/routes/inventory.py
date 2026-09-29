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
    Blueprint, Response, abort, current_app, flash, redirect, render_template, request, url_for,
)
from itsdangerous import BadSignature, URLSafeTimedSerializer
from flask_login import current_user, login_required

from database import Database, INVENTORY_COLUMNS
from decorators import admin_required


bp = Blueprint("inventory", __name__, url_prefix="/inventory")

_db = Database()

# How many items to show per page in the list view. Keeps the initial
# HTML tiny (< 100 rows) even for pantries that grow to thousands.
_PAGE_SIZE = 25
_COLUMN_LABELS = {"barcode": "Barcode", "item": "Item", "category": "Category",
                  "quantity": "Qty", "minimum": "Min", "location": "Location"}


@bp.route("/")
@login_required
def list_items():
    search = (request.args.get("q") or "").strip()[:100]
    columns = (_db.get_inventory_columns(int(current_user.id))
               if current_user.is_admin else list(INVENTORY_COLUMNS))
    requested_sort = request.args.get("sort") or "item"
    sort = requested_sort if requested_sort in columns else "item"
    direction = ("desc" if requested_sort in columns and
                 request.args.get("direction") == "desc" else "asc")

    # get_all_items handles empty-string search fine (returns everything).
    all_items = _db.get_all_items(search, sort=sort, direction=direction) or []
    if sort == "location":
        all_locations = _db.get_item_locations([item["id"] for item in all_items])
        all_items.sort(key=lambda item: (all_locations.get(item["id"], "").casefold(),
                                         item["item_name"].casefold(), item["id"]),
                       reverse=direction == "desc")

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
        locations=(all_locations if sort == "location" else
                   _db.get_item_locations([item["id"] for item in page_items])),
        columns=columns, column_labels=_COLUMN_LABELS, all_columns=INVENTORY_COLUMNS,
        sort=sort, direction=direction,
    )


@bp.route("/columns", methods=["POST"])
@login_required
@admin_required
def save_columns():
    visible = request.form.getlist("visible")
    if (not visible or "item" not in visible or len(visible) != len(set(visible)) or
            any(column not in INVENTORY_COLUMNS for column in visible)):
        abort(400)
    try:
        positions = {column: int(request.form.get(f"position_{column}") or "")
                     for column in visible}
    except ValueError:
        abort(400)
    if any(not 1 <= position <= len(INVENTORY_COLUMNS) for position in positions.values()):
        abort(400)
    ordered = sorted(visible, key=lambda column: (positions[column],
                                                   INVENTORY_COLUMNS.index(column)))
    try:
        _db.save_inventory_columns(int(current_user.id), ordered)
    except ValueError:
        abort(400)
    flash("Your inventory columns were saved.", "success")
    return redirect(url_for("inventory.list_items", q=request.form.get("q") or "",
                            sort=request.form.get("sort") or "item",
                            direction=request.form.get("direction") or "asc",
                            page=request.form.get("page") or "1"))


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
# Inventory entry, catalog import, and labels
# ─────────────────────────────────────────────────────────────────

def _catalog_signer():
    return URLSafeTimedSerializer(current_app.secret_key, salt="inventory-catalog-review-v1")


@bp.route("/import")
@login_required
@admin_required
def import_catalog():
    return render_template("inventory/import_upload.html")


@bp.route("/import/preview", methods=["POST"])
@login_required
@admin_required
def import_preview():
    from catalog_import import parse_catalog
    uploaded = request.files.get("file")
    if not uploaded:
        flash("Choose an inventory CSV file to review.", "error")
        return render_template("inventory/import_upload.html"), 400
    try:
        rows = parse_catalog(uploaded.read())
    except ValueError as error:
        flash(str(error), "error")
        return render_template("inventory/import_upload.html"), 400
    token = _catalog_signer().dumps({"owner": current_user.id, "rows": rows})
    return render_template("inventory/import_preview.html", rows=rows, preview_token=token)


@bp.route("/import/confirm", methods=["POST"])
@login_required
@admin_required
def import_confirm():
    try:
        payload = _catalog_signer().loads(request.form.get("preview_token") or "", max_age=1800)
    except BadSignature:
        flash("This catalog preview expired or was changed. Upload it again.", "error")
        return render_template("inventory/import_upload.html"), 400
    if payload.get("owner") != current_user.id:
        abort(403)
    rows = payload.get("rows")
    if not isinstance(rows, list) or len(rows) > 150:
        abort(400)
    selected = request.form.getlist("selected")
    try:
        indexes = sorted({int(value) for value in selected})
    except ValueError:
        indexes = []
    if not indexes or any(index < 0 or index >= len(rows) or rows[index].get("problem") for index in indexes):
        flash("Select one or more valid rows from the preview.", "error")
        return render_template("inventory/import_preview.html", rows=rows, preview_token=request.form["preview_token"]), 400
    try:
        count = _db.import_catalog_rows([rows[index] for index in indexes], current_user.username)
    except ValueError as error:
        flash(str(error), "error")
        return render_template("inventory/import_preview.html", rows=rows, preview_token=request.form["preview_token"]), 400
    flash(f"Imported {count} catalog item(s) with zero stock. Review item weights and count shelves before scanning.", "success")
    return redirect(url_for("inventory.list_items"))


@bp.route("/<int:item_id>/labels")
@login_required
@admin_required
def labels(item_id: int):
    item = _db.get_item_by_id(item_id)
    if not item:
        abort(404)
    response = render_template("inventory/labels.html", item=item,
                               locations=_db.get_item_locations([item_id]).get(item_id, "Unassigned"))
    return response, 200, {"Cache-Control": "private, no-store"}


@bp.route("/<int:item_id>/barcode/<direction>.svg")
@login_required
@admin_required
def barcode_image(item_id: int, direction: str):
    item = _db.get_item_by_id(item_id)
    if not item or direction not in ("in", "out"):
        abort(404)
    value = item["barcode"] if direction == "in" else item["barcode_out"]
    if not value:
        abort(404)
    from barcode_labels import render_barcode
    try:
        image = render_barcode(value)
    except ValueError:
        abort(404)
    return Response(image, mimetype="image/svg+xml",
                    headers={"Cache-Control": "private, no-store"})


@bp.route("/new", methods=["GET", "POST"])
@login_required
@admin_required
def new():
    """Let an Admin add an item with a selected shelf and generated pantry labels."""
    sections = _db.get_pantry_layout()
    if request.method == "GET":
        return render_template("inventory/form.html", mode="new", item=_blank_item(),
                               sections=sections)

    data, err = _parse_form(request.form)
    data["shelf_id"] = request.form.get("shelf_id") or ""
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
                username=current_user.username,
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
    """Edit item metadata without changing printed barcodes or shelf stock."""
    row = _db.get_item_by_id(item_id)
    if not row:
        abort(404)

    if request.method == "GET":
        return render_template("inventory/form.html", mode="edit", item=row)

    data, err = _parse_form(request.form, editing=True,
                            existing_barcode=row["barcode"])
    # Quantity changes must name a physical shelf.
    if "current_quantity" in request.form and data["current_quantity"] != row["current_quantity"]:
        err = "Use the item detail page to correct stock on a specific shelf."
    if not err:
        try:
            _db.update_item_profile(
                item_id, data["item_name"], data["category"], data["minimum_stock"],
                data["notes"], data["barcode_out"], data["brand"], None,
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
    if request.form.get("redirect_to") == "pantry":
        return redirect(url_for("sections.index"))
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
    if editing and not data["barcode"]:
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
