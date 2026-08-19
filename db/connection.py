import sqlite3
from pathlib import Path

# Path.resolve() makes this independent of the working directory the app is
# launched from (e.g. running `reflex run` from the repo root vs. running a
# script from inside db/ during testing both resolve correctly).
DB_PATH = (Path(__file__).parent.parent / "data" / "budget.db").resolve()
SCHEMA_PATH = (Path(__file__).parent / "schema.sql").resolve()


def get_connection():
    """Returns a SQLite connection with foreign keys enabled and Row access by column name.
    Raises sqlite3.Error if the connection cannot be established (e.g. permissions issue)."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn
    except sqlite3.Error as e:
        raise RuntimeError(f"Failed to connect to database at {DB_PATH}: {e}") from e


def init_db():
    """Creates tables if they don't exist. Safe to call every app startup."""
    conn = get_connection()
    with open(SCHEMA_PATH, "r") as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()


def ensure_user(user_id: str):
    """Creates a user row if it doesn't already exist. Called on login / app start."""
    conn = get_connection()
    conn.execute(
        "INSERT OR IGNORE INTO users (id) VALUES (?)",
        (user_id,),
    )
    conn.commit()
    conn.close()