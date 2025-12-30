# mypy: disable-error-code=no-untyped-def
# mypy: disable-error-code=no-untyped-call

import os

import pytest
from fastapi.responses import Response
from zen_auth.claims.base import Claims
from zen_auth.config import ZENAUTH_CONFIG
from zen_auth.dto import UserDTOForCreate, UserDTOForUpdate
from zen_auth.errors import InvalidTokenError
from zen_auth.server.claims_self import ClaimsSelf
from zen_auth.server.persistence.init_db import init_db
from zen_auth.server.persistence.session import (
    create_engine_from_dsn,
    create_sessionmaker,
    session_scope,
)
from zen_auth.server.usecases import user_service


class DummyReq:
    def __init__(self, cookies=None, headers=None):
        self.cookies = cookies or {}
        self.headers = headers or {}


def make_user(session, user_name: str) -> None:
    user_service.create_user(
        session,
        UserDTOForCreate(
            user_name=user_name,
            password="password",
            roles=["user"],
            real_name="Edge Test",
            division="QA",
            description="",
            policy_epoch=1,
        ),
    )


def test_guard_with_deleted_user_returns_invalid_token(tmp_path):
    db = tmp_path / "test_deleted_user.db"
    dsn = f"sqlite:///{db}"
    engine = create_engine_from_dsn(dsn)
    init_db(engine)
    session_factory = create_sessionmaker(engine)

    # create user and token
    with session_scope(session_factory) as session:
        make_user(session, "deleted_user")
        user = user_service.get_user(session, "deleted_user")
        token = ClaimsSelf.from_user(user).token

    # delete user to simulate concurrent deletion
    with session_scope(session_factory) as session:
        user_service.delete_user(session, "deleted_user")

    req = DummyReq(cookies={ZENAUTH_CONFIG().cookie_name: token})
    resp = Response()

    dep = ClaimsSelf.guard()

    with pytest.raises(InvalidTokenError) as exc:
        with session_scope(session_factory) as session:
            dep(req, resp, None, session=session)

    assert getattr(exc.value, "kind", None) in {"user_not_found", "invalid"}

    try:
        engine.dispose()
    except Exception:
        pass
    try:
        os.remove(db)
    except OSError:
        pass


def test_policy_epoch_update_invalidates_token(tmp_path):
    db = tmp_path / "test_policy_epoch.db"
    dsn = f"sqlite:///{db}"
    engine = create_engine_from_dsn(dsn)
    init_db(engine)
    session_factory = create_sessionmaker(engine)

    with session_scope(session_factory) as session:
        make_user(session, "epoch_user")
        user = user_service.get_user(session, "epoch_user")
        token = ClaimsSelf.from_user(user).token

    # bump policy epoch to simulate policy change
    # trigger policy epoch bump via update (update increments epoch on password/roles/division change)
    with session_scope(session_factory) as session:
        user_service.update_user(session, UserDTOForUpdate(user_name="epoch_user", password="new_password"))

    req = DummyReq(cookies={ZENAUTH_CONFIG().cookie_name: token})
    resp = Response()
    dep = ClaimsSelf.guard()

    with pytest.raises(InvalidTokenError):
        with session_scope(session_factory) as session:
            dep(req, resp, None, session=session)

    try:
        engine.dispose()
    except Exception:
        pass
    try:
        os.remove(db)
    except OSError:
        pass


def test_guard_missing_token_raises_no_token():
    req = DummyReq(cookies={})
    resp = Response()
    dep = ClaimsSelf.guard()

    with pytest.raises(InvalidTokenError) as exc:
        dep(req, resp, None)

    assert getattr(exc.value, "kind", None) == "no_token"
