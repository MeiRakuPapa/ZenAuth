from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Protocol, cast

from sqlalchemy.orm import Session
from zen_auth.server.persistence.init_db import init_db
from zen_auth.server.persistence.models import ClientAppOrm, RoleOrm, ScopeOrm, UserOrm
from zen_auth.server.persistence.session import create_engine_from_dsn


class ImportCsvModule(Protocol):
    def main(self, argv: list[str] | None = None) -> int: ...


def _load_import_csv_module() -> ImportCsvModule:
    script_path = Path(__file__).resolve().parents[1] / "server" / "src" / "scripts" / "import_csv.py"
    module_name = "zenauth_import_csv"
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    assert spec is not None
    assert spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod
    spec.loader.exec_module(mod)
    return cast(ImportCsvModule, mod)


def test_import_csv_upsert_inserts_data(tmp_path: Path) -> None:
    mod = _load_import_csv_module()

    fixtures = Path(__file__).resolve().parent / "fixtures" / "csv_import"
    db_path = tmp_path / "import_csv.sqlite3"
    dsn = f"sqlite+pysqlite:///{db_path.as_posix()}"

    rc = mod.main(
        [
            "--dsn",
            dsn,
            "--roles",
            str(fixtures / "roles.csv"),
            "--scopes",
            str(fixtures / "scopes.csv"),
            "--apps",
            str(fixtures / "apps.csv"),
            "--users",
            str(fixtures / "users.csv"),
        ]
    )
    assert rc == 0

    engine = create_engine_from_dsn(dsn)
    init_db(engine)

    with Session(engine) as session:
        # Users
        alice = session.get(UserOrm, "alice")
        assert alice is not None
        assert {r.role_name for r in alice.roles} == {"admin"}

        bob = session.get(UserOrm, "bob")
        assert bob is not None
        assert {r.role_name for r in bob.roles} == {"viewer"}

        # Roles + scopes binding
        admin = session.get(RoleOrm, "admin")
        assert admin is not None
        assert {s.scope_name for s in admin.scopes} >= {"read:users", "write:users"}

        viewer = session.get(RoleOrm, "viewer")
        assert viewer is not None
        assert {s.scope_name for s in viewer.scopes} >= {"read:users"}

        read_users = session.get(ScopeOrm, "read:users")
        assert read_users is not None
        assert {r.role_name for r in read_users.roles} >= {"admin", "viewer"}

        # App
        app = session.get(ClientAppOrm, "example_webapp")
        assert app is not None
        assert app.return_to == "/after_login"


def test_import_csv_upsert_updates_existing_data(tmp_path: Path) -> None:
    mod = _load_import_csv_module()

    fixtures = Path(__file__).resolve().parent / "fixtures" / "csv_import"
    db_path = tmp_path / "import_csv.sqlite3"
    dsn = f"sqlite+pysqlite:///{db_path.as_posix()}"

    # First import
    rc = mod.main(
        [
            "--dsn",
            dsn,
            "--roles",
            str(fixtures / "roles.csv"),
            "--scopes",
            str(fixtures / "scopes.csv"),
            "--apps",
            str(fixtures / "apps.csv"),
            "--users",
            str(fixtures / "users.csv"),
        ]
    )
    assert rc == 0

    # Update roles (change viewer display_name)
    roles_update = tmp_path / "roles_update.csv"
    roles_update.write_text(
        "role_name,display_name,description,scopes\n" 'viewer,Viewer v2,Read-only role,"read:users"\n',
        encoding="utf-8",
    )

    rc = mod.main(["--dsn", dsn, "--roles", str(roles_update), "--mode", "upsert"])
    assert rc == 0

    engine = create_engine_from_dsn(dsn)
    init_db(engine)

    with Session(engine) as session:
        viewer = session.get(RoleOrm, "viewer")
        assert viewer is not None
        assert viewer.display_name == "Viewer v2"
