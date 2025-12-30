from __future__ import annotations

import datetime as DT

from sqlalchemy import select
from sqlalchemy.orm import Session
from zen_auth.dto import RoleDTO, ScopeDTO, ScopeDTOForCreate, ScopeDTOForUpdate
from zen_auth.errors import ScopeAlreadyExistsError, ScopeNotFoundError

from ..persistence.models import RoleOrm, ScopeOrm


def _iso(dt: DT.datetime | None) -> str | None:
    return dt.isoformat() if dt is not None else None


def role_to_dto(role: RoleOrm) -> RoleDTO:
    return RoleDTO(
        role_name=role.role_name,
        display_name=role.display_name,
        description=role.description,
        created_at=_iso(role.created_at),
        updated_at=_iso(role.updated_at),
    )


def scope_to_dto(scope: ScopeOrm) -> ScopeDTO:
    return ScopeDTO(
        scope_name=scope.scope_name,
        display_name=scope.display_name,
        description=scope.description,
        roles=[r.role_name for r in scope.roles],
        created_at=_iso(scope.created_at),
        updated_at=_iso(scope.updated_at),
    )


# ---- Scope CRUD ----


def list_scopes(session: Session) -> list[ScopeDTO]:
    scopes = session.scalars(select(ScopeOrm).order_by(ScopeOrm.scope_name)).all()
    return [scope_to_dto(s) for s in scopes]


def get_scope(session: Session, scope_name: str) -> ScopeDTO:
    scope = session.get(ScopeOrm, scope_name)
    if scope is None:
        raise ScopeNotFoundError(f"Scope not found: {scope_name}", scope_name=scope_name)
    return scope_to_dto(scope)


def _ensure_roles(session: Session, role_names: list[str]) -> list[RoleOrm]:
    roles: list[RoleOrm] = []
    for rn in role_names:
        role = session.get(RoleOrm, rn)
        if role is None:
            role = RoleOrm(role_name=rn, display_name=rn)
            session.add(role)
            session.flush()
        roles.append(role)
    return roles


def create_scope(session: Session, scope: ScopeDTOForCreate) -> ScopeDTO:
    if not scope.scope_name or scope.scope_name.strip() == "":
        raise ValueError("Scope name cannot be empty or whitespace.")
    if session.get(ScopeOrm, scope.scope_name) is not None:
        raise ScopeAlreadyExistsError(
            f"Scope already exists: {scope.scope_name}",
            scope_name=scope.scope_name,
        )

    obj = ScopeOrm(
        scope_name=scope.scope_name, display_name=scope.display_name, description=scope.description
    )
    session.add(obj)
    session.flush()

    # Optional initial role bindings
    if scope.roles:
        obj.roles = _ensure_roles(session, scope.roles)
        session.flush()

    return scope_to_dto(obj)


def update_scope(session: Session, scope_name: str, patch: ScopeDTOForUpdate) -> ScopeDTO:
    obj = session.get(ScopeOrm, scope_name)
    if obj is None:
        raise ScopeNotFoundError(f"Scope not found: {scope_name}", scope_name=scope_name)

    if patch.display_name is not None:
        obj.display_name = patch.display_name
    if patch.description is not None:
        obj.description = patch.description
    if patch.roles is not None:
        obj.roles = _ensure_roles(session, patch.roles)

    session.flush()
    return scope_to_dto(obj)


def delete_scope(session: Session, scope_name: str) -> None:
    obj = session.get(ScopeOrm, scope_name)
    if obj is None:
        raise ScopeNotFoundError(f"Scope not found: {scope_name}", scope_name=scope_name)

    obj.roles.clear()
    session.delete(obj)
    session.flush()
