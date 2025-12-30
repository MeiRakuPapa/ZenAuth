# mypy: disable-error-code=no-untyped-def

import pytest
from zen_auth.dto import (
    RoleDTOForCreate,
    RoleDTOForUpdate,
    ScopeDTOForCreate,
    UserDTOForCreate,
)
from zen_auth.errors import RoleNotFoundError, ScopeNotFoundError
from zen_auth.server.persistence.init_db import init_db
from zen_auth.server.persistence.session import (
    create_engine_from_dsn,
    create_sessionmaker,
    session_scope,
)
from zen_auth.server.usecases import (
    rbac_checks,
    role_service,
    scope_service,
    user_service,
)


def _make_session_factory(dsn: str):
    engine = create_engine_from_dsn(dsn)
    init_db(engine)
    return engine, create_sessionmaker(engine)


def test_role_scope_crud_and_binding(tmp_path):
    db = tmp_path / "rbac.db"
    engine, session_factory = _make_session_factory(f"sqlite:///{db}")

    with session_scope(session_factory) as session:
        role_service.create_role(session, RoleDTOForCreate(role_name="viewer", display_name="Viewer"))
        scope_service.create_scope(
            session, ScopeDTOForCreate(scope_name="read:users", display_name="Read Users")
        )

    with session_scope(session_factory) as session:
        scopes = role_service.set_role_scopes(session, "viewer", ["read:users"])
        assert [s.scope_name for s in scopes] == ["read:users"]

    with session_scope(session_factory) as session:
        role = role_service.update_role(session, "viewer", RoleDTOForUpdate(display_name="Viewer2"))
        assert role.display_name == "Viewer2"

    with session_scope(session_factory) as session:
        scope_service.delete_scope(session, "read:users")

    with session_scope(session_factory) as session:
        with pytest.raises(ScopeNotFoundError):
            scope_service.get_scope(session, "read:users")

    with session_scope(session_factory) as session:
        role_service.delete_role(session, "viewer")

    with session_scope(session_factory) as session:
        with pytest.raises(RoleNotFoundError):
            role_service.get_role(session, "viewer")

    try:
        engine.dispose()
    except Exception:
        pass


def test_user_role_and_scope_verification_helpers(tmp_path):
    db = tmp_path / "rbac_verify.db"
    engine, session_factory = _make_session_factory(f"sqlite:///{db}")

    with session_scope(session_factory) as session:
        role_service.create_role(session, RoleDTOForCreate(role_name="viewer", display_name="Viewer"))
        scope_service.create_scope(
            session, ScopeDTOForCreate(scope_name="read:users", display_name="Read Users")
        )
        role_service.set_role_scopes(session, "viewer", ["read:users"])
        user_service.create_user(
            session,
            UserDTOForCreate(
                user_name="alice",
                password="password",
                roles=["viewer"],
                real_name="Alice",
            ),
        )

    with session_scope(session_factory) as session:
        assert rbac_checks.user_has_role(session, "alice", "viewer") is True
        assert rbac_checks.user_has_role(session, "alice", "admin") is False

        assert rbac_checks.user_allowed_scope(session, "alice", "read:users") is True
        assert rbac_checks.user_allowed_scope(session, "alice", "write:users") is False

        # unknown user => False
        assert rbac_checks.user_has_role(session, "missing", "viewer") is False
        assert rbac_checks.user_allowed_scope(session, "missing", "read:users") is False

    try:
        engine.dispose()
    except Exception:
        pass
