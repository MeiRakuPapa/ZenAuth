# mypy: disable-error-code=no-untyped-def

from __future__ import annotations

import pytest
from starlette.requests import Request
from zen_auth.claims import Claims
from zen_auth.claims.base import Claims
from zen_auth.dto import UserDTO
from zen_auth.errors import MissingRequiredRolesError, MissingRequiredRolesOrScopesError
from zen_auth.server.claims_self import ClaimsSelf

from tests.paths import api_path, auth_example_url


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


def _mock_endpoints_discovery_with_combined(monkeypatch) -> None:
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
                    "verify_user_role_or_scope": auth_example_url("/verify/user/role_or_scope"),
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


def test_rbac_allows_if_any_required_group_matches(monkeypatch):
    roles_by_user: dict[str, set[str]] = {}

    class OkResp:
        status_code = 200

        def __init__(self, has_role: bool):
            self._has_role = has_role
            self.text = ""

        def json(self):
            return {"data": {"has_role": self._has_role}}

    def fake_post(url, timeout=3.0, json=None, **kwargs):
        payload = json or {}
        user_name = payload.get("user_name")
        required_roles = payload.get("required_roles")
        if not isinstance(user_name, str):
            return OkResp(False)
        user_roles = roles_by_user.get(user_name, set())
        if not isinstance(required_roles, list):
            return OkResp(False)
        return OkResp(bool(user_roles & set(required_roles)))

    monkeypatch.setattr(Claims, "_POST", staticmethod(fake_post))
    _mock_endpoints_discovery(monkeypatch)

    for impl in (ClaimsSelf, Claims):
        dep = impl.role("admin", "viewer")

        user = _user("admin")
        roles_by_user[user.user_name] = set(user.roles)
        assert dep(_req(), user=user).user_name == "test_user"

        user = _user("viewer")
        roles_by_user[user.user_name] = set(user.roles)
        assert dep(_req(), user=user).user_name == "test_user"


def test_rbac_denies_if_no_required_group_matches(monkeypatch):
    roles_by_user: dict[str, set[str]] = {}

    class OkResp:
        status_code = 200

        def __init__(self, has_role: bool):
            self._has_role = has_role
            self.text = ""

        def json(self):
            return {"data": {"has_role": self._has_role}}

    def fake_post(url, timeout=3.0, json=None, **kwargs):
        payload = json or {}
        user_name = payload.get("user_name")
        required_roles = payload.get("required_roles")
        if not isinstance(user_name, str):
            return OkResp(False)
        user_roles = roles_by_user.get(user_name, set())
        if not isinstance(required_roles, list):
            return OkResp(False)
        return OkResp(bool(user_roles & set(required_roles)))

    monkeypatch.setattr(Claims, "_POST", staticmethod(fake_post))
    _mock_endpoints_discovery(monkeypatch)

    for impl in (ClaimsSelf, Claims):
        dep = impl.role("admin", "viewer")

        user = _user("guest")
        roles_by_user[user.user_name] = set(user.roles)

        with pytest.raises(MissingRequiredRolesError) as excinfo:
            dep(_req(), user=user)

        err = excinfo.value
        assert err.user_name == "test_user"
        assert set(err.roles or []) == {"guest"}
        assert err.required is not None
        assert list(err.required) == ["admin", "viewer"]


def test_rbac_role_denies_on_403_from_server(monkeypatch):
    class Resp403:
        status_code = 403
        text = ""

        def json(self):
            return {"data": {"has_role": False}}

    def fake_post(url, timeout=3.0, json=None, **kwargs):
        return Resp403()

    monkeypatch.setattr(Claims, "_POST", staticmethod(fake_post))
    _mock_endpoints_discovery(monkeypatch)

    dep = Claims.role("admin")
    user = _user("guest")

    with pytest.raises(MissingRequiredRolesError):
        dep(_req(), user=user)


def test_rbac_denies_when_no_required_groups_provided(monkeypatch):
    roles_by_user: dict[str, set[str]] = {}

    class OkResp:
        status_code = 200

        def __init__(self, has_role: bool):
            self._has_role = has_role
            self.text = ""

        def json(self):
            return {"data": {"has_role": self._has_role}}

    def fake_post(url, timeout=3.0, json=None, **kwargs):
        payload = json or {}
        user_name = payload.get("user_name")
        required_roles = payload.get("required_roles")
        if not isinstance(user_name, str):
            return OkResp(False)
        user_roles = roles_by_user.get(user_name, set())
        if not isinstance(required_roles, list):
            return OkResp(False)
        return OkResp(bool(user_roles & set(required_roles)))

    monkeypatch.setattr(Claims, "_POST", staticmethod(fake_post))
    _mock_endpoints_discovery(monkeypatch)

    for impl in (ClaimsSelf, Claims):
        dep = impl.role()

        user = _user("admin")
        roles_by_user[user.user_name] = set(user.roles)
        with pytest.raises(MissingRequiredRolesError):
            dep(_req(), user=user)


def test_rbac_role_or_scope_allows_if_role_matches(monkeypatch):
    roles_by_user: dict[str, set[str]] = {}

    class OkResp:
        status_code = 200

        def __init__(self, data: dict[str, object]):
            self._data = data
            self.text = ""

        def json(self):
            return {"data": self._data}

    def fake_post(url, timeout=3.0, json=None, **kwargs):
        payload = json or {}
        user_name = payload.get("user_name")
        if not isinstance(user_name, str):
            return OkResp({"has_role": False})

        if "required_roles" in payload:
            required_roles = payload.get("required_roles")
            if not isinstance(required_roles, list):
                return OkResp({"has_role": False})
            ok = bool(roles_by_user.get(user_name, set()) & set(required_roles))
            return OkResp({"has_role": ok})

        if "required_scopes" in payload:
            # not used in this test
            return OkResp({"allowed": False})

        return OkResp({"has_role": False})

    monkeypatch.setattr(Claims, "_POST", staticmethod(fake_post))
    _mock_endpoints_discovery(monkeypatch)

    dep = Claims.role_or_scope(roles=("admin",), scopes=("s1",))
    user = _user("admin")
    roles_by_user[user.user_name] = set(user.roles)
    assert dep(_req(), user=user).user_name == "test_user"


def test_rbac_role_or_scope_uses_combined_endpoint_and_allows(monkeypatch):
    calls: list[tuple[str, dict[str, object] | None]] = []

    class OkResp:
        status_code = 200
        text = ""

        def json(self):
            return {"data": {"has_access": True}}

    def fake_post(url, timeout=3.0, json=None, **kwargs):
        if url.endswith(api_path("/verify/user_role")) or url.endswith(api_path("/verify/user_scope")):
            raise AssertionError("Expected combined endpoint to be used")
        calls.append((url, json))
        return OkResp()

    monkeypatch.setattr(Claims, "_POST", staticmethod(fake_post))
    Claims._endpoints_cache.clear()
    _mock_endpoints_discovery_with_combined(monkeypatch)

    dep = Claims.role_or_scope(roles=("admin",), scopes=("s1",))
    user = _user("admin")
    assert dep(_req(), user=user).user_name == "test_user"

    # Single POST to the combined endpoint (preferred)
    assert len(calls) == 1
    assert calls[0][0].endswith(api_path("/verify/user/role_or_scope"))

    # Avoid leaking global discovery cache into other tests
    Claims._endpoints_cache.clear()


def test_rbac_role_or_scope_uses_combined_endpoint_and_denies(monkeypatch):
    calls: list[tuple[str, dict[str, object] | None]] = []

    class DenyResp:
        status_code = 403
        text = ""

        def json(self):
            return {"data": {"has_access": False}}

    def fake_post(url, timeout=3.0, json=None, **kwargs):
        if url.endswith(api_path("/verify/user_role")) or url.endswith(api_path("/verify/user_scope")):
            raise AssertionError("Expected combined endpoint to be used")
        calls.append((url, json))
        return DenyResp()

    monkeypatch.setattr(Claims, "_POST", staticmethod(fake_post))
    Claims._endpoints_cache.clear()
    _mock_endpoints_discovery_with_combined(monkeypatch)

    dep = Claims.role_or_scope(roles=("admin",), scopes=("s1",))
    user = _user("guest")

    with pytest.raises(MissingRequiredRolesOrScopesError):
        dep(_req(), user=user)

    assert len(calls) == 1
    assert calls[0][0].endswith(api_path("/verify/user/role_or_scope"))

    # Avoid leaking global discovery cache into other tests
    Claims._endpoints_cache.clear()
