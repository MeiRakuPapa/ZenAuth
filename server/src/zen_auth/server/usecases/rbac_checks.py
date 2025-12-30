from __future__ import annotations

from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..persistence.models import role_scopes, user_roles


def user_has_role(session: Session, user_name: str, role_name: str) -> bool:
    stmt = (
        select(1)
        .select_from(user_roles)
        .where(user_roles.c.user_name == user_name, user_roles.c.role_name == role_name)
        .limit(1)
    )
    return session.execute(stmt).first() is not None


def user_allowed_scope(session: Session, user_name: str, scope_name: str) -> bool:
    stmt = (
        select(1)
        .select_from(user_roles.join(role_scopes, user_roles.c.role_name == role_scopes.c.role_name))
        .where(user_roles.c.user_name == user_name, role_scopes.c.scope_name == scope_name)
        .limit(1)
    )
    return session.execute(stmt).first() is not None


def user_allowed_scopes(session: Session, user_name: str) -> set[str]:
    stmt = (
        select(role_scopes.c.scope_name)
        .distinct()
        .select_from(user_roles.join(role_scopes, user_roles.c.role_name == role_scopes.c.role_name))
        .where(user_roles.c.user_name == user_name)
    )
    return set(session.scalars(stmt).all())


def has_required_roles(user_roles: Iterable[str], required_roles: Iterable[str]) -> bool:
    roles = set(user_roles)
    required = set(required_roles)
    return bool(roles & required)


def has_required_scopes(session: Session, user_name: str, required_scopes: Iterable[str]) -> bool:
    allowed = user_allowed_scopes(session, user_name)
    required = set(required_scopes)
    return bool(allowed & required)
