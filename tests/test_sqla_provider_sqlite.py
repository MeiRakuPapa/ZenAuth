# mypy: disable-error-code=no-untyped-def

import os

import pytest
from zen_auth.dto import UserDTOForCreate, UserDTOForUpdate
from zen_auth.errors import (
    UserAlreadyExistsError,
    UserNotFoundError,
    UserVerificationError,
)
from zen_auth.server.persistence.init_db import init_db
from zen_auth.server.persistence.session import (
    create_engine_from_dsn,
    create_sessionmaker,
    session_scope,
)
from zen_auth.server.usecases import user_service


def _make_session_factory(dsn: str):
    engine = create_engine_from_dsn(dsn)
    init_db(engine)
    return engine, create_sessionmaker(engine)


def test_user_service_with_sqlite():
    engine, session_factory = _make_session_factory("sqlite:///test_user_service.db")

    user_data = UserDTOForCreate(
        user_name="test_user",
        password="test_password",
        roles=["user"],
        real_name="Test User",
        division="Test Division",
        description="Test Description",
        policy_epoch=1,
    )
    with session_scope(session_factory) as session:
        user = user_service.create_user(session, user_data)

    with session_scope(session_factory) as session:
        fetched_user = user_service.get_user(session, "test_user")
    assert fetched_user.user_name == user.user_name
    assert fetched_user.roles == user.roles
    assert fetched_user.real_name == user.real_name
    assert fetched_user.division == user.division
    assert fetched_user.description == user.description

    try:
        engine.dispose()
    except Exception:
        pass
    os.remove("test_user_service.db")


def test_verify_user():
    engine, session_factory = _make_session_factory("sqlite:///test_user_service_verify.db")

    user_data = UserDTOForCreate(
        user_name="verify_user",
        password="verify_password",
        roles=["user"],
        real_name="Verify User",
        division="Test Division",
        description="Test Description",
        policy_epoch=1,
    )
    with session_scope(session_factory) as session:
        user_service.create_user(session, user_data)

    with session_scope(session_factory) as session:
        verified_user = user_service.verify_user(session, "verify_user", "verify_password")
    assert verified_user.user_name == "verify_user"

    with pytest.raises(UserVerificationError):
        with session_scope(session_factory) as session:
            user_service.verify_user(session, "verify_user", "wrong_password")

    with pytest.raises(UserNotFoundError):
        with session_scope(session_factory) as session:
            user_service.verify_user(session, "non_existent_user", "some_password")

    try:
        engine.dispose()
    except Exception:
        pass
    os.remove("test_user_service_verify.db")


def test_empty_username():
    engine, session_factory = _make_session_factory("sqlite:///test_empty_username.db")

    with pytest.raises(ValueError):
        with session_scope(session_factory) as session:
            user_service.create_user(
                session,
                UserDTOForCreate(
                    user_name="",
                    password="password",
                    roles=["user"],
                    real_name="",
                    division="",
                    description="",
                    policy_epoch=1,
                ),
            )

    try:
        engine.dispose()
    except Exception:
        pass
    os.remove("test_empty_username.db")


def test_empty_password():
    engine, session_factory = _make_session_factory("sqlite:///test_empty_password.db")

    with pytest.raises(ValueError):
        with session_scope(session_factory) as session:
            user_service.create_user(
                session,
                UserDTOForCreate(
                    user_name="user",
                    password="",
                    roles=["user"],
                    real_name="",
                    division="",
                    description="",
                    policy_epoch=1,
                ),
            )

    try:
        engine.dispose()
    except Exception:
        pass
    os.remove("test_empty_password.db")


def test_long_username():
    engine, session_factory = _make_session_factory("sqlite:///test_long_username.db")

    long_string = "a" * 256
    with pytest.raises(ValueError):
        with session_scope(session_factory) as session:
            user_service.create_user(
                session,
                UserDTOForCreate(
                    user_name=long_string,
                    password="password",
                    roles=["user"],
                    real_name="",
                    division="",
                    description="",
                    policy_epoch=1,
                ),
            )

    try:
        engine.dispose()
    except Exception:
        pass
    os.remove("test_long_username.db")


def test_duplicate_user():
    engine, session_factory = _make_session_factory("sqlite:///test_duplicate_user.db")

    user_data = UserDTOForCreate(
        user_name="duplicate_user",
        password="password",
        roles=["user"],
        real_name="",
        division="",
        description="",
        policy_epoch=1,
    )
    with session_scope(session_factory) as session:
        user_service.create_user(session, user_data)

    with pytest.raises(UserAlreadyExistsError):
        with session_scope(session_factory) as session:
            user_service.create_user(session, user_data)

    try:
        engine.dispose()
    except Exception:
        pass
    os.remove("test_duplicate_user.db")


def test_read_user():
    engine, session_factory = _make_session_factory("sqlite:///test_read_user.db")

    user_data = UserDTOForCreate(
        user_name="read_user",
        password="password",
        roles=["user"],
        real_name="Read User",
        division="Test Division",
        description="Test Description",
        policy_epoch=1,
    )
    with session_scope(session_factory) as session:
        user_service.create_user(session, user_data)

    with session_scope(session_factory) as session:
        fetched_user = user_service.get_user(session, "read_user")
    assert fetched_user.user_name == "read_user"
    assert fetched_user.roles == ["user"]
    assert fetched_user.real_name == "Read User"

    try:
        engine.dispose()
    except Exception:
        pass
    os.remove("test_read_user.db")


def test_update_user():
    engine, session_factory = _make_session_factory("sqlite:///test_update_user.db")

    user_data = UserDTOForCreate(
        user_name="update_user",
        password="password",
        roles=["user"],
        real_name="Update User",
        division="Test Division",
        description="Test Description",
        policy_epoch=1,
    )
    with session_scope(session_factory) as session:
        user_service.create_user(session, user_data)

    with session_scope(session_factory) as session:
        updated_user = user_service.update_user(
            session,
            UserDTOForUpdate(
                user_name="update_user",
                password="new_password",
                roles=["admin"],
                real_name="Updated User",
                division="Updated Division",
                description="Updated Description",
            ),
        )
    assert updated_user.roles == ["admin"]
    assert updated_user.real_name == "Updated User"

    with pytest.raises(UserVerificationError):
        with session_scope(session_factory) as session:
            user_service.verify_user(session, "update_user", "password")

    with session_scope(session_factory) as session:
        user_service.verify_user(session, "update_user", "new_password")

    try:
        engine.dispose()
    except Exception:
        pass
    os.remove("test_update_user.db")


def test_delete_user():
    engine, session_factory = _make_session_factory("sqlite:///test_delete_user.db")

    user_data = UserDTOForCreate(
        user_name="delete_user",
        password="password",
        roles=["user"],
        real_name="Delete User",
        division="Test Division",
        description="Test Description",
        policy_epoch=1,
    )
    with session_scope(session_factory) as session:
        user_service.create_user(session, user_data)

    with session_scope(session_factory) as session:
        user_service.delete_user(session, "delete_user")

    with pytest.raises(UserNotFoundError):
        with session_scope(session_factory) as session:
            user_service.get_user(session, "delete_user")

    try:
        engine.dispose()
    except Exception:
        pass
    os.remove("test_delete_user.db")


if __name__ == "__main__":
    pytest.main()
