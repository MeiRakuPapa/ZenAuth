from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from zen_auth.server.config import ZENAUTH_SERVER_CONFIG
from zen_auth.server.run import create_app

from tests.paths import api_path


def test_client_apps_crud_admin_ui(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    db_path = tmp_path / "zenauth_test.sqlite3"
    monkeypatch.setenv("ZENAUTH_SERVER_DSN", f"sqlite+pysqlite:///{db_path}")

    # Create a known admin user for RBAC-protected admin endpoints.
    monkeypatch.setenv("ZENAUTH_SERVER_BOOTSTRAP_ADMIN", "true")
    monkeypatch.setenv("ZENAUTH_SERVER_BOOTSTRAP_ADMIN_USER", "admin")
    monkeypatch.setenv("ZENAUTH_SERVER_BOOTSTRAP_ADMIN_PASSWORD", "pw")
    ZENAUTH_SERVER_CONFIG.cache_clear()

    app = create_app()

    with TestClient(app) as client:
        csrf_headers = {"Origin": "http://testserver"}

        # Login to obtain access_token cookie.
        res = client.post(
            api_path("/auth/login"),
            data={"user_name": "admin", "password": "pw"},
        )
        assert res.status_code == 200
        assert client.cookies.get("access_token")

        # Create (Admin UI)
        res = client.post(
            api_path("/admin/app/create"),
            data={
                "app_id": "app1",
                "display_name": "My App",
                "description": "desc",
                "return_to": "/after",
            },
            headers=csrf_headers,
        )
        assert res.status_code == 200
        assert "app1" in res.text

        # List
        res = client.get(api_path("/admin/app"))
        assert res.status_code == 200
        assert "app1" in res.text

        # Update
        res = client.post(
            api_path("/admin/app/update"),
            data={
                "app_id": "app1",
                "display_name": "My App 2",
                "description": "desc",
                "return_to": "/after",
            },
            headers=csrf_headers,
        )
        assert res.status_code == 200
        assert "My App 2" in res.text

        # Delete
        res = client.delete(api_path("/admin/app/delete/app1"), headers=csrf_headers)
        assert res.status_code == 204

        # Gone
        res = client.get(api_path("/admin/app/edit/app1"))
        assert res.status_code == 404
