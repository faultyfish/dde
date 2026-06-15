"""
db/migrate.py
Run this once to create tables in Neon Postgres.
Usage: python db/migrate.py
"""
import os
import sys
from pathlib import Path
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def migrate():
    db_url = os.getenv("NEON_DATABASE_URL")
    if not db_url:
        print("❌ NEON_DATABASE_URL not set in .env")
        sys.exit(1)

    schema_path = Path(__file__).parent / "schema.sql"
    schema_sql = schema_path.read_text()

    print("🔗 Connecting to Neon Postgres...")
    conn = psycopg2.connect(db_url)
    conn.autocommit = True
    cur = conn.cursor()

    print("🛠  Running schema migrations...")
    cur.execute(schema_sql)

    print("✅ Migration complete.")
    cur.close()
    conn.close()

if __name__ == "__main__":
    migrate()
