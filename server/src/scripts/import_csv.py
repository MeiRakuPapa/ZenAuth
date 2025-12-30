from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import dataclass
from pathlib import Path


def _bootstrap_sys_path() -> None:
    """Allow running this file directly without installing packages."""

    repo_root = Path(__file__).resolve().parents[3]
    for p in (repo_root / "core" / "src", repo_root / "server" / "src"):
        p_str = str(p)
        if p_str not in sys.path:
            sys.path.insert(0, p_str)


_bootstrap_sys_path()

from sqlalchemy.orm import Session  # noqa: E402
from zen_auth.dto import (  # noqa: E402
    RoleDTOForCreate,
    RoleDTOForUpdate,
    ScopeDTOForCreate,
    ScopeDTOForUpdate,
    UserDTOForCreate,
    UserDTOForUpdate,
)
from zen_auth.server.persistence.init_db import init_db  # noqa: E402
from zen_auth.server.persistence.models import (  # noqa: E402
    ClientAppOrm,
    RoleOrm,
    ScopeOrm,
    UserOrm,
)
from zen_auth.server.persistence.session import (  # noqa: E402
    create_engine_from_dsn,
    create_sessionmaker,
    session_scope,
)
from zen_auth.server.usecases import (  # noqa: E402
    app_service,
    role_service,
    scope_service,
    user_service,
)


@dataclass(frozen=True)
class CsvPaths:
    users: Path | None
    apps: Path | None
    roles: Path | None
    scopes: Path | None


def _split_list(value: str | None) -> list[str]:
    if value is None:
        return []
    s = value.strip()
    if not s:
        return []
    return [x.strip() for x in s.split(",") if x.strip()]


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError(f"CSV has no header: {path}")
        rows: list[dict[str, str]] = []
        for raw in reader:
            # Normalize: DictReader can return None values
            row: dict[str, str] = {k: (v or "").strip() for k, v in raw.items() if k is not None}
            # Skip fully empty lines
            if not any(row.values()):
                continue
            rows.append(row)
        return rows


def _get(row: dict[str, str], key: str) -> str | None:
    v = row.get(key)
    if v is None:
        return None
    v = v.strip()
    return v if v else None


def _upsert_role(session: Session, row: dict[str, str], *, mode: str) -> None:
    role_name = _get(row, "role_name")
    if not role_name:
        raise ValueError("roles.csv: role_name is required")

    display_name = _get(row, "display_name") or role_name
    description = _get(row, "description")

    exists = session.get(RoleOrm, role_name) is not None

    if mode == "create" and exists:
        raise ValueError(f"role already exists: {role_name}")

    if not exists:
        role_service.create_role(
            session,
            RoleDTOForCreate(role_name=role_name, display_name=display_name, description=description),
        )
    else:
        role_service.update_role(
            session,
            role_name,
            RoleDTOForUpdate(display_name=display_name, description=description),
        )

    scopes = _split_list(_get(row, "scopes"))
    if scopes:
        role_service.set_role_scopes(session, role_name, scopes)


def _upsert_scope(session: Session, row: dict[str, str], *, mode: str) -> None:
    scope_name = _get(row, "scope_name")
    if not scope_name:
        raise ValueError("scopes.csv: scope_name is required")

    display_name = _get(row, "display_name") or scope_name
    description = _get(row, "description")
    roles = _split_list(_get(row, "roles"))

    exists = session.get(ScopeOrm, scope_name) is not None

    if mode == "create" and exists:
        raise ValueError(f"scope already exists: {scope_name}")

    if not exists:
        scope_service.create_scope(
            session,
            ScopeDTOForCreate(
                scope_name=scope_name,
                display_name=display_name,
                description=description,
                roles=roles,
            ),
        )
    else:
        scope_service.update_scope(
            session,
            scope_name,
            ScopeDTOForUpdate(
                display_name=display_name,
                description=description,
                roles=roles if "roles" in row else None,
            ),
        )


def _upsert_app(session: Session, row: dict[str, str], *, mode: str) -> None:
    app_id = _get(row, "app_id")
    if not app_id:
        raise ValueError("apps.csv: app_id is required")

    display_name = _get(row, "display_name")
    description = _get(row, "description")
    return_to = _get(row, "return_to")
    if not return_to:
        raise ValueError("apps.csv: return_to is required")

    exists = session.get(ClientAppOrm, app_id) is not None

    if mode == "create" and exists:
        raise ValueError(f"app already exists: {app_id}")

    if not exists:
        app_service.create_app(
            session,
            app_id=app_id,
            display_name=display_name,
            description=description,
            return_to=return_to,
        )
    else:
        app_service.update_app(
            session,
            app_id=app_id,
            display_name=display_name if "display_name" in row else None,
            description=description if "description" in row else None,
            return_to=return_to if "return_to" in row else None,
        )


def _upsert_user(
    session: Session,
    row: dict[str, str],
    *,
    mode: str,
    password_already_hashed: bool,
) -> None:
    user_name = _get(row, "user_name")
    if not user_name:
        raise ValueError("users.csv: user_name is required")

    password = _get(row, "password")
    roles = _split_list(_get(row, "roles"))

    real_name = _get(row, "real_name")
    division = _get(row, "division")
    description = _get(row, "description")

    policy_epoch_raw = _get(row, "policy_epoch")
    policy_epoch = int(policy_epoch_raw) if policy_epoch_raw is not None else 1

    exists = session.get(UserOrm, user_name) is not None

    if mode == "create" and exists:
        raise ValueError(f"user already exists: {user_name}")

    if not exists:
        if not password:
            raise ValueError("users.csv: password is required for new users")
        user_service.create_user(
            session,
            UserDTOForCreate(
                user_name=user_name,
                password=password,
                roles=roles,
                real_name=real_name or "",
                division=division or "",
                description=description or "",
                policy_epoch=policy_epoch,
            ),
            already_hashed=password_already_hashed,
        )
        return

    # Update existing
    user_service.update_user(
        session,
        UserDTOForUpdate(
            user_name=user_name,
            password=password if "password" in row and password else None,
            roles=roles if "roles" in row else None,
            real_name=real_name if "real_name" in row else None,
            division=division if "division" in row else None,
            description=description if "description" in row else None,
        ),
        already_hashed=password_already_hashed,
    )


def _apply(
    session: Session,
    *,
    paths: CsvPaths,
    mode: str,
    password_already_hashed: bool,
) -> dict[str, int]:
    counts = {"roles": 0, "scopes": 0, "apps": 0, "users": 0}

    # Create roles/scopes first so later entities can reference them.
    if paths.roles is not None:
        for row in _read_csv_rows(paths.roles):
            _upsert_role(session, row, mode=mode)
            counts["roles"] += 1

    if paths.scopes is not None:
        for row in _read_csv_rows(paths.scopes):
            _upsert_scope(session, row, mode=mode)
            counts["scopes"] += 1

    if paths.apps is not None:
        for row in _read_csv_rows(paths.apps):
            _upsert_app(session, row, mode=mode)
            counts["apps"] += 1

    if paths.users is not None:
        for row in _read_csv_rows(paths.users):
            _upsert_user(session, row, mode=mode, password_already_hashed=password_already_hashed)
            counts["users"] += 1

    return counts


def _parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Bulk import ZenAuth data from CSV")
    p.add_argument(
        "--dsn",
        required=True,
        help="SQLAlchemy DSN (e.g. sqlite+pysqlite:////path/to/db.sqlite3)",
    )
    p.add_argument("--users", type=Path, help="Path to users.csv")
    p.add_argument("--apps", type=Path, help="Path to apps.csv")
    p.add_argument("--roles", type=Path, help="Path to roles.csv")
    p.add_argument("--scopes", type=Path, help="Path to scopes.csv")
    p.add_argument(
        "--mode",
        choices=["create", "upsert"],
        default="upsert",
        help="create: fail if exists, upsert: create or update (default)",
    )
    p.add_argument(
        "--password-already-hashed",
        action="store_true",
        help="Treat users.csv password as already hashed (bcrypt)",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv or sys.argv[1:])

    if not any((args.users, args.apps, args.roles, args.scopes)):
        raise SystemExit("Provide at least one of --users/--apps/--roles/--scopes")

    engine = create_engine_from_dsn(args.dsn)
    init_db(engine)
    session_factory = create_sessionmaker(engine)

    paths = CsvPaths(users=args.users, apps=args.apps, roles=args.roles, scopes=args.scopes)

    with session_scope(session_factory) as session:
        counts = _apply(
            session,
            paths=paths,
            mode=args.mode,
            password_already_hashed=args.password_already_hashed,
        )

    total = sum(counts.values())
    print(f"Imported rows: {counts} (total={total})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
