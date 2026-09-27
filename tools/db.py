"""
db.py
Shared Postgres connection pool for all Lifespring tool modules.

Reads connection settings from environment variables (see .env.example).
Every tool module imports `get_conn` / `put_conn` from here instead of
opening its own connection, so we don't exhaust Postgres connections
when the agent calls several tools in a row.
"""

import os
from contextlib import contextmanager
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()
_DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432"),
    "dbname": os.getenv("DB_NAME", "lifespring_healthcare"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", ""),
}

_MIN_CONN = int(os.getenv("DB_POOL_MIN", "1"))
_MAX_CONN = int(os.getenv("DB_POOL_MAX", "5"))

_pool = pool.ThreadedConnectionPool(_MIN_CONN, _MAX_CONN, **_DB_CONFIG)


@contextmanager
def get_cursor(commit: bool = False):
    """
    Context manager that yields a RealDictCursor (rows come back as dicts,
    so tool functions can do dict(row) / row["col"] directly).

    Usage:
        with get_cursor() as cur:
            cur.execute("SELECT ...", (param,))
            rows = cur.fetchall()

        with get_cursor(commit=True) as cur:
            cur.execute("INSERT ...", (...))
    """
    conn = _pool.getconn()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        yield cur
        if commit:
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        _pool.putconn(conn)


def close_pool():
    """Call on application shutdown."""
    _pool.closeall()