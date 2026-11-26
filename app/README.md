# Part 3: Web application

Flask + SQLAlchemy (plain SQL with bound parameters) + HTML templates.
It uses the Part 1 PostgreSQL database.

## Run locally

Run these from the project root (the folder that contains `app/`).

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

createdb conference_assignment
psql -d conference_assignment -v ON_ERROR_STOP=1 -f part1_postgresql/00_restore.sql

export DATABASE_URL="postgresql://USER:PASSWORD@localhost:5432/conference_assignment"
flask --app app run --debug
```

Open http://127.0.0.1:5000.

`00_restore.sql` deletes and rebuilds the project tables.

On a server, start the app with `gunicorn "app:create_app()"` and set
`DATABASE_URL` and `SECRET_KEY` (any long random text).

## Files

| File | What it does |
|---|---|
| `__init__.py` | Creates the app |
| `db.py` | Database connection and query helpers |
| `helpers.py` | Reads form fields; error messages |
| `checks.py` | The two required application checks |
| `users.py` | Users, author and reviewer profiles |
| `papers.py` | Papers, authors, keywords, versions |
| `reviews.py` | Reviews |
| `sessions.py` | Sessions |
| `templates/` | HTML pages |

## Required checks (`checks.py`)

Each save runs in one transaction. The change is written first, then checked.
If a check fails, the whole change is rolled back.

1. **No self-review:** checked when a review is created or edited, and when a
   paper's authors are saved.
2. **Valid session assignment:** a scheduled paper must be accepted, and its
   track and session must be in the same conference. Checked when a paper is
   saved and when a session is edited. Invalid changes are rejected. To change a
   scheduled paper to another status, also choose "No session" in the same form.

Conferences and tracks are read-only in the app.

## Optional business rules

Enforced by the app:

- A user is an author, a reviewer, or both.
- An author has at least one research area; a reviewer has at least one expertise area.
- A paper has at least one author, keyword and version.
- A paper has exactly one corresponding author.

Enforced by the database: session chairs and track coordinators are in their
conference's reviewer pool.

Not enforced: a session date lies within the conference dates.

## Deleting

| Delete | Result |
|---|---|
| Paper | Its authorship, keywords, versions and reviews are deleted |
| Session | Its papers are kept without a session |
| Review | Only the review is deleted |
| User | Rejected if the user is still referenced; otherwise the profiles are deleted too |

## Rejection demos (original sample data)

| Try this | Expected |
|---|---|
| New review: paper 1, reviewer 1 | Rejected: self-review |
| Edit paper 12: add author 4 | Rejected: self-review |
| Edit paper 2: choose session 3 | Rejected: different conference |
| Edit paper 4: choose session 1 | Rejected: not accepted |
| Edit paper 1: status `rejected` | Rejected: not accepted |
| Edit paper 1: track in AICON26, "Applied Learning" | Rejected: different conference |
| Edit session 1: conference AICON26 | Rejected: different conference |

Valid examples: a new review by reviewer 11 for paper 2; assigning paper 2 to session 2.
