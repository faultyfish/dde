"""
api/db.py
Neon Postgres connection (context manager).
"""
import os
from contextlib import contextmanager
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()


@contextmanager
def get_conn():
    conn = psycopg2.connect(
        os.environ["NEON_DATABASE_URL"],
        cursor_factory=psycopg2.extras.RealDictCursor
    )
    try:
        yield conn
    finally:
        conn.close()
