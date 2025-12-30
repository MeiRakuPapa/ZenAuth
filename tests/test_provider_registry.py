# mypy: disable-error-code=no-untyped-def

import pytest
from zen_auth.dto import UserDTOForCreate
from zen_auth.errors import UserNotFoundError, UserVerificationError
from zen_auth.server.persistence.init_db import init_db
from zen_auth.server.persistence.session import (
    create_engine_from_dsn,
    create_sessionmaker,
    session_scope,
)
from zen_auth.server.usecases import user_service


def test_user_service_get_user(tmp_path):
    db = tmp_path / "test_user_service_get.db"
    engine = create_engine_from_dsn(f"sqlite:///{db}")
    init_db(engine)
    session_factory = create_sessionmaker(engine)

    try:
        with session_scope(session_factory) as session:
            user_service.create_user(
                session,
                UserDTOForCreate(
                    user_name="test_user",
                    password="password",
                    roles=["admin"],
                    real_name="Test User",
                    division="IT",
                    description="Test user",
                    policy_epoch=1,
                ),
            )

        with session_scope(session_factory) as session:
            user = user_service.get_user(session, "test_user")
        assert user.user_name == "test_user"
    finally:
        try:
            engine.dispose()
        except Exception:
            pass


def test_user_service_verify_user(tmp_path):
    db = tmp_path / "test_user_service_verify.db"
    engine = create_engine_from_dsn(f"sqlite:///{db}")
    init_db(engine)
    session_factory = create_sessionmaker(engine)

    try:
        with session_scope(session_factory) as session:
            user_service.create_user(
                session,
                UserDTOForCreate(
                    user_name="test_user",
                    password="password",
                    roles=["admin"],
                    real_name="Test User",
                    division="IT",
                    description="Test user",
                    policy_epoch=1,
                ),
            )

        with session_scope(session_factory) as session:
            user = user_service.verify_user(session, "test_user", "password")
        assert user.user_name == "test_user"

        with pytest.raises(UserVerificationError):
            with session_scope(session_factory) as session:
                user_service.verify_user(session, "test_user", "wrong")

        with pytest.raises(UserNotFoundError):
            with session_scope(session_factory) as session:
                user_service.verify_user(session, "missing", "password")
    finally:
        try:
            engine.dispose()
        except Exception:
            pass
