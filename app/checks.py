"""The two rules that the application (not the database) must enforce.

How they are used: first save the change, then call the check inside the SAME
transaction. If the check raises FormError, the whole change is rolled back.
"""

from .db import fetch_one
from .helpers import FormError


def check_no_self_review(conn, paper_id):
    """Nobody may review a paper that they wrote."""
    problem = fetch_one(conn, """
        SELECT u.given_name, u.surname
        FROM review r
        JOIN paper_author pa ON pa.paper_id = r.paper_id
                            AND pa.author_id = r.reviewer_id
        JOIN app_user u      ON u.user_id = r.reviewer_id
        WHERE r.paper_id = :paper_id
    """, paper_id=paper_id)

    if problem:
        name = f"{problem['given_name']} {problem['surname']}"
        raise FormError(f"Self-review is not allowed: {name} would be both an author "
                        f"and a reviewer of paper {paper_id}.")


def check_session_assignment(conn, paper_id):
    """A scheduled paper must be accepted and belong to the session's conference."""
    paper = fetch_one(conn, """
        SELECT p.status,
               t.conference_id AS track_conference,
               s.conference_id AS session_conference
        FROM paper p
        JOIN track t              ON t.track_id = p.track_id
        JOIN conference_session s ON s.session_id = p.session_id
        WHERE p.paper_id = :paper_id
    """, paper_id=paper_id)

    if paper is None:  # the paper has no session, so there is nothing to check
        return
    if paper["status"] != "accepted":
        raise FormError(f"Invalid session assignment: paper {paper_id} must be accepted "
                        f"to be in a session (its status is '{paper['status']}'). "
                        f"Remove it from the session first.")
    if paper["track_conference"] != paper["session_conference"]:
        raise FormError(f"Invalid session assignment: the track and the session of "
                        f"paper {paper_id} belong to different conferences.")
