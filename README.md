# Research Conference and Paper Review Management System

CSCI 341, Assignment 3. PostgreSQL database, SQL operations in Python with
SQLAlchemy, and a Flask web application.

## Project layout

| Path | Contents |
|---|---|
| `assignment3_final.sql` | `pg_dump` export: schema, constraints, indexes, sample data, view |
| `part1_postgresql/` | Part 1 SQL scripts and checks |
| `part2_queries.py` | Part 2: all numbered SQL operations |
| `app/` | Part 3: web application |
| `requirements.txt` | Python dependencies |

The project has no triggers.

## Software versions

| Software | Version used in testing |
|---|---|
| PostgreSQL, `psql`, `pg_dump` | 16.15 |
| Python | 3.14 |
| SQLAlchemy | 2.0.58 |
| psycopg | 3.3.9 |
| Flask | 3.1.3 |
| gunicorn (server for deployment) | 27.0.1 |

## Setup

Run all commands from the project root, with a PostgreSQL server running.

```bash
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
python -m pip install -r requirements.txt
```

## Database restoration

Restore the export into a **new, empty** database with `psql`:

```bash
createdb conference_assignment
psql -d conference_assignment -v ON_ERROR_STOP=1 -f assignment3_final.sql
```

Use a recent version of `psql`: the export contains `\restrict` commands, which
pgAdmin's Query Tool and older `psql` versions do not understand.

To reset an existing project database to the original data, run the script below.
**It deletes and rebuilds the project tables and the view.** It also works in pgAdmin.

```bash
psql -d conference_assignment -v ON_ERROR_STOP=1 -f part1_postgresql/00_restore.sql
```

Optional checks (run on the original data):

```bash
psql -d conference_assignment -v ON_ERROR_STOP=1 -f part1_postgresql/04_verify.sql
psql -d conference_assignment -v ON_ERROR_STOP=1 -f part1_postgresql/05_constraint_tests.sql
```

`05_constraint_tests.sql` rolls back all its changes.

If your database needs a user name or password, add it to the commands and to the
URL below: `postgresql://USER:PASSWORD@localhost:5432/conference_assignment`.
Do not save real passwords in the project files.

## Running the Part 2 queries

```bash
export DATABASE_URL="postgresql://localhost:5432/conference_assignment"
python part2_queries.py
```

The program prints each task number, the SQL, the bound parameters and the result,
and saves a copy to `part2_output.txt`.

**Warning:** a full run drops and recreates the project tables. Never run it, or
`--restore-only`, on the deployed database.

| Option | Meaning |
|---|---|
| (none) | Run tasks 1 to 8 |
| `--restore-only` | Run tasks 1 and 2 only: recreate and fill the database |
| `--skip-setup` | Run tasks 3 to 8 on a database that has the original data |
| `--brief-scripts` | Print only the start of each SQL script |

- Tasks 1 and 2 run `01_schema.sql` and `02_seed.sql` through SQLAlchemy.
- Updates and deletions (tasks 3 and 4) show the data before and after, then roll back.
- The program checks that the original data is unchanged after each rollback and
  before each query.
- Task 8 creates the view `accepted_paper_schedule`. It stores no copy of the result.

## Running the web application

```bash
export DATABASE_URL="postgresql://localhost:5432/conference_assignment"
python -m flask --app app run --port 5001
```

Open http://127.0.0.1:5001. The app needs no login.

On a server, set `DATABASE_URL` and `SECRET_KEY` (any long random text) and start
the app with `gunicorn "app:create_app()"`.

The app has full create, read, update and delete for **users, papers, reviews and
sessions**. Author and reviewer profiles are managed on the user form. Authors and
keywords are managed on the paper form, and versions on the paper's page.
Conferences, tracks, reviewer pools and conference hosts come from the seed data;
the app does not edit them.

## Schema and keys

PK = primary key, FK = foreign key, UQ = unique. All columns are `NOT NULL` except
`author.orcid`, `paper.session_id`, `paper_version.change_note` and
`review.confidential_comments`.

| Table | Primary key | Foreign keys and unique constraints |
|---|---|---|
| `app_user` | `user_id` | UQ `email` |
| `author` | `author_id` | FK to `app_user` |
| `author_research_area` | `author_id, area_label` | FK to `author` |
| `reviewer` | `reviewer_id` | FK to `app_user` |
| `reviewer_expertise` | `reviewer_id, area_label` | FK to `reviewer` |
| `conference` | `conference_id` | |
| `conference_host` | `conference_id, host_name` | FK to `conference` |
| `conference_reviewer` | `conference_id, reviewer_id` | FKs to `conference`, `reviewer` |
| `track` | `track_id` | FKs to `conference`, `reviewer` (`coordinator_id`); `(conference_id, coordinator_id)` to `conference_reviewer` |
| `conference_session` | `session_id` | FKs to `conference`, `reviewer` (`chair_id`); `(conference_id, chair_id)` to `conference_reviewer` |
| `paper` | `paper_id` | FKs to `track`, `conference_session` (`session_id`, optional) |
| `paper_keyword` | `paper_id, keyword` | FK to `paper` |
| `paper_author` | `paper_id, author_id` | FKs to `paper`, `author`; UQ `(paper_id, author_position)`; at most one corresponding author per paper (partial unique index) |
| `paper_version` | `paper_id, version_no` | FK to `paper` |
| `review` | `review_id` | FKs to `paper`, `reviewer`; UQ `(paper_id, reviewer_id)` |

`CHECK` constraints:

- Paper status is `submitted`, `under review`, `accepted`, `rejected` or `withdrawn`.
- Review score is 1 to 5; recommendation is `accept` or `reject`.
- Comments for authors are not blank.
- Author position and version number are positive.
- Reviewing experience is not negative.
- A conference does not end before it starts.
- A session ends after it starts.

### Deletion actions

| Deleted record | Effect |
|---|---|
| Paper | Cascades to its authorship, keywords, versions and reviews |
| Session | Its papers are kept; their `session_id` becomes `NULL` |
| User | Cascades to author and reviewer profiles; blocked if a profile is still referenced |
| Author or reviewer profile | Cascades to its area labels; blocked by other references |
| Conference | Cascades to hosts and pool memberships; blocked while it has tracks or sessions |
| Pool membership | Blocked while that reviewer coordinates a track or chairs a session there |
| Track | Blocked while it has papers |

Foreign keys are never disabled.

## Required application checks

Both are in `app/checks.py`. The app saves a change and runs the check in the same
transaction. If the check fails, the whole change is rolled back and an error is shown.
These checks apply to changes made through the web app; direct SQL is not covered.

1. **No self-reviews.** Checked when a review is created or edited, and when a
   paper's authors are saved.
2. **Valid session assignments.** A scheduled paper must be accepted, and its track
   and session must belong to the same conference. Checked when a paper is saved and
   when a session is edited. Invalid changes are rejected. To give a scheduled paper
   another status, also choose "No session" in the same form. The app cannot edit a
   track's conference.

### Rejection examples (original data)

| Action in the app | Result |
|---|---|
| New review: paper 1, reviewer 1 | Rejected: self-review |
| Edit paper 12: add author 4 | Rejected: self-review |
| Edit paper 2: choose session 3 | Rejected: different conferences |
| Edit paper 4: choose session 1 | Rejected: paper not accepted |
| Edit paper 1: status `rejected` | Rejected: paper not accepted |
| Edit paper 1: track "AICON26: Applied Learning" | Rejected: different conferences |
| Edit session 1: conference AICON26 | Rejected: different conferences |

Valid examples: reviewer 11 reviews paper 2; paper 2 is assigned to session 2.

## Optional business rules

All rules below hold in the sample data.

| Rule | Enforced by |
|---|---|
| A user is an author, a reviewer, or both | App |
| An author has at least one research area | App |
| A reviewer has at least one expertise area | App |
| A paper has at least one author, keyword and version | App |
| A paper has exactly one corresponding author | App; database enforces "at most one" |
| An author appears once per paper, at a unique positive position | Database |
| One completed review per reviewer and paper | Database |
| A paper has at most one session | Database |
| A paper has one track; a track or session has one conference | Database |
| A track has one coordinator; a session has one chair | Database |
| Coordinators and chairs are in the conference's reviewer pool | Database |
| A user has one affiliation | Database |
| A conference has at least one host, track and pool reviewer | Not enforced (seed data only) |
| A session's date is within its conference's dates | Not enforced (seed data only) |

## Design assumptions and changes from Assignment 1

- `USER` is named `app_user` and `SESSION` is named `conference_session`, to avoid
  confusion with SQL terms.
- The authorship relationship is the table `paper_author`, with position and
  corresponding-author flag. The reviewer pool is `conference_reviewer`.
- Research areas, expertise, hosts and keywords are stored in separate tables, not
  as comma-separated lists. They are attributes, not new domain entities.
- A track has one research area. Affiliation and room are single text values.
- Versions are identified by paper and version number. Gaps are allowed; the highest
  number is the current version.
- Only completed reviews are stored. There are no file uploads; each version stores
  a fictional file location.
- Session times are local conference times. Version upload times include a time
  zone; the web app shows and reads them as UTC.
- The database treats emails as case-sensitive. The web app saves them in lowercase.
- Conference acronyms and ORCIDs are not required to be unique.
- Review scores do not determine the recommendation or the paper's status.
- Reviewers do not have to be in a conference's pool to review its papers.
- All sample names, institutions and content are fictional.

## Query parameter values

Results refer to the original sample data.

| Task | Parameters | Expected result |
|---|---|---|
| 3.1 | `email = arman.armanov@example.com`, `new_phone = +77773414141` | User 1's phone changes |
| 3.2 | `city = Astana`, `astana_days = 7`, `other_days = 3` | Deadlines: conference 1 to 2026-11-27, 2 to 2026-11-25, 3 to 2027-01-17 |
| 4.1 | `email = amina.aminova@example.com`, `status = withdrawn` | Papers 6 and 11 and their dependent rows are deleted |
| 4.2 | `city = Astana` | Sessions 2 and 5 are deleted |
| 5.1 | `status = accepted` | Papers 1, 2, 7, 12 |
| 5.2 | `pattern = %machine learning%` | Papers 1, 4, 7 |
| 5.3 | `paper_id = 1` | Versions 4, 2, 1 |
| 5.4 | `conference_id = 1`, `area_label = Databases`, `min_years = 3` | Reviewers 1, 6, 7, 8 |
| 6.1 | none | Papers/authors per track 1 to 6: 4/5, 3/4, 0/0, 2/3, 3/4, 0/0 |
| 6.2 | none | All 8 reviewers; reviewers 11 and 12 have 0 reviews and a `NULL` average |
| 6.3 | none | Papers/accepted/average: conference 1: 7/2/2.91; 2: 5/2/3.60; 3: 0/0/`NULL` |
| 6.4 | none | Average is 2.00; reviewers 6, 7, 8 are above it |
| 7 | `accepted = accepted`, `rejected = rejected` | Conferences 1 and 2: 66.67%; conference 3: `NULL` |
| 8 | none | The view returns papers 1 and 7 |
