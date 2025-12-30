# mypy: disable-error-code=no-untyped-def
# mypy: disable-error-code=no-untyped-call

import json

import pytest
import requests
from fastapi.responses import Response
from zen_auth.claims import Claims
from zen_auth.claims.base import Claims
from zen_auth.errors import ClaimSourceError, InvalidTokenError


class DummyReq:
    def __init__(self, cookies=None, headers=None):
        self.cookies = cookies or {}
        self.headers = headers or {}

        # minimal url attrs if needed
        class Url:
            scheme = "http"
            hostname = "localhost"
            port = None

        self.url = Url()


class FakeResp:
    def __init__(self, status_code=200, text=""):
        self.status_code = status_code
        self.text = text

    def json(self):
        raise json.JSONDecodeError("Expecting value", self.text, 0)


class SimpleClaims:
    def __init__(self, username="u", token="tok"):
        self.username = username
        self.token = token


@pytest.mark.anyio
async def test_remote_guard_timeout(monkeypatch):
    monkeypatch.setattr(Claims, "_validate_token", classmethod(lambda cls, t: SimpleClaims()))

    def fake_post(*args, **kwargs):
        raise requests.Timeout("timeout")

    monkeypatch.setattr(Claims, "_POST", fake_post)

    dep = Claims.guard(url="http://auth/verify/token")
    req = DummyReq(cookies={})
    resp = Response()

    with pytest.raises(ClaimSourceError) as exc:
        dep(req, resp, "Bearer tok")

    assert getattr(exc.value, "code", None) == "timeout"


@pytest.mark.anyio
async def test_remote_guard_connection_error(monkeypatch):
    monkeypatch.setattr(Claims, "_validate_token", classmethod(lambda cls, t: SimpleClaims()))

    def fake_post(*args, **kwargs):
        raise requests.ConnectionError("conn")

    monkeypatch.setattr(Claims, "_POST", fake_post)

    dep = Claims.guard(url="http://auth/verify/token")
    req = DummyReq(cookies={})
    resp = Response()

    with pytest.raises(ClaimSourceError) as exc:
        dep(req, resp, "Bearer tok")

    assert getattr(exc.value, "code", None) == "connection"


@pytest.mark.anyio
async def test_remote_guard_invalid_json(monkeypatch):
    monkeypatch.setattr(Claims, "_validate_token", classmethod(lambda cls, t: SimpleClaims()))

    fake = FakeResp(status_code=200, text="not-json")

    def fake_post(*args, **kwargs):
        return fake

    monkeypatch.setattr(Claims, "_POST", fake_post)

    dep = Claims.guard(url="http://auth/verify/token")
    req = DummyReq(cookies={})
    resp = Response()

    with pytest.raises(InvalidTokenError) as exc:
        dep(req, resp, "Bearer tok")

    assert getattr(exc.value, "kind", None) == "invalid"


@pytest.mark.anyio
async def test_remote_guard_non_200_returns_invalid_token(monkeypatch):
    monkeypatch.setattr(Claims, "_validate_token", classmethod(lambda cls, t: SimpleClaims()))

    class OkResp:
        def __init__(self, status_code=401, data=None):
            self.status_code = status_code
            self._data = data or {"data": {}}
            self.text = "err"

        def json(self):
            return self._data

    def fake_post(*args, **kwargs):
        return OkResp(status_code=401)

    monkeypatch.setattr(Claims, "_POST", fake_post)

    dep = Claims.guard(url="http://auth/verify/token")
    req = DummyReq(cookies={})
    resp = Response()

    with pytest.raises(InvalidTokenError):
        dep(req, resp, "Bearer tok")
