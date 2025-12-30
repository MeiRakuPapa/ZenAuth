from __future__ import annotations

import time
from urllib.parse import urlsplit

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from starlette.requests import Request
from zen_auth.claims import Claims
from zen_auth.server.config import ZENAUTH_SERVER_CONFIG
from zen_auth.server.persistence.init_db import init_db
from zen_auth.server.persistence.models import ClientAppOrm
from zen_auth.server.run import create_app

from tests.paths import api_path

# mypy: disable-error-code=no-untyped-def


def _seed_claims_discovery_cache(req: Request, endpoints: dict[str, str]) -> None:
    discovery_url = Claims._endpoints_discovery_url(req)
    now = time.monotonic()
    with Claims._endpoints_cache_lock:
        Claims._endpoints_cache[discovery_url] = (now, endpoints)


def test_login_page_response_sets_return_to_cookie(monkeypatch, tmp_path) -> None:
    db_path = tmp_path / "zenauth_test.sqlite3"
    monkeypatch.setenv("ZENAUTH_SERVER_DSN", f"sqlite+pysqlite:///{db_path}")
    ZENAUTH_SERVER_CONFIG.cache_clear()

    # Register a client app mapping: app_id -> return_to.
    engine = create_engine(f"sqlite+pysqlite:///{db_path}")
    init_db(engine)
    with Session(engine) as session:
        with session.begin():
            session.merge(
                ClientAppOrm(app_id="app1", display_name="App1", description=None, return_to="/after")
            )

    app = create_app()

    with TestClient(app) as client:
        res = client.get(api_path("/meta/endpoints"))
        assert res.status_code == 200
        endpoints: dict[str, str] = res.json()["data"]
        assert "login_page" in endpoints

        # Use Claims helper (discovery cached from the server response)
        req = Request(
            {
                "type": "http",
                "scheme": "http",
                "server": ("testserver", 80),
                "path": "/",
                "query_string": b"",
                "headers": [],
            }
        )
        _seed_claims_discovery_cache(req, endpoints)
        login_url = Claims.login_page_url(req, app_id="app1")

        parts = urlsplit(login_url)
        res = client.get(f"{parts.path}?{parts.query}")
        assert res.status_code == 200
        assert res.headers.get("content-type", "").startswith("text/html")

        # app_id cookie is set on the response
        cookie_header = res.headers.get("set-cookie", "")
        assert "login_app_id=" in cookie_header
        assert "app1" in cookie_header


def test_login_flow_posts_form_and_sets_auth_cookie(monkeypatch, tmp_path) -> None:
    db_path = tmp_path / "zenauth_test.sqlite3"
    monkeypatch.setenv("ZENAUTH_SERVER_DSN", f"sqlite+pysqlite:///{db_path}")

    # Create a known user for the test via bootstrap.
    monkeypatch.setenv("ZENAUTH_SERVER_BOOTSTRAP_ADMIN", "true")
    monkeypatch.setenv("ZENAUTH_SERVER_BOOTSTRAP_ADMIN_USER", "admin")
    monkeypatch.setenv("ZENAUTH_SERVER_BOOTSTRAP_ADMIN_PASSWORD", "pw")

    ZENAUTH_SERVER_CONFIG.cache_clear()

    # Register a client app mapping: app_id -> return_to.
    engine = create_engine(f"sqlite+pysqlite:///{db_path}")
    init_db(engine)
    with Session(engine) as session:
        with session.begin():
            session.merge(
                ClientAppOrm(app_id="app1", display_name="App1", description=None, return_to="/after")
            )

    app = create_app()

    with TestClient(app) as client:
        # 1) Load login page to set return_to cookie.
        res = client.get(api_path("/auth/login_page"), params={"app_id": "app1"})
        assert res.status_code == 200

        # 2) Post login form (server returns HX-Redirect header).
        res = client.post(
            api_path("/auth/login"),
            data={"user_name": "admin", "password": "pw"},
        )
        assert res.status_code == 200
        assert res.headers.get("HX-Redirect") == "/after"

        # 3) Auth cookie should be set on the client.
        assert client.cookies.get("access_token")


def test_login_flow_without_app_id_redirects_to_admin_top(monkeypatch, tmp_path) -> None:
    db_path = tmp_path / "zenauth_test.sqlite3"
    monkeypatch.setenv("ZENAUTH_SERVER_DSN", f"sqlite+pysqlite:///{db_path}")

    # Create a known user for the test via bootstrap.
    monkeypatch.setenv("ZENAUTH_SERVER_BOOTSTRAP_ADMIN", "true")
    monkeypatch.setenv("ZENAUTH_SERVER_BOOTSTRAP_ADMIN_USER", "admin")
    monkeypatch.setenv("ZENAUTH_SERVER_BOOTSTRAP_ADMIN_PASSWORD", "pw")

    ZENAUTH_SERVER_CONFIG.cache_clear()

    app = create_app()

    with TestClient(app) as client:
        # Load login page WITHOUT app_id
        res = client.get(api_path("/auth/login_page"))
        assert res.status_code == 200

        # Post login form
        res = client.post(
            api_path("/auth/login"),
            data={"user_name": "admin", "password": "pw"},
        )
        assert res.status_code == 200
        hx = res.headers.get("HX-Redirect")
        assert hx is not None
        assert urlsplit(hx).path == api_path("/admin/")


def test_login_page_with_unknown_app_id_returns_404(monkeypatch, tmp_path) -> None:
    db_path = tmp_path / "zenauth_test.sqlite3"
    monkeypatch.setenv("ZENAUTH_SERVER_DSN", f"sqlite+pysqlite:///{db_path}")
    ZENAUTH_SERVER_CONFIG.cache_clear()

    app = create_app()

    with TestClient(app) as client:
        res = client.get(api_path("/auth/login_page"), params={"app_id": "nope"})
        assert res.status_code == 404
        assert res.headers.get("content-type", "").startswith("text/html")
        assert "The specified APP_ID was not found" in res.text

        cookie_header = res.headers.get("set-cookie", "")
        assert "login_app_id=" not in cookie_header


def test_login_page_with_app_id_displays_app_display_name(monkeypatch, tmp_path) -> None:
    db_path = tmp_path / "zenauth_test.sqlite3"
    monkeypatch.setenv("ZENAUTH_SERVER_DSN", f"sqlite+pysqlite:///{db_path}")
    ZENAUTH_SERVER_CONFIG.cache_clear()

    engine = create_engine(f"sqlite+pysqlite:///{db_path}")
    init_db(engine)
    with Session(engine) as session:
        with session.begin():
            session.merge(
                ClientAppOrm(app_id="app1", display_name="My App", description=None, return_to="/after")
            )

    app = create_app()
    with TestClient(app) as client:
        res = client.get(api_path("/auth/login_page"), params={"app_id": "app1"})
        assert res.status_code == 200
        assert "My App" in res.text
