# CSCI 341 Assignment 3 — Part 2: SQL operations through Python and SQLAlchemy

Program: `part2_queries.py`. It works on the Part 1 database (`../part1_postgresql`)
and runs tasks 1–8 in order. For every statement it prints the SQL text, the bound
parameters and the result, labelled with the task number. A copy of the output is
written to `part2_output.txt`.

## Software

- Python 3.10+
- SQLAlchemy 2.0 (`text()` with bound parameters; Core connections and transactions)
- psycopg 3 (PostgreSQL driver)
- PostgreSQL 14+ (developed for PostgreSQL 17, same as Part 1)

## Setup and run

```bash
pip install -r requirements.txt
createdb conference_assignment          # or create an empty DB in pgAdmin

# Linux / macOS
export DATABASE_URL="postgresql+psycopg://USER:PASSWORD@localhost:5432/conference_assignment"
# Windows PowerShell
$env:DATABASE_URL="postgresql+psycopg://USER:PASSWORD@localhost:5432/conference_assignment"

python part2_queries.py
```

Expected folder layout (the Part 1 scripts are found automatically):

```
part1_postgresql/   01_schema.sql, 02_seed.sql, ...
part2_sqlalchemy/   part2_queries.py, requirements.txt, README_PART2.md
```

Options:

| Option | Meaning |
|---|---|
| `--restore-only` | Run tasks 1–2 only: drop, recreate and reseed (restores the initial dataset). |
| `--skip-setup` | Skip tasks 1–2 and run tasks 3–8 on an already seeded database. |
| `--brief-scripts` | Print only the first 30 lines of each SQL script (shorter output for the video). |
| `--sql-dir PATH` | Location of the Part 1 scripts (or env `PART1_SQL_DIR`). |
| `--database-url URL` | Instead of `DATABASE_URL`. `postgres://` URLs are converted to psycopg 3. |

**Warning:** task 1 drops and recreates the 15 project tables. Do not run the full
program against the deployed Part 3 database during grading; use a local database
or `--skip-setup`.

## How each requirement is met

- **Task 1** — drops old project objects (repeatable run), then executes
  `01_schema.sql` through SQLAlchemy's `engine.raw_connection()` (the script owns its
  `BEGIN/COMMIT`). Then it lists the created tables, all PK/FK/UNIQUE/CHECK
  constraints from `pg_constraint`, and the partial unique index.
- **Task 2** — executes `02_seed.sql` the same way and prints the row count of every table.
- **Restoring the initial dataset:** `python part2_queries.py --restore-only`
  (or run `part1_postgresql/00_restore.sql` in psql/pgAdmin).
- **Tasks 3–4 (mutations)** — each runs in its own transaction: BEFORE query →
  UPDATE/DELETE with `RETURNING` → AFTER query → `ROLLBACK`.
- **Original seed for every task** — after setup the program takes a snapshot of all
  15 tables (row count + md5 checksum of the contents). Before every retrieval/view
  task and after every rollback it checks that the database still equals this
  snapshot, and stops with an error otherwise.
- **All logic in the database** — filtering, joins, aggregation, CTEs and date
  arithmetic are in SQL; Python only binds parameters and prints results.
- **No row multiplication** — 6.1 uses `COUNT(DISTINCT ...)`; 6.3 aggregates papers
  and reviews in separate CTEs; 6.2/6.4 join only `review`; 5.1 joins only the
  corresponding author (`is_corresponding = TRUE`).

## Query parameter values and expected results (original seed)

| Task | Bound parameters | Expected result |
|---|---|---|
| 3.1 | `email = arman.armanov@example.com`, `new_phone = +77773414141` | 1 row: user 1, +77010000001 → +77773414141 |
| 3.2 | `city = Astana`, `astana_days = 7`, `other_days = 3` | 3 rows: conf 1 2026-11-20→11-27, conf 2 (Almaty) 11-22→11-25, conf 3 2027-01-10→01-17 |
| 4.1 | `email = amina.aminova@example.com`, `status = withdrawn` | papers 6, 11 deleted; −4 authorships, −4 keywords, −2 versions, −2 reviews; users/tracks/conferences unchanged |
| 4.2 | `city = Astana` | sessions 2, 5 deleted; 1 (non-empty, Astana) and 4 (empty, Almaty) kept; 3 conferences kept |
| 5.1 | `status = accepted` | papers 1, 2, 7, 12 (one row each) |
| 5.2 | `pattern = %machine learning%` (ILIKE) | papers 1, 4, 7 |
| 5.3 | `paper_id = 1` | versions 4, 2, 1 (gap at 3 is allowed; 4 is current) |
| 5.4 | `conference_id = 1`, `area_label = Databases`, `min_years = 3` | reviewers 1, 6, 7, 8 |
| 6.1 | — | tracks 1: 4/5, 2: 3/4, 3: 0/0, 4: 2/3, 5: 3/4, 6: 0/0 (papers/authors) |
| 6.2 | — | 1: 2/4.50, 4: 1/4.00, 5: 1/1.00, 6: 5/3.80, 7: 4/2.50, 8: 3/2.33, 11: 0/NULL, 12: 0/NULL |
| 6.3 | — | conf 1: 7 papers, 2 accepted, avg 2.91; conf 2: 5, 2, 3.60; conf 3: 0, 0, NULL |
| 6.4 | — | average 2.00 reviews per reviewer; reviewers 6 (5), 7 (4), 8 (3) |
| 7 | `accepted`, `rejected` | conf 1: 2/1/66.67; conf 2: 2/1/66.67; conf 3: 0/0/NULL |
| 8 | — | papers 1 (session 1) and 7 (session 3); accepted papers 2 and 12 have no session and are absent |

Averages are displayed rounded to 2 decimals with `ROUND`; the computation itself
uses the full precision.
