from datetime import datetime
from flask import render_template, session, redirect, url_for, abort, flash

from . import main
from .. import db
from ..models import User
from flask_login import current_user, login_required
from .forms import EditProfileForm, EditProfileAdminForm
from ..decorators import admin_required
from ..models import Role


@main.route("/", methods=["GET", "POST"])
def index():
    return render_template("index.html")


@main.route("/user/<int:id>")
def user(id):
    user = User.query.filter_by(id=id).first()
    if user is None:
        abort(404)
    return render_template("user.html", user=user)


@main.route("/edit-profile", methods=["GET", "POST"])
@login_required
def edit_profile():
    form = EditProfileForm()
    if form.validate_on_submit():
        current_user.name = form.name.data
        current_user.location = form.location.data
        current_user.about_me = form.about_me.data
        db.session.add(user)
        flash("Your profile has been updated.")
        return redirect(url_for(".user", id=current_user.id))
    form.name.data = current_user.name
    form.location.data = current_user.location
    form.about_me.data = current_user.about_me
    return render_template("edit_profile.html", form=form, user=current_user)


@main.route("/edit-profile/<int:id>", methods=["GET", "POST"])
@login_required
@admin_required
def edit_profile_admin(id):
    user = User.query.get_or_404(id)
    form = EditProfileAdminForm(user=user)
    if form.validate_on_submit():
        user.role = Role.query.get(form.role.data)
        user.name = form.name.data
        user.location = form.location.data
        user.about_me = form.about_me.data
        db.session.add(user)
        flash("The profile has been updated.")
        return redirect(url_for(".user", id=user.id))
    form.role.data = user.role_id
    form.name.data = user.name
    form.location.data = user.location
    form.about_me.data = user.about_me
    return render_template("edit_profile.html", form=form, user=user)
