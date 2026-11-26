"""Completed reviews."""

from datetime import date

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from .checks import check_no_self_review
from .db import engine, fetch_all, fetch_one, run
from .helpers import (SAVE_ERRORS, error_message, optional, required, required_date,
                      required_int)

bp = Blueprint("reviews", __name__, url_prefix="/reviews")


@bp.route("/")
def list_reviews():
    with engine.connect() as conn:
        reviews = fetch_all(conn, """
            SELECT r.*, p.title AS paper_title, u.given_name, u.surname
            FROM review r
            JOIN paper p    ON p.paper_id = r.paper_id
            JOIN app_user u ON u.user_id = r.reviewer_id
            ORDER BY r.review_id
        """)
    return render_template("reviews_list.html", reviews=reviews)


def form_choices(conn):
    return {
        "papers": fetch_all(conn, "SELECT paper_id, title FROM paper ORDER BY paper_id"),
        "reviewers": fetch_all(conn, """
            SELECT r.reviewer_id, u.given_name, u.surname
            FROM reviewer r JOIN app_user u ON u.user_id = r.reviewer_id
            ORDER BY r.reviewer_id
        """),
    }


def save_review(conn, form, review_id=None):
    """Create (review_id is None) or update a review."""
    values = {
        "paper_id": required_int(form, "paper_id", "Paper"),
        "reviewer_id": required_int(form, "reviewer_id", "Reviewer"),
        "overall_score": required_int(form, "overall_score", "Score"),
        "recommendation": required(form, "recommendation", "Recommendation"),
        "comments_for_authors": required(form, "comments_for_authors", "Comments for authors"),
        "confidential_comments": optional(form, "confidential_comments"),
        "review_submission_date": required_date(form, "review_submission_date", "Review date"),
    }

    if review_id is None:
        run(conn, """
            INSERT INTO review (paper_id, reviewer_id, overall_score, recommendation,
                comments_for_authors, confidential_comments, review_submission_date)
            VALUES (:paper_id, :reviewer_id, :overall_score, :recommendation,
                :comments_for_authors, :confidential_comments, :review_submission_date)
        """, **values)
    else:
        run(conn, """
            UPDATE review
            SET paper_id = :paper_id, reviewer_id = :reviewer_id,
                overall_score = :overall_score, recommendation = :recommendation,
                comments_for_authors = :comments_for_authors,
                confidential_comments = :confidential_comments,
                review_submission_date = :review_submission_date
            WHERE review_id = :id
        """, id=review_id, **values)

    # Required check. If it fails, the insert or update is rolled back.
    check_no_self_review(conn, values["paper_id"])


@bp.route("/new", methods=["GET", "POST"])
def create_review():
    if request.method == "POST":
        form = request.form
        try:
            with engine.begin() as conn:
                save_review(conn, form)
            flash("Review created.", "success")
            return redirect(url_for("reviews.list_reviews"))
        except SAVE_ERRORS as error:
            flash(error_message(error), "error")
    else:
        form = {"review_submission_date": date.today().isoformat()}

    with engine.connect() as conn:
        choices = form_choices(conn)
    return render_template("review_form.html", form=form, title="New review", **choices)


@bp.route("/<int:review_id>/edit", methods=["GET", "POST"])
def edit_review(review_id):
    with engine.connect() as conn:
        review = fetch_one(conn, "SELECT * FROM review WHERE review_id = :id", id=review_id)
        choices = form_choices(conn)
    if review is None:
        abort(404)

    if request.method == "POST":
        form = request.form
        try:
            with engine.begin() as conn:
                save_review(conn, form, review_id)
            flash("Review updated.", "success")
            return redirect(url_for("reviews.list_reviews"))
        except SAVE_ERRORS as error:
            flash(error_message(error), "error")
    else:
        form = dict(review)
        form["confidential_comments"] = review["confidential_comments"] or ""

    return render_template("review_form.html", form=form, title=f"Edit review {review_id}",
                           **choices)


@bp.route("/<int:review_id>/delete", methods=["POST"])
def delete_review(review_id):
    with engine.begin() as conn:
        deleted = run(conn, "DELETE FROM review WHERE review_id = :id", id=review_id).rowcount
    if not deleted:
        abort(404)
    flash("Review deleted.", "success")
    return redirect(url_for("reviews.list_reviews"))
