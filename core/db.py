import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "db.sqlite3"
DB_PATH.parent.mkdir(exist_ok=True)

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id TEXT PRIMARY KEY,
            slug TEXT UNIQUE,
            path TEXT,
            created_at TEXT
        )
    """)
    conn.commit()
    conn.close()