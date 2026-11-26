"""Conference sessions."""

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from .checks import check_session_assignment
from .db import engine, fetch_all, fetch_one, run
from .helpers import (SAVE_ERRORS, error_message, required, required_date, required_int,
                      required_time)

bp = Blueprint("sessions", __name__, url_prefix="/sessions")


@bp.route("/")
def list_sessions():
    with engine.connect() as conn:
        sessions = fetch_all(conn, """
            SELECT s.*, c.acronym, u.given_name, u.surname,
                   (SELECT count(*) FROM paper p WHERE p.session_id = s.session_id) AS papers
            FROM conference_session s
            JOIN conference c ON c.conference_id = s.conference_id
            JOIN app_user u   ON u.user_id = s.chair_id
            ORDER BY s.session_id
        """)
    return render_template("sessions_list.html", sessions=sessions)


def form_choices(conn):
    return {
        "conferences": fetch_all(conn, """
            SELECT conference_id, acronym, city FROM conference ORDER BY conference_id
        """),
        # Each reviewer is shown with their pools, to help choose a valid chair.
        "chairs": fetch_all(conn, """
            SELECT u.user_id, u.given_name, u.surname,
                   string_agg(c.acronym, ', ' ORDER BY c.conference_id) AS pools
            FROM conference_reviewer cr
            JOIN app_user u   ON u.user_id = cr.reviewer_id
            JOIN conference c ON c.conference_id = cr.conference_id
            GROUP BY u.user_id, u.given_name, u.surname
            ORDER BY u.user_id
        """),
    }


def save_session(conn, form, session_id=None):
    """Create (session_id is None) or update a session."""
    values = {
        "conference_id": required_int(form, "conference_id", "Conference"),
        "title": required(form, "title", "Title"),
        "session_date": required_date(form, "session_date", "Date"),
        "start_time": required_time(form, "start_time", "Start time"),
        "end_time": required_time(form, "end_time", "End time"),
        "room_label": required(form, "room_label", "Room"),
        "chair_id": required_int(form, "chair_id", "Chair"),
    }

    if session_id is None:
        run(conn, """
            INSERT INTO conference_session (conference_id, title, session_date,
                start_time, end_time, room_label, chair_id)
            VALUES (:conference_id, :title, :session_date,
                :start_time, :end_time, :room_label, :chair_id)
        """, **values)
        return

    run(conn, """
        UPDATE conference_session
        SET conference_id = :conference_id, title = :title, session_date = :session_date,
            start_time = :start_time, end_time = :end_time,
            room_label = :room_label, chair_id = :chair_id
        WHERE session_id = :id
    """, id=session_id, **values)

    # Required check: the conference may have changed, so check every paper here.
    papers = fetch_all(conn, "SELECT paper_id FROM paper WHERE session_id = :id", id=session_id)
    for paper in papers:
        check_session_assignment(conn, paper["paper_id"])


@bp.route("/new", methods=["GET", "POST"])
def create_session():
    if request.method == "POST":
        try:
            with engine.begin() as conn:
                save_session(conn, request.form)
            flash("Session created.", "success")
            return redirect(url_for("sessions.list_sessions"))
        except SAVE_ERRORS as error:
            flash(error_message(error), "error")

    with engine.connect() as conn:
        choices = form_choices(conn)
    return render_template("session_form.html", form=request.form, title="New session",
                           **choices)


@bp.route("/<int:session_id>/edit", methods=["GET", "POST"])
def edit_session(session_id):
    with engine.connect() as conn:
        session = fetch_one(conn, "SELECT * FROM conference_session WHERE session_id = :id",
                            id=session_id)
        choices = form_choices(conn)
    if session is None:
        abort(404)

    if request.method == "POST":
        form = request.form
        try:
            with engine.begin() as conn:
                save_session(conn, form, session_id)
            flash("Session updated.", "success")
            return redirect(url_for("sessions.list_sessions"))
        except SAVE_ERRORS as error:
            flash(error_message(error), "error")
    else:
        form = dict(session)
        # The browser's time box expects HH:MM.
        form["start_time"] = session["start_time"].strftime("%H:%M")
        form["end_time"] = session["end_time"].strftime("%H:%M")

    return render_template("session_form.html", form=form, title=f"Edit session {session_id}",
                           **choices)


@bp.route("/<int:session_id>/delete", methods=["POST"])
def delete_session(session_id):
    with engine.begin() as conn:
        # Papers in this session are kept; their session_id becomes NULL.
        deleted = run(conn, "DELETE FROM conference_session WHERE session_id = :id",
                      id=session_id).rowcount
    if not deleted:
        abort(404)
    flash("Session deleted. Its papers are kept without a session.", "success")
    return redirect(url_for("sessions.list_sessions"))
