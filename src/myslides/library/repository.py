"""
Database connection, session management, and CRUD helpers.
"""
from __future__ import annotations

from collections.abc import Generator
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool

from myslides.config import settings
from myslides.library.models import Base


def get_db_path() -> Path:
    settings.ensure_directories()
    return settings.data_dir / "library.sqlite"


def get_engine(db_path: Path | None = None):
    path = db_path or get_db_path()
    return create_engine(
        f"sqlite:///{path.as_posix()}",
        connect_args={"check_same_thread": False, "timeout": 30},
    )


_engine = None
_SessionFactory = None


def init_db(engine=None) -> None:
    global _engine, _SessionFactory
    _engine = engine or get_engine()
    Base.metadata.create_all(_engine)
    _SessionFactory = sessionmaker(bind=_engine, autocommit=False, autoflush=False)


def get_session() -> Generator[Session, None, None]:
    """Yield a database session and guarantee cleanup on request exit."""
    global _SessionFactory
    if _SessionFactory is None:
        init_db()
    session = _SessionFactory()
    try:
        yield session
    finally:
        session.close()


def get_standalone_session() -> Session:
    """Get standalone session for background workers/scripts with manual close."""
    global _SessionFactory
    if _SessionFactory is None:
        init_db()
    return _SessionFactory()
