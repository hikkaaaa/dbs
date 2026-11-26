"""Papers, including their authors, keywords and versions."""

from datetime import datetime, timezone

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from .checks import check_no_self_review, check_session_assignment
from .db import engine, fetch_all, fetch_one, run
from .helpers import (SAVE_ERRORS, FormError, error_message, lines, optional, required,
                      required_date, required_int, required_utc_datetime, to_int)

bp = Blueprint("papers", __name__, url_prefix="/papers")

STATUSES = ["submitted", "under review", "accepted", "rejected", "withdrawn"]


# ---------- Reading ----------

@bp.route("/")
def list_papers():
    with engine.connect() as conn:
        papers = fetch_all(conn, """
            SELECT p.paper_id, p.title, p.status,
                   t.name AS track_name, c.acronym, s.title AS session_title
            FROM paper p
            JOIN track t      ON t.track_id = p.track_id
            JOIN conference c ON c.conference_id = t.conference_id
            LEFT JOIN conference_session s ON s.session_id = p.session_id
            ORDER BY p.paper_id
        """)
    return render_template("papers_list.html", papers=papers)


def find_paper(conn, paper_id):
    paper = fetch_one(conn, "SELECT * FROM paper WHERE paper_id = :id", id=paper_id)
    if paper is None:
        abort(404)
    return paper


@bp.route("/<int:paper_id>")
def show_paper(paper_id):
    with engine.connect() as conn:
        paper = fetch_one(conn, """
            SELECT p.*, t.name AS track_name, c.acronym, s.title AS session_title
            FROM paper p
            JOIN track t      ON t.track_id = p.track_id
            JOIN conference c ON c.conference_id = t.conference_id
            LEFT JOIN conference_session s ON s.session_id = p.session_id
            WHERE p.paper_id = :id
        """, id=paper_id)
        if paper is None:
            abort(404)
        authors = fetch_all(conn, """
            SELECT pa.author_position, pa.is_corresponding, u.given_name, u.surname, u.email
            FROM paper_author pa
            JOIN app_user u ON u.user_id = pa.author_id
            WHERE pa.paper_id = :id
            ORDER BY pa.author_position
        """, id=paper_id)
        keywords = fetch_all(conn, """
            SELECT keyword FROM paper_keyword WHERE paper_id = :id ORDER BY keyword
        """, id=paper_id)
        versions = fetch_all(conn, """
            SELECT version_no, file_location, change_note,
                   uploaded_at AT TIME ZONE 'UTC' AS uploaded_utc
            FROM paper_version
            WHERE paper_id = :id
            ORDER BY version_no DESC
        """, id=paper_id)
    return render_template("paper_detail.html", paper=paper, authors=authors,
                           keywords=keywords, versions=versions)


# ---------- Creating and updating a paper ----------

def form_choices(conn):
    """The lists needed by the paper form."""
    return {
        "statuses": STATUSES,
        "tracks": fetch_all(conn, """
            SELECT t.track_id, t.name, c.acronym
            FROM track t JOIN conference c ON c.conference_id = t.conference_id
            ORDER BY t.track_id
        """),
        "sessions": fetch_all(conn, """
            SELECT s.session_id, s.title, c.acronym
            FROM conference_session s JOIN conference c ON c.conference_id = s.conference_id
            ORDER BY s.session_id
        """),
        "authors": fetch_all(conn, """
            SELECT a.author_id, u.given_name, u.surname, u.email
            FROM author a JOIN app_user u ON u.user_id = a.author_id
            ORDER BY a.author_id
        """),
    }


def load_paper(conn, paper_id):
    """Read one paper and return it in the same shape as the HTML form."""
    form = dict(find_paper(conn, paper_id))
    form["session_id"] = form["session_id"] or ""

    keywords = fetch_all(conn, """
        SELECT keyword FROM paper_keyword WHERE paper_id = :id ORDER BY keyword
    """, id=paper_id)
    form["keywords"] = "\n".join(row["keyword"] for row in keywords)

    for row in fetch_all(conn, "SELECT * FROM paper_author WHERE paper_id = :id", id=paper_id):
        form[f"position_{row['author_id']}"] = row["author_position"]
        if row["is_corresponding"]:
            form["corresponding"] = row["author_id"]
    return form


def read_authors(form):
    """An author is on the paper if their position box is filled in."""
    corresponding = form.get("corresponding", "")
    authors = []
    for name, value in form.items():
        if name.startswith("position_") and value.strip():
            author_id = to_int(name.removeprefix("position_"), "Author ID")
            authors.append({
                "author_id": author_id,
                "position": to_int(value, "Author position"),
                "is_corresponding": str(author_id) == corresponding,
            })

    if not authors:
        raise FormError("A paper needs at least one author (enter a position).")
    if sum(author["is_corresponding"] for author in authors) != 1:
        raise FormError("Choose exactly one corresponding author, and give them a position.")
    return authors


def save_paper(conn, form, paper_id=None):
    """Create (paper_id is None) or update a paper, its authors and its keywords."""
    session_id = optional(form, "session_id")
    values = {
        "track_id": required_int(form, "track_id", "Track"),
        "title": required(form, "title", "Title"),
        "abstract": required(form, "abstract", "Abstract"),
        "submission_date": required_date(form, "submission_date", "Submission date"),
        "status": required(form, "status", "Status"),
        "session_id": to_int(session_id, "Session") if session_id else None,
    }
    authors = read_authors(form)
    keywords = lines(form, "keywords", "keyword")

    if paper_id is None:
        paper_id = run(conn, """
            INSERT INTO paper (track_id, title, abstract, submission_date, status, session_id)
            VALUES (:track_id, :title, :abstract, :submission_date, :status, :session_id)
            RETURNING paper_id
        """, **values).scalar_one()
    else:
        run(conn, """
            UPDATE paper
            SET track_id = :track_id, title = :title, abstract = :abstract,
                submission_date = :submission_date, status = :status, session_id = :session_id
            WHERE paper_id = :id
        """, id=paper_id, **values)

    # Replace the lists. Deleting all authors first also means that changing the
    # corresponding author or swapping positions never causes a temporary clash.
    run(conn, "DELETE FROM paper_author WHERE paper_id = :id", id=paper_id)
    for author in authors:
        run(conn, """
            INSERT INTO paper_author (paper_id, author_id, author_position, is_corresponding)
            VALUES (:paper_id, :author_id, :position, :is_corresponding)
        """, paper_id=paper_id, **author)

    run(conn, "DELETE FROM paper_keyword WHERE paper_id = :id", id=paper_id)
    for keyword in keywords:
        run(conn, "INSERT INTO paper_keyword VALUES (:id, :keyword)",
            id=paper_id, keyword=keyword)

    # Required checks. If one fails, everything above is rolled back.
    check_no_self_review(conn, paper_id)
    check_session_assignment(conn, paper_id)
    return paper_id


@bp.route("/new", methods=["GET", "POST"])
def create_paper():
    if request.method == "POST":
        try:
            # The paper and its first version are saved in ONE transaction.
            with engine.begin() as conn:
                paper_id = save_paper(conn, request.form)
                save_new_version(conn, request.form, paper_id)
            flash("Paper created.", "success")
            return redirect(url_for("papers.show_paper", paper_id=paper_id))
        except SAVE_ERRORS as error:
            flash(error_message(error), "error")

    with engine.connect() as conn:
        choices = form_choices(conn)
    return render_template("paper_form.html", form=request.form, title="New paper",
                           is_new=True, **choices)


@bp.route("/<int:paper_id>/edit", methods=["GET", "POST"])
def edit_paper(paper_id):
    with engine.connect() as conn:
        form = load_paper(conn, paper_id)
        choices = form_choices(conn)

    if request.method == "POST":
        form = request.form
        try:
            with engine.begin() as conn:
                save_paper(conn, form, paper_id)
            flash("Paper updated.", "success")
            return redirect(url_for("papers.show_paper", paper_id=paper_id))
        except SAVE_ERRORS as error:
            flash(error_message(error), "error")

    return render_template("paper_form.html", form=form, title=f"Edit paper {paper_id}",
                           is_new=False, **choices)


@bp.route("/<int:paper_id>/delete", methods=["POST"])
def delete_paper(paper_id):
    with engine.begin() as conn:
        # Authors, keywords, versions and reviews are deleted automatically (cascade).
        deleted = run(conn, "DELETE FROM paper WHERE paper_id = :id", id=paper_id).rowcount
    if not deleted:
        abort(404)
    flash("Paper deleted, with its authorship, keywords, versions and reviews.", "success")
    return redirect(url_for("papers.list_papers"))


# ---------- Versions ----------

def read_version(form):
    return {
        "file_location": required(form, "file_location", "File location"),
        "uploaded_at": required_utc_datetime(form, "uploaded_at", "Upload time"),
        "change_note": optional(form, "change_note"),
    }


def save_new_version(conn, form, paper_id):
    run(conn, """
        INSERT INTO paper_version (paper_id, version_no, file_location, uploaded_at, change_note)
        VALUES (:paper_id, :version_no, :file_location, :uploaded_at, :change_note)
    """, paper_id=paper_id,
        version_no=required_int(form, "version_no", "Version number"),
        **read_version(form))


@bp.route("/<int:paper_id>/versions/new", methods=["GET", "POST"])
def create_version(paper_id):
    with engine.connect() as conn:
        find_paper(conn, paper_id)

    if request.method == "POST":
        form = request.form
        try:
            with engine.begin() as conn:
                save_new_version(conn, form, paper_id)
            flash("Version added.", "success")
            return redirect(url_for("papers.show_paper", paper_id=paper_id))
        except SAVE_ERRORS as error:
            flash(error_message(error), "error")
    else:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M")
        form = {"uploaded_at": now}

    return render_template("version_form.html", form=form, paper_id=paper_id,
                           title=f"New version of paper {paper_id}", is_new=True)


@bp.route("/<int:paper_id>/versions/<int:version_no>/edit", methods=["GET", "POST"])
def edit_version(paper_id, version_no):
    with engine.connect() as conn:
        version = fetch_one(conn, """
            SELECT version_no, file_location, change_note,
                   uploaded_at AT TIME ZONE 'UTC' AS uploaded_utc
            FROM paper_version
            WHERE paper_id = :paper_id AND version_no = :version_no
        """, paper_id=paper_id, version_no=version_no)
    if version is None:
        abort(404)

    if request.method == "POST":
        form = request.form
        try:
            with engine.begin() as conn:
                run(conn, """
                    UPDATE paper_version
                    SET file_location = :file_location, uploaded_at = :uploaded_at,
                        change_note = :change_note
                    WHERE paper_id = :paper_id AND version_no = :version_no
                """, paper_id=paper_id, version_no=version_no, **read_version(form))
            flash("Version updated.", "success")
            return redirect(url_for("papers.show_paper", paper_id=paper_id))
        except SAVE_ERRORS as error:
            flash(error_message(error), "error")
    else:
        form = dict(version)
        form["change_note"] = version["change_note"] or ""
        form["uploaded_at"] = version["uploaded_utc"].strftime("%Y-%m-%dT%H:%M:%S")

    return render_template("version_form.html", form=form, paper_id=paper_id,
                           title=f"Edit version {version_no} of paper {paper_id}", is_new=False)


@bp.route("/<int:paper_id>/versions/<int:version_no>/delete", methods=["POST"])
def delete_version(paper_id, version_no):
    with engine.begin() as conn:
        count = fetch_one(conn, "SELECT count(*) AS n FROM paper_version WHERE paper_id = :id",
                          id=paper_id)["n"]
        if count <= 1:
            flash("Cannot delete the only version: a paper needs at least one.", "error")
        else:
            deleted = run(conn, """
                DELETE FROM paper_version
                WHERE paper_id = :paper_id AND version_no = :version_no
            """, paper_id=paper_id, version_no=version_no).rowcount
            if not deleted:
                abort(404)
            flash("Version deleted.", "success")
    return redirect(url_for("papers.show_paper", paper_id=paper_id))
