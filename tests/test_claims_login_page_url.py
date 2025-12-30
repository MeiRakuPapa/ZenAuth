import time

import pytest
from starlette.requests import Request
from zen_auth.claims import Claims
from zen_auth.config import ZENAUTH_CONFIG
from zen_auth.errors import ConfigError

from tests.paths import auth_example_url


def _make_request(*, scheme: str = "https", host: str = "web.example.com", port: int = 443) -> Request:
    scope = {
        "type": "http",
        "scheme": scheme,
        "server": (host, port),
        "path": "/",
        "query_string": b"",
        "headers": [],
    }
    return Request(scope)


def _seed_discovery_cache(req: Request, *, login_page_base: str) -> None:
    discovery_url = Claims._endpoints_discovery_url(req)
    now = time.monotonic()
    with Claims._endpoints_cache_lock:
        Claims._endpoints_cache.clear()
        Claims._endpoints_cache[discovery_url] = (
            now,
            {
                "login_page": login_page_base,
                "verify_token": "https://unused/verify/token",
                "verify_user": "https://unused/verify/user",
                "verify_user_role": "https://unused/verify/user/role",
                "verify_user_scope": "https://unused/verify/user/scope",
            },
        )


def test_login_page_url_uses_auth_server_origin(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ZENAUTH_AUTH_SERVER_ORIGIN", "https://auth.example.com")
    ZENAUTH_CONFIG.cache_clear()

    req = _make_request(host="web.example.com")
    _seed_discovery_cache(req, login_page_base=auth_example_url("/auth/login_page", https=True))
    url = Claims.login_page_url(req, app_id="app1")

    assert url.startswith(auth_example_url("/auth/login_page", https=True) + "?")
    assert "app_id=app1" in url


def test_login_page_url_requires_auth_server_origin(monkeypatch: pytest.MonkeyPatch) -> None:
    # Workspace `.env` may provide a default value; force an empty env var
    # (env vars take precedence over env_file) to validate required behavior.
    monkeypatch.setenv("ZENAUTH_AUTH_SERVER_ORIGIN", "")
    ZENAUTH_CONFIG.cache_clear()

    req = _make_request(host="web.example.net")
    with pytest.raises(ConfigError):
        Claims.login_page_url(req, app_id="app1")
