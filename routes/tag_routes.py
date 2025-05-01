from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user

from extensions import db
from models import Tag
from services.wrappers import login_required_dev

tag_bp = Blueprint("tag", __name__)


@tag_bp.route("/tags")
@login_required_dev
def manage_tags():
    tags = Tag.query.filter_by(user_id=current_user.id).all()
    return render_template("tags.html", tags=tags)


@tag_bp.route("/tags/add", methods=["POST"])
@login_required_dev
def add_tag():
    name = request.form.get("name")
    color = request.form.get("color", "#6c757d")

    # Check if tag already exists for this user
    existing_tag = Tag.query.filter_by(
        user_id=current_user.id, name=name
    ).first()
    if existing_tag:
        flash("Tag with this name already exists")
        return redirect(url_for("manage_tags"))

    tag = Tag(name=name, color=color, user_id=current_user.id)
    db.session.add(tag)
    db.session.commit()

    flash("Tag added successfully")
    return redirect(url_for("manage_tags"))


@tag_bp.route("/tags/delete/<int:tag_id>", methods=["POST"])
@login_required_dev
def delete_tag(tag_id):
    tag = Tag.query.get_or_404(tag_id)

    # Check if tag belongs to current user
    if tag.user_id != current_user.id:
        flash("You don't have permission to delete this tag")
        return redirect(url_for("manage_tags"))

    db.session.delete(tag)
    db.session.commit()

    flash("Tag deleted successfully")
    return redirect(url_for("manage_tags"))
