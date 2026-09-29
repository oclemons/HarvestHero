"""Administrator-managed physical pantry sections and shelves."""

from pathlib import Path

from flask import Blueprint, abort, flash, redirect, render_template, request, send_from_directory, url_for
from flask_login import current_user, login_required

from decorators import admin_required

bp = Blueprint("sections", __name__, url_prefix="/pantry")

_REFERENCE_DIR = Path(__file__).resolve().parents[2] / "input" / "Inventory"
_REFERENCE_IMAGES = tuple(f"822{number}.jpg" for number in range(13, 23))


def _visible_layout():
    from database import Database
    sections = Database().get_pantry_layout(include_items=True)
    visible = []
    for section in sections:
        if section["system"]:
            section["pending_items"] = [item for shelf in section["shelves"]
                                        for item in shelf["items"]]
            if not section["pending_items"] and not any(
                shelf["units"] for shelf in section["shelves"]
            ):
                continue
        visible.append(section)
    return visible


@bp.route("/")
@login_required
@admin_required
def index():
    references = [name for name in _REFERENCE_IMAGES if (_REFERENCE_DIR / name).is_file()]
    return render_template("sections/index.html", sections=_visible_layout(), references=references)


@bp.route("/references/<filename>")
@login_required
@admin_required
def reference_image(filename: str):
    if filename not in _REFERENCE_IMAGES or not (_REFERENCE_DIR / filename).is_file():
        abort(404)
    return send_from_directory(_REFERENCE_DIR, filename, max_age=3600)


@bp.route("/sections", methods=["POST"])
@login_required
@admin_required
def create_section():
    from database import Database
    try:
        Database().create_pantry_section(request.form.get("name") or "")
    except ValueError as error:
        flash(str(error), "error")
        return render_template("sections/index.html", sections=_visible_layout()), 400
    flash("Section added. Add shelves to organize stock.", "success")
    return redirect(url_for("sections.index"))


@bp.route("/shelves", methods=["POST"])
@login_required
@admin_required
def create_shelf():
    from database import Database
    try:
        section_id = int(request.form.get("section_id") or "")
        Database().create_pantry_shelf(
            section_id, request.form.get("name") or "",
            is_overflow=request.form.get("is_overflow") == "on",
        )
    except ValueError as error:
        flash(str(error), "error")
        return render_template("sections/index.html", sections=_visible_layout()), 400
    flash("Shelf added. It is ready even while empty.", "success")
    return redirect(url_for("sections.index"))


@bp.route("/sections/<int:section_id>/edit", methods=["POST"])
@login_required
@admin_required
def edit_section(section_id: int):
    from database import Database
    try:
        Database().rename_pantry_section(section_id, request.form.get("name") or "",
                                         current_user.username)
    except ValueError as error:
        flash(str(error), "error")
        return render_template("sections/index.html",
                               sections=_visible_layout()), 400
    flash("Section renamed; its shelves and stock stayed in place.", "success")
    return redirect(url_for("sections.index"))


@bp.route("/shelves/<int:shelf_id>/edit", methods=["POST"])
@login_required
@admin_required
def edit_shelf(shelf_id: int):
    from database import Database
    try:
        Database().update_pantry_shelf(shelf_id, request.form.get("name") or "",
                                       request.form.get("is_overflow") == "on",
                                       current_user.username)
    except ValueError as error:
        flash(str(error), "error")
        return render_template("sections/index.html",
                               sections=_visible_layout()), 400
    flash("Shelf updated; all food and stock counts stayed assigned to it.", "success")
    return redirect(url_for("sections.index"))
