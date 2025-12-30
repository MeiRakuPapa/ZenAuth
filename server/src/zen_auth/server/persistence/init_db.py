from __future__ import annotations

import os

from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from zen_auth.logger import LOGGER

from ..usecases.user_service import pwd_ctx
from .base import Base
from .models import RoleOrm, UserOrm


def init_db(engine: Engine) -> None:
    """Create DB tables.

    Optionally bootstraps an initial admin user when enabled via env:
    - `ZENAUTH_SERVER_BOOTSTRAP_ADMIN=true`
    - `ZENAUTH_SERVER_BOOTSTRAP_ADMIN_USER=<user>`
    - `ZENAUTH_SERVER_BOOTSTRAP_ADMIN_PASSWORD=<password>`

    This is intended for development/demo use.
    """

    Base.metadata.create_all(bind=engine)

    # Optional bootstrap admin: opt-in via env vars.
    # We intentionally avoid loading ZenAuthServerConfig here, because init_db(engine)
    # is used in tests/tools that construct an Engine directly and shouldn't require DSN env.
    bootstrap = os.getenv("ZENAUTH_SERVER_BOOTSTRAP_ADMIN", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    if not bootstrap:
        return

    user_name = os.getenv("ZENAUTH_SERVER_BOOTSTRAP_ADMIN_USER", "").strip()
    password = os.getenv("ZENAUTH_SERVER_BOOTSTRAP_ADMIN_PASSWORD", "")
    if not user_name or not password.strip():
        LOGGER.warning(
            "Bootstrap admin enabled but missing env vars: ZENAUTH_SERVER_BOOTSTRAP_ADMIN_USER / ZENAUTH_SERVER_BOOTSTRAP_ADMIN_PASSWORD"
        )
        return

    with Session(engine) as session:
        with session.begin():
            admin = session.get(UserOrm, user_name)
            if admin is None:
                role = session.get(RoleOrm, "admin")
                if role is None:
                    role = RoleOrm(role_name="admin", display_name="Admin")
                    session.add(role)
                    session.flush()
                session.add(
                    UserOrm(
                        user_name=user_name,
                        password=pwd_ctx.hash(password),
                        roles=[role],
                        real_name="Administrator",
                        division="admin",
                        description="Bootstrapped admin account",
                    )
                )
                LOGGER.info("Bootstrapped admin account created")
