from __future__ import annotations

import contextlib
from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from ..config import ZENAUTH_SERVER_CONFIG


def create_engine_from_dsn(dsn: str) -> Engine:
    if dsn.startswith("sqlite"):
        return create_engine(
            dsn,
            poolclass=StaticPool,
            connect_args={"check_same_thread": False},
        )
    return create_engine(dsn, pool_pre_ping=True)


def get_engine() -> Engine:
    return create_engine_from_dsn(ZENAUTH_SERVER_CONFIG().dsn)


def create_sessionmaker(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autocommit=False, autoflush=False)


@contextlib.contextmanager
def session_scope(session_factory: sessionmaker[Session]) -> Iterator[Session]:
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_session() -> Iterator[Session]:
    """FastAPI dependency: yields a DB session bound to configured engine."""

    engine = get_engine()
    session_factory = create_sessionmaker(engine)
    with session_scope(session_factory) as session:
        yield session
