"""Administrator-managed physical pantry sections and shelves."""

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from decorators import admin_required

bp = Blueprint("sections", __name__, url_prefix="/pantry")


@bp.route("/")
@login_required
@admin_required
def index():
    from database import Database
    return render_template("sections/index.html", sections=Database().get_pantry_layout(include_items=True))


@bp.route("/sections", methods=["POST"])
@login_required
@admin_required
def create_section():
    from database import Database
    try:
        Database().create_pantry_section(request.form.get("name") or "")
    except ValueError as error:
        flash(str(error), "error")
        return render_template("sections/index.html", sections=Database().get_pantry_layout(include_items=True)), 400
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
        return render_template("sections/index.html", sections=Database().get_pantry_layout(include_items=True)), 400
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
                               sections=Database().get_pantry_layout(include_items=True)), 400
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
                               sections=Database().get_pantry_layout(include_items=True)), 400
    flash("Shelf updated; all food and stock counts stayed assigned to it.", "success")
    return redirect(url_for("sections.index"))
