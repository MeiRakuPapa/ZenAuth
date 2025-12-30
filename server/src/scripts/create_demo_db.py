from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path
from typing import Any


def _bootstrap_sys_path() -> None:
    """Allow running this file directly without installing packages."""

    repo_root = Path(__file__).resolve().parents[3]
    for p in (repo_root / "core" / "src", repo_root / "server" / "src"):
        p_str = str(p)
        if p_str not in sys.path:
            sys.path.insert(0, p_str)


_bootstrap_sys_path()

_Faker: Any

try:
    from faker import Faker as _Faker
except Exception:  # pragma: no cover
    _Faker = None

from sqlalchemy import func, select  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402
from zen_auth.dto import (  # noqa: E402
    RoleDTOForCreate,
    ScopeDTOForCreate,
    UserDTOForCreate,
)
from zen_auth.server.persistence.base import Base  # noqa: E402
from zen_auth.server.persistence.init_db import init_db  # noqa: E402
from zen_auth.server.persistence.models import RoleOrm, ScopeOrm, UserOrm  # noqa: E402
from zen_auth.server.persistence.session import (  # noqa: E402
    create_engine_from_dsn,
    create_sessionmaker,
    session_scope,
)
from zen_auth.server.usecases import role_service, user_service  # noqa: E402


def _count(session: Session, model: type[Base]) -> int:
    return int(session.execute(select(func.count()).select_from(model)).scalar_one())


def _ensure_scope(
    session: Session, scope_name: str, *, display_name: str, description: str | None = None
) -> None:
    if session.get(ScopeOrm, scope_name) is not None:
        return
    from zen_auth.server.usecases import scope_service

    scope_service.create_scope(
        session,
        ScopeDTOForCreate(
            scope_name=scope_name,
            display_name=display_name,
            description=description,
            roles=[],
        ),
    )


def _ensure_role(
    session: Session, role_name: str, *, display_name: str, description: str | None = None
) -> None:
    if session.get(RoleOrm, role_name) is not None:
        return
    role_service.create_role(
        session,
        RoleDTOForCreate(role_name=role_name, display_name=display_name, description=description),
    )


def _ensure_user(
    session: Session,
    user_name: str,
    *,
    password: str,
    roles: list[str],
    real_name: str,
    division: str,
    description: str,
    policy_epoch: int = 1,
) -> None:
    if session.get(UserOrm, user_name) is not None:
        return
    user_service.create_user(
        session,
        UserDTOForCreate(
            user_name=user_name,
            password=password,
            roles=roles,
            real_name=real_name,
            division=division,
            description=description,
            policy_epoch=policy_epoch,
        ),
    )


def create_demo_db(
    db_path: str,
    *,
    user_target: int = 50,
    role_target: int = 10,
    scope_target: int = 10,
    seed: int = 42,
    reset: bool = False,
) -> None:
    """Create a demo sqlite DB with users/roles/scopes.

    Targets are *total counts* (including anything init_db already creates).
    The function is idempotent: rerunning tops up missing records.
    """

    db_file = Path(db_path)
    if reset and db_file.exists():
        db_file.unlink()

    db_file.parent.mkdir(parents=True, exist_ok=True)

    engine = create_engine_from_dsn(f"sqlite:///{db_file}")
    init_db(engine)
    session_factory = create_sessionmaker(engine)

    rng = random.Random(seed)

    fake: Any = _Faker() if _Faker is not None else None

    base_scopes: list[tuple[str, str]] = [
        ("read:users", "Read Users"),
        ("write:users", "Write Users"),
        ("read:roles", "Read Roles"),
        ("write:roles", "Write Roles"),
        ("read:scopes", "Read Scopes"),
        ("write:scopes", "Write Scopes"),
        ("read:settings", "Read Settings"),
        ("write:settings", "Write Settings"),
        ("read:audit", "Read Audit Logs"),
        ("write:audit", "Write Audit Logs"),
    ]

    base_roles: list[tuple[str, str]] = [
        ("admin", "Admin"),
        ("viewer", "Viewer"),
        ("editor", "Editor"),
        ("operator", "Operator"),
        ("auditor", "Auditor"),
        ("support", "Support"),
        ("hr", "HR"),
        ("finance", "Finance"),
        ("dev", "Developer"),
        ("qa", "QA"),
    ]

    with session_scope(session_factory) as session:
        # ---- Scopes ----
        for scope_name, display_name in base_scopes:
            _ensure_scope(session, scope_name, display_name=display_name)

        # Top-up additional scopes if requested target > base list.
        existing_scopes = _count(session, ScopeOrm)
        for i in range(max(0, scope_target - existing_scopes)):
            sn = f"custom:scope_{i + 1}"
            _ensure_scope(session, sn, display_name=f"Custom Scope {i + 1}")

        all_scope_names = [s.scope_name for s in session.scalars(select(ScopeOrm)).all()]

        # ---- Roles ----
        for role_name, display_name in base_roles:
            _ensure_role(session, role_name, display_name=display_name)

        existing_roles = _count(session, RoleOrm)
        for i in range(max(0, role_target - existing_roles)):
            rn = f"custom_role_{i + 1}"
            _ensure_role(session, rn, display_name=f"Custom Role {i + 1}")

        # Bind scopes to roles
        role_names = [r.role_name for r in session.scalars(select(RoleOrm)).all()]
        for rn in role_names:
            if rn == "admin":
                role_service.set_role_scopes(session, rn, sorted(all_scope_names))
                continue

            # Non-admin roles get 2-5 random scopes.
            k = rng.randint(2, min(5, len(all_scope_names)))
            role_service.set_role_scopes(session, rn, sorted(rng.sample(all_scope_names, k=k)))

        # ---- Users ----
        existing_users = _count(session, UserOrm)
        to_create = max(0, user_target - existing_users)

        non_admin_roles = [r for r in role_names if r != "admin"] or ["admin"]

        for idx in range(to_create):
            user_name = f"user_{existing_users + idx + 1:03d}"

            # Give 1-3 roles, biased to 1.
            role_k = 1 if rng.random() < 0.7 else (2 if rng.random() < 0.85 else 3)
            roles = sorted(rng.sample(non_admin_roles, k=min(role_k, len(non_admin_roles))))

            real_name = fake.name() if fake else f"Demo User {existing_users + idx + 1}"
            division = fake.company() if fake else "Demo Division"

            _ensure_user(
                session,
                user_name,
                password="password",
                roles=roles,
                real_name=real_name,
                division=division,
                description="demo account (password=password)",
                policy_epoch=1,
            )

        users_after = _count(session, UserOrm)
        roles_after = _count(session, RoleOrm)
        scopes_after = _count(session, ScopeOrm)

    try:
        engine.dispose()
    except Exception:
        pass

    print(f"DB: {db_file}")
    print(f"Users:  {users_after}")
    print(f"Roles:  {roles_after}")
    print(f"Scopes: {scopes_after}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create a ZenAuth demo sqlite DB with seeded users/roles/scopes"
    )
    parser.add_argument("--db-path", default="dummy_users.db", help="sqlite db file path")
    parser.add_argument("--users", type=int, default=50, help="target total users (including admin)")
    parser.add_argument("--roles", type=int, default=10, help="target total roles (including admin)")
    parser.add_argument("--scopes", type=int, default=10, help="target total scopes")
    parser.add_argument("--seed", type=int, default=42, help="random seed")
    parser.add_argument("--reset", action="store_true", help="delete db file before creating")
    args = parser.parse_args()

    create_demo_db(
        args.db_path,
        user_target=args.users,
        role_target=args.roles,
        scope_target=args.scopes,
        seed=args.seed,
        reset=args.reset,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
