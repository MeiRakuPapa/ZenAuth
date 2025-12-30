from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from zen_auth.server.config import ZENAUTH_SERVER_CONFIG
from zen_auth.server.persistence.init_db import init_db
from zen_auth.server.persistence.models import ClientAppOrm
from zen_auth.server.run import create_app

from tests.paths import api_path


def _bootstrap(monkeypatch: pytest.MonkeyPatch, db_path: Path) -> None:
    monkeypatch.setenv("ZENAUTH_SERVER_DSN", f"sqlite+pysqlite:///{db_path}")
    monkeypatch.setenv("ZENAUTH_SERVER_BOOTSTRAP_ADMIN", "true")
    monkeypatch.setenv("ZENAUTH_SERVER_BOOTSTRAP_ADMIN_USER", "admin")
    monkeypatch.setenv("ZENAUTH_SERVER_BOOTSTRAP_ADMIN_PASSWORD", "pw")
    ZENAUTH_SERVER_CONFIG.cache_clear()


def test_change_password_uses_app_id_redirect(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    db_path = tmp_path / "zenauth_test.sqlite3"
    _bootstrap(monkeypatch, db_path)

    engine = create_engine(f"sqlite+pysqlite:///{db_path}")
    init_db(engine)
    with Session(engine) as session:
        with session.begin():
            session.merge(
                ClientAppOrm(app_id="app1", display_name="App1", description=None, return_to="/after")
            )

    app = create_app()

    with TestClient(app) as client:
        # login first
        res = client.get(api_path("/auth/login_page"), params={"app_id": "app1"})
        assert res.status_code == 200

        res = client.post(api_path("/auth/login"), data={"user_name": "admin", "password": "pw"})
        assert res.status_code == 200
        assert client.cookies.get("access_token")

        # open change-password page with app_id -> should set login_app_id cookie
        res = client.get(api_path("/auth/change_password_page"), params={"app_id": "app1"})
        assert res.status_code == 200
        cookie_header = res.headers.get("set-cookie", "")
        assert "login_app_id=" in cookie_header
        assert "app1" in cookie_header

        # submit change password -> HX-Redirect should be resolved from app_id
        res = client.post(
            api_path("/auth/change_password"),
            data={"password": "pw2", "confirm_password": "pw2"},
            headers={"Origin": "http://testserver"},
        )
        assert res.status_code == 200
        assert res.headers.get("HX-Redirect") == "/after"


def test_change_password_page_unknown_app_id_returns_404(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    db_path = tmp_path / "zenauth_test.sqlite3"
    _bootstrap(monkeypatch, db_path)

    app = create_app()

    with TestClient(app) as client:
        # login first (otherwise guard will reject before app_id validation)
        res = client.get(api_path("/auth/login_page"))
        assert res.status_code == 200
        res = client.post(api_path("/auth/login"), data={"user_name": "admin", "password": "pw"})
        assert res.status_code == 200

        res = client.get(api_path("/auth/change_password_page"), params={"app_id": "nope"})
        assert res.status_code == 404
        assert res.headers.get("content-type", "").startswith("text/html")
        assert "The specified APP_ID was not found" in res.text

        cookie_header = res.headers.get("set-cookie", "")
        assert "login_app_id=" not in cookie_header
