"""Users, including their author and reviewer profiles."""

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from sqlalchemy.exc import IntegrityError

from .db import engine, fetch_all, fetch_one, run
from .helpers import (SAVE_ERRORS, FormError, error_message, lines, optional,
                      required, required_int)

bp = Blueprint("users", __name__, url_prefix="/users")


@bp.route("/")
def list_users():
    with engine.connect() as conn:
        users = fetch_all(conn, """
            SELECT u.*,
                   a.author_id IS NOT NULL   AS is_author,
                   r.reviewer_id IS NOT NULL AS is_reviewer
            FROM app_user u
            LEFT JOIN author a   ON a.author_id = u.user_id
            LEFT JOIN reviewer r ON r.reviewer_id = u.user_id
            ORDER BY u.user_id
        """)
    return render_template("users_list.html", users=users)


def load_user(conn, user_id):
    """Read one user and return it in the same shape as the HTML form."""
    user = fetch_one(conn, "SELECT * FROM app_user WHERE user_id = :id", id=user_id)
    if user is None:
        abort(404)
    form = dict(user)

    author = fetch_one(conn, "SELECT orcid FROM author WHERE author_id = :id", id=user_id)
    if author:
        areas = fetch_all(conn, """SELECT area_label FROM author_research_area
                                   WHERE author_id = :id ORDER BY area_label""", id=user_id)
        form["is_author"] = "on"
        form["orcid"] = author["orcid"] or ""
        form["research_areas"] = "\n".join(row["area_label"] for row in areas)

    reviewer = fetch_one(conn, "SELECT years_experience FROM reviewer WHERE reviewer_id = :id",
                         id=user_id)
    if reviewer:
        areas = fetch_all(conn, """SELECT area_label FROM reviewer_expertise
                                   WHERE reviewer_id = :id ORDER BY area_label""", id=user_id)
        form["is_reviewer"] = "on"
        form["years_experience"] = reviewer["years_experience"]
        form["expertise"] = "\n".join(row["area_label"] for row in areas)

    return form


def save_user(conn, form, user_id=None):
    """Create (user_id is None) or update a user and both profiles."""
    values = {
        "given_name": required(form, "given_name", "Given name"),
        "surname": required(form, "surname", "Surname"),
        "email": required(form, "email", "Email").lower(),
        "affiliation": required(form, "affiliation", "Affiliation"),
        "country": required(form, "country", "Country"),
        "phone_number": required(form, "phone_number", "Phone number"),
    }
    is_author = "is_author" in form
    is_reviewer = "is_reviewer" in form
    if not is_author and not is_reviewer:
        raise FormError("A user must be an author, a reviewer, or both.")

    if user_id is None:
        user_id = run(conn, """
            INSERT INTO app_user (given_name, surname, email, affiliation, country, phone_number)
            VALUES (:given_name, :surname, :email, :affiliation, :country, :phone_number)
            RETURNING user_id
        """, **values).scalar_one()
    else:
        run(conn, """
            UPDATE app_user
            SET given_name = :given_name, surname = :surname, email = :email,
                affiliation = :affiliation, country = :country, phone_number = :phone_number
            WHERE user_id = :id
        """, id=user_id, **values)

    save_author_profile(conn, form, user_id, is_author)
    save_reviewer_profile(conn, form, user_id, is_reviewer)


def save_author_profile(conn, form, user_id, is_author):
    if not is_author:
        try:
            # This fails if the author still has papers.
            run(conn, "DELETE FROM author WHERE author_id = :id", id=user_id)
        except IntegrityError:
            raise FormError("Cannot remove the author role: this user is an author of a paper.")
        return

    areas = lines(form, "research_areas", "research area")
    run(conn, """
        INSERT INTO author (author_id, orcid) VALUES (:id, :orcid)
        ON CONFLICT (author_id) DO UPDATE SET orcid = :orcid
    """, id=user_id, orcid=optional(form, "orcid"))

    # Simplest way to update a list: delete the old items and insert the new ones.
    run(conn, "DELETE FROM author_research_area WHERE author_id = :id", id=user_id)
    for area in areas:
        run(conn, "INSERT INTO author_research_area VALUES (:id, :area)", id=user_id, area=area)


def save_reviewer_profile(conn, form, user_id, is_reviewer):
    if not is_reviewer:
        try:
            # This fails if the reviewer has reviews, pools, tracks or sessions.
            run(conn, "DELETE FROM reviewer WHERE reviewer_id = :id", id=user_id)
        except IntegrityError:
            raise FormError("Cannot remove the reviewer role: this user is still used by "
                            "a review, conference pool, track or session.")
        return

    years = required_int(form, "years_experience", "Years of experience")
    areas = lines(form, "expertise", "expertise area")
    run(conn, """
        INSERT INTO reviewer (reviewer_id, years_experience) VALUES (:id, :years)
        ON CONFLICT (reviewer_id) DO UPDATE SET years_experience = :years
    """, id=user_id, years=years)

    run(conn, "DELETE FROM reviewer_expertise WHERE reviewer_id = :id", id=user_id)
    for area in areas:
        run(conn, "INSERT INTO reviewer_expertise VALUES (:id, :area)", id=user_id, area=area)


@bp.route("/new", methods=["GET", "POST"])
def create_user():
    if request.method == "POST":
        try:
            # engine.begin() = one transaction: commit on success, roll back on error.
            with engine.begin() as conn:
                save_user(conn, request.form)
            flash("User created.", "success")
            return redirect(url_for("users.list_users"))
        except SAVE_ERRORS as error:
            flash(error_message(error), "error")

    # On an error, request.form keeps what the user typed.
    return render_template("user_form.html", form=request.form, title="New user")


@bp.route("/<int:user_id>/edit", methods=["GET", "POST"])
def edit_user(user_id):
    with engine.connect() as conn:
        form = load_user(conn, user_id)

    if request.method == "POST":
        form = request.form
        try:
            with engine.begin() as conn:
                save_user(conn, form, user_id)
            flash("User updated.", "success")
            return redirect(url_for("users.list_users"))
        except SAVE_ERRORS as error:
            flash(error_message(error), "error")

    return render_template("user_form.html", form=form, title=f"Edit user {user_id}")


@bp.route("/<int:user_id>/delete", methods=["POST"])
def delete_user(user_id):
    try:
        with engine.begin() as conn:
            # The author and reviewer profiles are deleted automatically (cascade).
            deleted = run(conn, "DELETE FROM app_user WHERE user_id = :id", id=user_id).rowcount
        if not deleted:
            abort(404)
        flash("User deleted.", "success")
    except IntegrityError:
        flash("Cannot delete this user: they are still used by a paper, review, "
              "conference pool, track or session.", "error")
    return redirect(url_for("users.list_users"))
