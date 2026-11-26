"""Database connection and small query helpers."""

import os

from sqlalchemy import create_engine, text


def database_url():
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("Please set the DATABASE_URL environment variable.")

    # Hosting sites give "postgresql://...". We add the name of our driver.
    for prefix in ("postgresql://", "postgres://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    return url


# pool_pre_ping replaces connections that the server closed while we were idle.
engine = create_engine(database_url(), pool_pre_ping=True)


# In all helpers, values are passed separately from the SQL (bound parameters).
# This protects the app from SQL injection.

def run(conn, sql, **params):
    return conn.execute(text(sql), params)


def fetch_all(conn, sql, **params):
    return run(conn, sql, **params).mappings().all()


def fetch_one(conn, sql, **params):
    """Return the first row, or None if there is no row."""
    return run(conn, sql, **params).mappings().first()
