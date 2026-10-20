"""Tiny SQLite repository. Learn these 3 functions before touching JWT."""
import os
import sqlite3
from pathlib import Path

from dotenv import load_dotenv

# Load local settings before reading the database path.
# Existing environment variables keep precedence.
load_dotenv(Path(__file__).with_name(".env"))

DB_PATH = Path(
    os.getenv(
        "JWT_DEMO_DB_PATH",
        Path(__file__).with_name("users.db"),
    )
)


def init_db():
    """Create the users table once. Called when FastAPI starts."""
    connection = sqlite3.connect(DB_PATH)
    try:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password_hash TEXT NOT NULL,
                full_name TEXT
            )
            """
        )
        connection.commit()
    finally:
        connection.close()


def get_user(username: str) -> dict | None:
    """Return one user as a dictionary, or None if not found."""
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    try:
        row = connection.execute(
            "SELECT username, password_hash, full_name FROM users WHERE username = ?",
            (username,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        connection.close()


def create_user(username: str, password_hash: str, full_name: str | None) -> bool:
    """Return False when the username is already taken."""
    connection = sqlite3.connect(DB_PATH)
    try:
        connection.execute(
            "INSERT INTO users (username, password_hash, full_name) VALUES (?, ?, ?)",
            (username, password_hash, full_name),
        )
        connection.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        connection.close()
