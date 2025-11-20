"""One-time helper script to add the email column to the jobs table."""

from __future__ import annotations

from sqlalchemy import inspect, text

from config import Config
from services import database


def ensure_email_column() -> None:
    """Add the email column to jobs if it does not already exist."""
    Config.ensure_directories()
    database.init_db(Config.DATABASE_URL)

    bind = database.engine or database.SessionLocal.bind
    if bind is None:
        raise RuntimeError("Database engine is not initialized.")

    inspector = inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("jobs")}
    if "email" in columns:
        print("Email column already exists; nothing to do.")
        return

    with bind.begin() as connection:
        connection.execute(text("ALTER TABLE jobs ADD COLUMN email VARCHAR(255)"))
    print("Email column added successfully.")


if __name__ == "__main__":
    ensure_email_column()

