# mypy: disable-error-code=no-untyped-def

from __future__ import annotations

import pytest
from starlette.requests import Request
from zen_auth.claims.base import Claims
from zen_auth.dto import UserDTO
from zen_auth.errors import MissingRequiredScopesError
from zen_auth.server.claims_self import ClaimsSelf
from zen_auth.server.usecases import rbac_checks


def _req() -> Request:
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [],
        "query_string": b"",
        "scheme": "http",
        "client": ("testclient", 123),
        "server": ("testserver", 80),
    }
    return Request(scope)


def _user(*roles: str) -> UserDTO:
    return UserDTO(
        user_name="test_user",
        password=None,
        roles=list(roles),
        real_name="Test User",
        division="IT",
        description="test",
        policy_epoch=1,
        created_at=None,
        updated_at=None,
    )


def test_claims_self_scope_allows_if_any_required_group_matches(monkeypatch):
    allowed_scopes_by_user: dict[str, set[str]] = {}

    def fake_guard():
        def dep(req, user):
            _ = req
            return user

        return dep

    def fake_has_required_scopes(session, user_name: str, required_scopes: list[str]) -> bool:
        _ = session
        allowed = allowed_scopes_by_user.get(user_name, set())
        return bool(allowed & set(required_scopes))

    monkeypatch.setattr(ClaimsSelf, "guard", staticmethod(fake_guard))
    monkeypatch.setattr(rbac_checks, "has_required_scopes", fake_has_required_scopes)

    dep = ClaimsSelf.scope("s1", "s2")

    user = _user("any")
    allowed_scopes_by_user[user.user_name] = {"s2"}
    assert dep(_req(), user=user, session=None).user_name == "test_user"


def test_claims_self_scope_denies_when_no_required_groups_provided(monkeypatch):
    def fake_guard():
        def dep(req, user):
            _ = req
            return user

        return dep

    monkeypatch.setattr(ClaimsSelf, "guard", staticmethod(fake_guard))

    dep = ClaimsSelf.scope()
    user = _user("any")

    with pytest.raises(MissingRequiredScopesError):
        dep(_req(), user=user, session=None)
