#!/usr/bin/env python3


from __future__ import annotations

import argparse
import os
import sys
import textwrap
from datetime import date, datetime, time
from decimal import Decimal
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection, Engine, make_url

TABLES = [
    "app_user", "author", "author_research_area", "reviewer", "reviewer_expertise",
    "conference", "conference_host", "conference_reviewer", "track",
    "conference_session", "paper", "paper_keyword", "paper_author",
    "paper_version", "review",
]


PARAMS = {
    "3.1": {"email": "arman.armanov@example.com", "new_phone": "+77773414141"},
    "3.2": {"city": "Astana", "astana_days": 7, "other_days": 3},
    "4.1": {"email": "amina.aminova@example.com", "status": "withdrawn"},
    "4.2": {"city": "Astana"},
    "5.1": {"status": "accepted"},
    "5.2": {"pattern": "%machine learning%"},
    "5.3": {"paper_id": 1},
    "5.4": {"conference_id": 1, "area_label": "Databases", "min_years": 3},
    "7":   {"accepted": "accepted", "rejected": "rejected"},
}



class Tee:
    """Write everything to the console and to an output file."""

    def __init__(self, *streams):
        self.streams = streams

    def write(self, data):
        for s in self.streams:
            s.write(data)

    def flush(self):
        for s in self.streams:
            s.flush()


def banner(title: str) -> None:
    line = "=" * 78
    print(f"\n{line}\n{title}\n{line}")


def task(number: str, title: str) -> None:
    print(f"\n{'-' * 78}\nTASK {number}: {title}\n{'-' * 78}")


def note(msg: str) -> None:
    print(f"  >> {msg}")


def fmt(value) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, (datetime, date, time)):
        return value.isoformat(sep=" ") if isinstance(value, datetime) else value.isoformat()
    return str(value)


def print_table(columns, rows, max_width: int = 45) -> None:
    cells = [[fmt(v) for v in row] for row in rows]
    cells = [[c if len(c) <= max_width else c[: max_width - 3] + "..." for c in r] for r in cells]
    widths = [len(c) for c in columns]
    for r in cells:
        widths = [max(w, len(c)) for w, c in zip(widths, r)]
    sep = "+" + "+".join("-" * (w + 2) for w in widths) + "+"
    print(sep)
    print("| " + " | ".join(c.ljust(w) for c, w in zip(columns, widths)) + " |")
    print(sep)
    for r in cells:
        print("| " + " | ".join(c.ljust(w) for c, w in zip(r, widths)) + " |")
    print(sep)


def show_sql(sql: str, params: dict | None) -> None:
    print("SQL:")
    print(textwrap.indent(textwrap.dedent(sql).strip(), "    "))
    if params:
        print(f"Bound parameters: {params}")


def execute(conn: Connection, sql: str, params: dict | None = None, label: str | None = None):
    """Execute one statement with bound parameters, print SQL and result."""
    if label:
        print(f"\n[{label}]")
    show_sql(sql, params)
    result = conn.execute(text(sql), params or {})
    affected = result.rowcount   # read before fetching (RETURNING + fetch resets it to -1)
    rows = []
    print("Result:")
    if result.returns_rows:
        columns = list(result.keys())
        rows = result.fetchall()
        affected = len(rows)
        print_table(columns, rows)
        print(f"({len(rows)} row{'s' if len(rows) != 1 else ''})")
    first_word = textwrap.dedent(sql).strip().split(None, 1)[0].upper()
    if first_word in ("UPDATE", "DELETE", "INSERT"):
        print(f"Rows affected: {affected}")
    elif not result.returns_rows:
        print("OK")
    return rows, affected



def build_engine(url: str) -> Engine:
    u = make_url(url)
    
    if u.drivername in ("postgres", "postgresql"):
        u = u.set(drivername="postgresql+psycopg")
    return create_engine(u)


def find_sql_dir(cli_value: str | None) -> Path:
    here = Path(__file__).resolve().parent
    candidates = [cli_value, os.environ.get("PART1_SQL_DIR"),
                  here / "part1_postgresql", here.parent / "part1_postgresql", here / "sql"]
    for c in candidates:
        if c and (Path(c) / "01_schema.sql").is_file():
            return Path(c)
    sys.exit("ERROR: cannot find 01_schema.sql. Use --sql-dir or PART1_SQL_DIR.")


def run_sql_script(engine: Engine, path: Path, brief: bool) -> None:
    """
    Execute a complete Part 1 script (it owns its BEGIN/COMMIT) through the
    DBAPI connection that SQLAlchemy manages. The script is not split at
    semicolons; the driver receives it as one multi-statement string.
    """
    script = path.read_text(encoding="utf-8")
    lines = script.splitlines()
    print(f"Executing script {path.name} ({len(lines)} lines) via SQLAlchemy engine.raw_connection():")
    shown = lines[:30] if brief else lines
    print(textwrap.indent("\n".join(shown), "    "))
    if brief and len(lines) > 30:
        print(f"    ... ({len(lines) - 30} more lines, run without --brief-scripts to print all)")

    raw = engine.raw_connection()
    try:
        dbapi_conn = raw.driver_connection
        dbapi_conn.rollback()           
        dbapi_conn.autocommit = True     
        try:
            cur = dbapi_conn.cursor()
            if engine.dialect.driver == "psycopg":
                cur.execute(script, prepare=False)
            else:
                cur.execute(script)
            cur.close()
        finally:
            dbapi_conn.autocommit = False
    finally:
        raw.close()
    print(f"Result: script {path.name} executed successfully.")


def snapshot(engine: Engine) -> dict:
    """Row count and content checksum of every table."""
    sql = "\nUNION ALL\n".join(
        f"SELECT '{t}' AS table_name, count(*) AS row_count, "
        f"md5(coalesce(string_agg(x::text, '|' ORDER BY x::text), '')) AS checksum FROM {t} AS x"
        for t in TABLES
    )
    with engine.connect() as conn:
        return {r.table_name: (r.row_count, r.checksum) for r in conn.execute(text(sql))}


def ensure_seed_state(engine: Engine, baseline: dict) -> None:
    current = snapshot(engine)
    diff = [t for t in TABLES if current.get(t) != baseline.get(t)]
    if diff:
        raise RuntimeError(f"Database no longer matches the seed dataset; changed tables: {diff}")
    note("Seed check passed: all 15 tables have the original row counts and checksums.")


def rolled_back_demo(engine: Engine, baseline: dict, body) -> None:
    """Run a mutation demo in one transaction, then roll it back and re-verify the seed."""
    with engine.connect() as conn:
        trans = conn.begin()
        try:
            body(conn)
        finally:
            trans.rollback()
            print("\nTransaction ROLLED BACK - the seed data is restored.")
    ensure_seed_state(engine, baseline)




ROW_COUNT_SQL = "\nUNION ALL\n".join(
    f"SELECT {i} AS ord, '{t}' AS table_name, count(*) AS row_count FROM {t}"
    for i, t in enumerate(TABLES, start=1)
) + "\nORDER BY ord"


def task1_create(engine: Engine, sql_dir: Path, brief: bool) -> None:
    task("1", "Create statements (tables + required constraints)")
    with engine.begin() as conn:
        note("Removing previous project objects so the run is repeatable.")
        execute(conn, "DROP VIEW IF EXISTS accepted_paper_schedule")
        execute(conn, "DROP TABLE IF EXISTS " + ", ".join(reversed(TABLES)) + " CASCADE")

    run_sql_script(engine, sql_dir / "01_schema.sql", brief)

    with engine.connect() as conn:
        execute(conn, """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = current_schema() AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """, label="1.a Created tables")
        execute(conn, """
            SELECT conrelid::regclass::text AS table_name,
                   conname AS constraint_name,
                   CASE contype WHEN 'p' THEN 'PRIMARY KEY' WHEN 'f' THEN 'FOREIGN KEY'
                                WHEN 'u' THEN 'UNIQUE'      WHEN 'c' THEN 'CHECK' END AS type,
                   pg_get_constraintdef(oid) AS definition
            FROM pg_constraint
            WHERE connamespace = current_schema()::regnamespace
              AND contype IN ('p', 'f', 'u', 'c')
            ORDER BY array_position(CAST(:tables AS text[]), conrelid::regclass::text), contype, conname
        """, {"tables": TABLES}, label="1.b Created PK / FK / UNIQUE / CHECK constraints")
        execute(conn, """
            SELECT tablename, indexname, indexdef
            FROM pg_indexes
            WHERE schemaname = current_schema() AND indexname = 'uq_paper_one_corresponding'
        """, label="1.c Partial unique index (at most one corresponding author per paper)")


def task2_insert(engine: Engine, sql_dir: Path, brief: bool) -> None:
    task("2", "Insert statements (seed data) and row count of every table")
    run_sql_script(engine, sql_dir / "02_seed.sql", brief)
    with engine.connect() as conn:
        execute(conn, ROW_COUNT_SQL, label="2.a Row count of every table")
    note("To restore this initial dataset at any time: python part2_queries.py --restore-only")
    note("(or run part1_postgresql/00_restore.sql in psql / pgAdmin).")



def task3_1(engine: Engine, baseline: dict) -> None:
    task("3.1", "Update Arman Armanov's phone number (identified by email)")
    p = PARAMS["3.1"]
    select_sql = """
        SELECT user_id, given_name, surname, email, phone_number
        FROM app_user
        WHERE email = :email
    """

    def body(conn):
        execute(conn, select_sql, {"email": p["email"]}, label="BEFORE")
        _, n = execute(conn, """
            UPDATE app_user
            SET phone_number = :new_phone
            WHERE email = :email
            RETURNING user_id, given_name, surname, email, phone_number
        """, p, label="UPDATE")
        assert n == 1, "exactly one user must be updated"
        execute(conn, select_sql, {"email": p["email"]}, label="AFTER")

    rolled_back_demo(engine, baseline, body)


def task3_2(engine: Engine, baseline: dict) -> None:
    task("3.2", "Conditional UPDATE of review deadlines (+7 days Astana, +3 days otherwise)")
    p = PARAMS["3.2"]
    select_sql = """
        SELECT conference_id, acronym, city, review_deadline
        FROM conference
        ORDER BY conference_id
    """

    def body(conn):
        execute(conn, select_sql, label="BEFORE")
        execute(conn, """
            UPDATE conference
            SET review_deadline = review_deadline +
                CASE WHEN city = :city THEN CAST(:astana_days AS integer)
                     ELSE CAST(:other_days AS integer)
                END
            RETURNING conference_id, acronym, city, review_deadline AS new_review_deadline
        """, p, label="UPDATE (single statement, PostgreSQL date + integer arithmetic)")
        execute(conn, select_sql, label="AFTER")
        note("Both CASE branches executed: Astana conferences +7 days, others +3 days.")

    rolled_back_demo(engine, baseline, body)



TABLE_TOTALS_SQL = """
    SELECT (SELECT count(*) FROM paper)         AS papers,
           (SELECT count(*) FROM paper_author)  AS authorships,
           (SELECT count(*) FROM paper_keyword) AS keywords,
           (SELECT count(*) FROM paper_version) AS versions,
           (SELECT count(*) FROM review)        AS reviews,
           (SELECT count(*) FROM app_user)      AS users,
           (SELECT count(*) FROM track)         AS tracks,
           (SELECT count(*) FROM conference)    AS conferences
"""


def task4_1(engine: Engine, baseline: dict) -> None:
    task("4.1", "Delete withdrawn papers whose corresponding author is Amina Aminova")
    p = PARAMS["4.1"]
    withdrawn_sql = """
        SELECT p.paper_id, p.title, p.status, u.email AS corresponding_email,
               (SELECT count(*) FROM paper_author  x WHERE x.paper_id = p.paper_id) AS authors,
               (SELECT count(*) FROM paper_keyword x WHERE x.paper_id = p.paper_id) AS keywords,
               (SELECT count(*) FROM paper_version x WHERE x.paper_id = p.paper_id) AS versions,
               (SELECT count(*) FROM review        x WHERE x.paper_id = p.paper_id) AS reviews
        FROM paper p
        LEFT JOIN paper_author pa ON pa.paper_id = p.paper_id AND pa.is_corresponding
        LEFT JOIN app_user u ON u.user_id = pa.author_id
        WHERE p.status = :status
        ORDER BY p.paper_id
    """

    def body(conn):
        execute(conn, withdrawn_sql, {"status": p["status"]}, label="BEFORE: withdrawn papers and their dependent rows")
        execute(conn, TABLE_TOTALS_SQL, label="BEFORE: table totals")
        execute(conn, """
            DELETE FROM paper p
            WHERE p.status = :status
              AND EXISTS (SELECT 1
                          FROM paper_author pa
                          JOIN app_user u ON u.user_id = pa.author_id
                          WHERE pa.paper_id = p.paper_id
                            AND pa.is_corresponding
                            AND u.email = :email)
            RETURNING p.paper_id, p.title
        """, p, label="DELETE (paper_author, paper_keyword, paper_version, review removed by ON DELETE CASCADE)")
        execute(conn, withdrawn_sql, {"status": p["status"]}, label="AFTER: withdrawn papers")
        execute(conn, TABLE_TOTALS_SQL, label="AFTER: table totals (users, tracks, conferences unchanged)")

    rolled_back_demo(engine, baseline, body)


def task4_2(engine: Engine, baseline: dict) -> None:
    task("4.2", "Delete empty sessions of conferences held in Astana")
    p = PARAMS["4.2"]
    sessions_sql = """
        SELECT s.session_id, s.title, c.conference_id, c.city,
               count(p.paper_id) AS assigned_papers
        FROM conference_session s
        JOIN conference c ON c.conference_id = s.conference_id
        LEFT JOIN paper p ON p.session_id = s.session_id
        GROUP BY s.session_id, s.title, c.conference_id, c.city
        ORDER BY s.session_id
    """
    conf_sql = "SELECT count(*) AS conferences FROM conference"

    def body(conn):
        execute(conn, sessions_sql, label="BEFORE: sessions")
        execute(conn, conf_sql, label="BEFORE: conferences")
        execute(conn, """
            DELETE FROM conference_session s
            USING conference c
            WHERE c.conference_id = s.conference_id
              AND c.city = :city
              AND NOT EXISTS (SELECT 1 FROM paper p WHERE p.session_id = s.session_id)
            RETURNING s.session_id, s.title, c.city
        """, p, label="DELETE")
        execute(conn, sessions_sql, label="AFTER: sessions (non-empty and non-Astana sessions kept)")
        execute(conn, conf_sql, label="AFTER: conferences (all kept)")

    rolled_back_demo(engine, baseline, body)



def task5(engine: Engine, baseline: dict) -> None:
    task("5.1", "Accepted papers with corresponding author, track and conference")
    ensure_seed_state(engine, baseline)
    with engine.connect() as conn:
        execute(conn, """
            SELECT p.paper_id, p.title,
                   u.given_name || ' ' || u.surname AS corresponding_author,
                   u.email AS corresponding_email,
                   t.name AS track_name,
                   c.conference_id, c.acronym
            FROM paper p
            JOIN track t       ON t.track_id = p.track_id
            JOIN conference c  ON c.conference_id = t.conference_id
            LEFT JOIN paper_author pa ON pa.paper_id = p.paper_id AND pa.is_corresponding
            LEFT JOIN app_user u      ON u.user_id = pa.author_id
            WHERE p.status = :status
            ORDER BY p.paper_id
        """, PARAMS["5.1"])

    task("5.2", "Papers whose abstract contains 'machine learning' (case-insensitive)")
    ensure_seed_state(engine, baseline)
    with engine.connect() as conn:
        execute(conn, """
            SELECT paper_id, title
            FROM paper
            WHERE abstract ILIKE :pattern
            ORDER BY paper_id
        """, PARAMS["5.2"])

    task("5.3", "All versions of a selected paper, highest version first")
    ensure_seed_state(engine, baseline)
    with engine.connect() as conn:
        execute(conn, """
            SELECT version_no, file_location, uploaded_at
            FROM paper_version
            WHERE paper_id = :paper_id
            ORDER BY version_no DESC
        """, PARAMS["5.3"])

    task("5.4", "Pool reviewers with 'Databases' expertise and >= 3 years experience")
    ensure_seed_state(engine, baseline)
    with engine.connect() as conn:
        execute(conn, """
            SELECT u.user_id AS reviewer_id,
                   u.given_name || ' ' || u.surname AS full_name,
                   u.email, r.years_experience
            FROM conference_reviewer cr
            JOIN reviewer r ON r.reviewer_id = cr.reviewer_id
            JOIN app_user u ON u.user_id = r.reviewer_id
            WHERE cr.conference_id = :conference_id
              AND r.years_experience >= :min_years
              AND EXISTS (SELECT 1 FROM reviewer_expertise e
                          WHERE e.reviewer_id = r.reviewer_id
                            AND e.area_label = :area_label)
            ORDER BY u.user_id
        """, PARAMS["5.4"])



def task6(engine: Engine, baseline: dict) -> None:
    task("6.1", "Per track: distinct papers and distinct authors (tracks with no papers included)")
    ensure_seed_state(engine, baseline)
    with engine.connect() as conn:
        execute(conn, """
            SELECT t.track_id, t.name AS track_name, t.conference_id,
                   count(DISTINCT p.paper_id)   AS paper_count,
                   count(DISTINCT pa.author_id) AS author_count
            FROM track t
            LEFT JOIN paper p         ON p.track_id = t.track_id
            LEFT JOIN paper_author pa ON pa.paper_id = p.paper_id
            GROUP BY t.track_id, t.name, t.conference_id
            ORDER BY t.track_id
        """)

    task("6.2", "Per reviewer: completed reviews and average overall score")
    ensure_seed_state(engine, baseline)
    with engine.connect() as conn:
        execute(conn, """
            SELECT r.reviewer_id,
                   u.given_name || ' ' || u.surname AS full_name,
                   count(v.review_id)                AS review_count,
                   round(avg(v.overall_score), 2)    AS avg_overall_score
            FROM reviewer r
            JOIN app_user u     ON u.user_id = r.reviewer_id
            LEFT JOIN review v  ON v.reviewer_id = r.reviewer_id
            GROUP BY r.reviewer_id, u.given_name, u.surname
            ORDER BY r.reviewer_id
        """)

    task("6.3", "Per conference: total papers, accepted papers, average review score")
    ensure_seed_state(engine, baseline)
    with engine.connect() as conn:
        execute(conn, """
            WITH paper_stats AS (
                SELECT t.conference_id,
                       count(*)                                     AS total_papers,
                       count(*) FILTER (WHERE p.status = 'accepted') AS accepted_papers
                FROM paper p
                JOIN track t ON t.track_id = p.track_id
                GROUP BY t.conference_id
            ),
            review_stats AS (
                SELECT t.conference_id,
                       count(*)              AS review_count,
                       avg(v.overall_score)  AS avg_score
                FROM review v
                JOIN paper p ON p.paper_id = v.paper_id
                JOIN track t ON t.track_id = p.track_id
                GROUP BY t.conference_id
            )
            SELECT c.conference_id, c.acronym,
                   coalesce(ps.total_papers, 0)    AS total_papers,
                   coalesce(ps.accepted_papers, 0) AS accepted_papers,
                   coalesce(rs.review_count, 0)    AS review_count,
                   round(rs.avg_score, 2)          AS avg_overall_score
            FROM conference c
            LEFT JOIN paper_stats  ps ON ps.conference_id = c.conference_id
            LEFT JOIN review_stats rs ON rs.conference_id = c.conference_id
            ORDER BY c.conference_id
        """)
    note("Papers and reviews are aggregated in separate CTEs, so multiple reviews "
         "per paper cannot inflate the paper counts.")

    task("6.4", "Reviewers with more completed reviews than the average per reviewer")
    ensure_seed_state(engine, baseline)
    with engine.connect() as conn:
        execute(conn, """
            WITH review_counts AS (
                SELECT r.reviewer_id,
                       u.given_name || ' ' || u.surname AS full_name,
                       count(v.review_id) AS review_count
                FROM reviewer r
                JOIN app_user u    ON u.user_id = r.reviewer_id
                LEFT JOIN review v ON v.reviewer_id = r.reviewer_id
                GROUP BY r.reviewer_id, u.given_name, u.surname
            ),
            overall AS (
                SELECT avg(review_count) AS avg_reviews_per_reviewer
                FROM review_counts               -- includes reviewers with 0 reviews
            )
            SELECT rc.reviewer_id, rc.full_name, rc.review_count,
                   round(o.avg_reviews_per_reviewer, 2) AS avg_reviews_per_reviewer
            FROM review_counts rc
            CROSS JOIN overall o
            WHERE rc.review_count > o.avg_reviews_per_reviewer
            ORDER BY rc.review_count DESC, rc.reviewer_id
        """)


def task7(engine: Engine, baseline: dict) -> None:
    task("7", "Acceptance rate per conference (derived attribute)")
    ensure_seed_state(engine, baseline)
    with engine.connect() as conn:
        execute(conn, """
            WITH decided AS (
                SELECT c.conference_id, c.acronym,
                       count(p.paper_id) FILTER (WHERE p.status = :accepted) AS accepted_count,
                       count(p.paper_id) FILTER (WHERE p.status = :rejected) AS rejected_count
                FROM conference c
                LEFT JOIN track t ON t.conference_id = c.conference_id
                LEFT JOIN paper p ON p.track_id = t.track_id
                GROUP BY c.conference_id, c.acronym
            )
            SELECT conference_id, acronym, accepted_count, rejected_count,
                   round(100.0 * accepted_count
                         / NULLIF(accepted_count + rejected_count, 0), 2) AS acceptance_rate_pct
            FROM decided
            ORDER BY conference_id
        """, PARAMS["7"])
    note("Submitted, under review and withdrawn papers are excluded from the denominator; "
         "NULLIF returns NULL when there are no decided papers.")



VIEW_SQL = """
    CREATE OR REPLACE VIEW accepted_paper_schedule AS
    SELECT p.paper_id,
           p.title                              AS paper_title,
           c.conference_id,
           c.acronym                            AS conference_acronym,
           t.name                               AS track_name,
           s.session_id,
           s.title                              AS session_title,
           s.session_date,
           s.start_time,
           s.end_time,
           s.room_label,
           chair.given_name || ' ' || chair.surname AS chair_full_name,
           ca.given_name || ' ' || ca.surname       AS corresponding_author_full_name,
           ca.email                                 AS corresponding_author_email
    FROM paper p
    JOIN track t              ON t.track_id = p.track_id
    JOIN conference c         ON c.conference_id = t.conference_id
    JOIN conference_session s ON s.session_id = p.session_id
                             AND s.conference_id = c.conference_id
    JOIN app_user chair       ON chair.user_id = s.chair_id
    JOIN paper_author pa      ON pa.paper_id = p.paper_id AND pa.is_corresponding
    JOIN app_user ca          ON ca.user_id = pa.author_id
    WHERE p.status = 'accepted'
"""


def task8(engine: Engine, baseline: dict) -> None:
    task("8", "View accepted_paper_schedule")
    ensure_seed_state(engine, baseline)
    with engine.begin() as conn:
        execute(conn, VIEW_SQL, label="8.a Create the view")
    with engine.connect() as conn:
        execute(conn, """
            SELECT table_name, table_type
            FROM information_schema.tables
            WHERE table_schema = current_schema() AND table_name = 'accepted_paper_schedule'
        """, label="8.b The object is a VIEW (no stored copy of the result)")
        execute(conn, """
            SELECT *
            FROM accepted_paper_schedule
            ORDER BY conference_id, session_date, start_time, session_id, paper_id
        """, label="8.c Query the view")
        execute(conn, """
            SELECT p.paper_id, p.title, p.session_id
            FROM paper p
            WHERE p.status = :status
              AND p.paper_id NOT IN (SELECT paper_id FROM accepted_paper_schedule)
            ORDER BY p.paper_id
        """, {"status": "accepted"}, label="8.d Accepted papers NOT in the view (no session)")



def main() -> None:
    ap = argparse.ArgumentParser(description="CSCI 341 A3 Part 2 (SQLAlchemy)")
    ap.add_argument("--database-url", default=os.environ.get("DATABASE_URL"),
                    help="SQLAlchemy URL (default: $DATABASE_URL)")
    ap.add_argument("--sql-dir", help="folder with Part 1 scripts (default: ../part1_postgresql)")
    ap.add_argument("--skip-setup", action="store_true",
                    help="skip tasks 1-2; use the already seeded database")
    ap.add_argument("--restore-only", action="store_true",
                    help="run only tasks 1-2 (recreate and reseed) and exit")
    ap.add_argument("--brief-scripts", action="store_true",
                    help="print only the first 30 lines of each SQL script")
    ap.add_argument("--output", default="part2_output.txt", help="file for a copy of the output")
    args = ap.parse_args()

    if not args.database_url:
        sys.exit("ERROR: set DATABASE_URL or pass --database-url.")

    out_file = open(args.output, "w", encoding="utf-8")
    sys.stdout = Tee(sys.__stdout__, out_file)
    try:
        engine = build_engine(args.database_url)
        with engine.connect() as conn:
            version = conn.execute(text("SELECT version()")).scalar_one()
        import sqlalchemy
        banner("CSCI 341 Assignment 3 - Part 2: SQL operations through Python and SQLAlchemy")
        print(f"Python     : {sys.version.split()[0]}")
        print(f"SQLAlchemy : {sqlalchemy.__version__}")
        print(f"Driver     : {engine.dialect.driver}")
        print(f"Database   : {version}")
        print(f"Target     : {engine.url.render_as_string(hide_password=True)}")

        if not args.skip_setup:
            sql_dir = find_sql_dir(args.sql_dir)
            banner("PART 2 / TASKS 1-2: CREATE AND INSERT")
            task1_create(engine, sql_dir, args.brief_scripts)
            task2_insert(engine, sql_dir, args.brief_scripts)
            if args.restore_only:
                print("\nSeed dataset restored.")
                return

        baseline = snapshot(engine)
        note("Baseline snapshot of the seed dataset taken (row counts + checksums of all tables).")

        banner("TASK 3: UPDATE STATEMENTS")
        task3_1(engine, baseline)
        task3_2(engine, baseline)

        banner("TASK 4: DELETE STATEMENTS")
        task4_1(engine, baseline)
        task4_2(engine, baseline)

        banner("TASK 5: SIMPLE QUERIES")
        task5(engine, baseline)

        banner("TASK 6: COMPLEX QUERIES")
        task6(engine, baseline)

        banner("TASK 7: QUERY WITH A DERIVED ATTRIBUTE")
        task7(engine, baseline)

        banner("TASK 8: VIEW OPERATION")
        task8(engine, baseline)

        banner("ALL TASKS COMPLETED")
        ensure_seed_state(engine, baseline)
        print(f"A copy of this output was written to {args.output}")
    finally:
        sys.stdout = sys.__stdout__
        out_file.close()


if __name__ == "__main__":
    main()
