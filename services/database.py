"""Database utilities using SQLAlchemy."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, scoped_session, sessionmaker

engine = None
SessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False))
Base = declarative_base()


def init_db(database_url: str) -> None:
    """Initialise the database engine and session factory."""
    global engine

    if engine is None:
        engine = create_engine(database_url, future=True)
        SessionLocal.configure(bind=engine)

        # Import models to ensure they are registered with SQLAlchemy metadata
        from models import Job  # noqa: F401

        Base.metadata.create_all(bind=engine)


@contextmanager
def session_scope() -> Generator:
    """Provide a transactional scope around a series of operations."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

