# mypy: disable-error-code=no-untyped-def

from __future__ import annotations

import pytest
from starlette.requests import Request
from zen_auth.claims import Claims
from zen_auth.claims.base import Claims
from zen_auth.dto import UserDTO
from zen_auth.errors import MissingRequiredScopesError

from tests.paths import auth_example_url


def _mock_endpoints_discovery(monkeypatch) -> None:
    class OkResp:
        status_code = 200
        text = ""

        def json(self):
            return {
                "data": {
                    "verify_token": auth_example_url("/verify/token"),
                    "verify_user": auth_example_url("/verify/user"),
                    "verify_user_role": auth_example_url("/verify/user_role"),
                    "verify_user_scope": auth_example_url("/verify/user_scope"),
                }
            }

    def fake_get(url, timeout=3.0, **kwargs):
        return OkResp()

    monkeypatch.setattr(Claims, "_GET", staticmethod(fake_get))


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


def test_scope_allows_if_any_required_group_matches(monkeypatch):
    allowed_scopes_by_user: dict[str, set[str]] = {}

    class OkResp:
        status_code = 200

        def __init__(self, allowed: bool):
            self._allowed = allowed
            self.text = ""

        def json(self):
            return {"data": {"allowed": self._allowed}}

    def fake_post(url, timeout=3.0, json=None, **kwargs):
        payload = json or {}
        user_name = payload.get("user_name")
        required_scopes = payload.get("required_scopes")
        if not isinstance(user_name, str) or not isinstance(required_scopes, list):
            return OkResp(False)
        allowed = allowed_scopes_by_user.get(user_name, set())
        return OkResp(bool(allowed & set(required_scopes)))

    monkeypatch.setattr(Claims, "_POST", staticmethod(fake_post))
    _mock_endpoints_discovery(monkeypatch)

    dep = Claims.scope("s1", "s2")

    user = _user("any")
    allowed_scopes_by_user[user.user_name] = {"s2"}
    assert dep(_req(), user=user).user_name == "test_user"


def test_scope_denies_if_no_required_group_matches(monkeypatch):
    allowed_scopes_by_user: dict[str, set[str]] = {}

    class OkResp:
        status_code = 200

        def __init__(self, allowed: bool):
            self._allowed = allowed
            self.text = ""

        def json(self):
            return {"data": {"allowed": self._allowed}}

    def fake_post(url, timeout=3.0, json=None, **kwargs):
        payload = json or {}
        user_name = payload.get("user_name")
        required_scopes = payload.get("required_scopes")
        if not isinstance(user_name, str) or not isinstance(required_scopes, list):
            return OkResp(False)
        allowed = allowed_scopes_by_user.get(user_name, set())
        return OkResp(bool(allowed & set(required_scopes)))

    monkeypatch.setattr(Claims, "_POST", staticmethod(fake_post))
    _mock_endpoints_discovery(monkeypatch)

    dep = Claims.scope("s1", "s2")

    user = _user("any")
    allowed_scopes_by_user[user.user_name] = {"s3"}

    with pytest.raises(MissingRequiredScopesError) as excinfo:
        dep(_req(), user=user)

    err = excinfo.value
    assert err.user_name == "test_user"
    assert err.required is not None
    assert list(err.required) == ["s1", "s2"]


def test_scope_denies_on_403_from_server(monkeypatch):
    class Resp403:
        status_code = 403
        text = ""

        def json(self):
            return {"data": {"allowed": False}}

    def fake_post(url, timeout=3.0, json=None, **kwargs):
        return Resp403()

    monkeypatch.setattr(Claims, "_POST", staticmethod(fake_post))
    _mock_endpoints_discovery(monkeypatch)

    dep = Claims.scope("s1")
    user = _user("any")

    with pytest.raises(MissingRequiredScopesError):
        dep(_req(), user=user)


def test_scope_denies_when_no_required_groups_provided(monkeypatch):
    class OkResp:
        status_code = 200

        def __init__(self, allowed: bool):
            self._allowed = allowed
            self.text = ""

        def json(self):
            return {"data": {"allowed": self._allowed}}

    def fake_post(url, timeout=3.0, json=None, **kwargs):
        return OkResp(True)

    monkeypatch.setattr(Claims, "_POST", staticmethod(fake_post))
    _mock_endpoints_discovery(monkeypatch)

    dep = Claims.scope()
    user = _user("any")

    with pytest.raises(MissingRequiredScopesError):
        dep(_req(), user=user)
