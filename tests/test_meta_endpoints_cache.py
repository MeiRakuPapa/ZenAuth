# mypy: disable-error-code=no-untyped-def
# mypy: disable-error-code=no-untyped-call

import pytest
from fastapi.responses import Response
from zen_auth.claims.base import Claims


class DummyReq:
    def __init__(self, cookies=None, headers=None):
        self.cookies = cookies or {}
        self.headers = headers or {}

        class Url:
            scheme = "http"
            hostname = "localhost"
            port = None

        self.url = Url()


class SimpleClaims:
    def __init__(self, username="u", token="tok"):
        self.username = username
        self.token = token


@pytest.mark.anyio
async def test_claims_discovers_endpoints_and_caches(monkeypatch):
    # ensure discovery cache starts empty
    Claims._endpoints_cache.clear()

    monkeypatch.setattr(Claims, "_validate_token", classmethod(lambda cls, t: SimpleClaims()))

    get_calls = {"n": 0}

    class GetResp:
        status_code = 200

        def json(self):
            return {
                "data": {
                    "verify_token": "http://auth.example/verify/token",
                    "verify_user": "http://auth.example/verify/user",
                    "verify_user_role": "http://auth.example/verify/user/role",
                    "verify_user_scope": "http://auth.example/verify/user/scope",
                }
            }

    def fake_get(*args, **kwargs):
        get_calls["n"] += 1
        return GetResp()

    posted = []

    class PostResp:
        def __init__(self):
            self.status_code = 200

        def json(self):
            return {
                "data": {
                    "token": "tok",
                    "user": {
                        "user_name": "u",
                        "roles": [],
                        "real_name": "",
                        "division": "",
                        "description": "",
                        "policy_epoch": 1,
                    },
                }
            }

    def fake_post(url, *args, **kwargs):
        posted.append(url)
        return PostResp()

    monkeypatch.setattr(Claims, "_GET", staticmethod(fake_get))
    monkeypatch.setattr(Claims, "_POST", staticmethod(fake_post))

    req = DummyReq(cookies={})

    dep1 = Claims.guard()
    dep2 = Claims.guard()

    # call twice via separate deps; discovery should only happen once (process cache)
    dep1(req, Response(), "Bearer tok")
    dep2(req, Response(), "Bearer tok")

    assert get_calls["n"] == 1
    assert posted == [
        "http://auth.example/verify/token",
        "http://auth.example/verify/token",
    ]
