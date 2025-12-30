from __future__ import annotations

import datetime as DT

from sqlalchemy import select
from sqlalchemy.orm import Session
from zen_auth.dto import RoleDTO, RoleDTOForCreate, RoleDTOForUpdate, ScopeDTO
from zen_auth.errors import RoleAlreadyExistsError, RoleNotFoundError

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


# ---- Role CRUD ----


def list_roles(session: Session) -> list[RoleDTO]:
    roles = session.scalars(select(RoleOrm).order_by(RoleOrm.role_name)).all()
    return [role_to_dto(r) for r in roles]


def get_role(session: Session, role_name: str) -> RoleDTO:
    role = session.get(RoleOrm, role_name)
    if role is None:
        raise RoleNotFoundError(f"Role not found: {role_name}", role_name=role_name)
    return role_to_dto(role)


def create_role(session: Session, role: RoleDTOForCreate) -> RoleDTO:
    if not role.role_name or role.role_name.strip() == "":
        raise ValueError("Role name cannot be empty or whitespace.")
    if session.get(RoleOrm, role.role_name) is not None:
        raise RoleAlreadyExistsError(f"Role already exists: {role.role_name}", role_name=role.role_name)

    obj = RoleOrm(role_name=role.role_name, display_name=role.display_name, description=role.description)
    session.add(obj)
    session.flush()
    return role_to_dto(obj)


def update_role(session: Session, role_name: str, patch: RoleDTOForUpdate) -> RoleDTO:
    obj = session.get(RoleOrm, role_name)
    if obj is None:
        raise RoleNotFoundError(f"Role not found: {role_name}", role_name=role_name)

    if patch.display_name is not None:
        obj.display_name = patch.display_name
    if patch.description is not None:
        obj.description = patch.description

    session.flush()
    return role_to_dto(obj)


def delete_role(session: Session, role_name: str) -> None:
    obj = session.get(RoleOrm, role_name)
    if obj is None:
        raise RoleNotFoundError(f"Role not found: {role_name}", role_name=role_name)

    # Clear associations first to avoid FK constraint errors.
    obj.users.clear()
    obj.scopes.clear()

    session.delete(obj)
    session.flush()


# ---- Role <-> Scope bindings ----


def _ensure_scopes(session: Session, scope_names: list[str]) -> list[ScopeOrm]:
    scopes: list[ScopeOrm] = []
    for sn in scope_names:
        scope = session.get(ScopeOrm, sn)
        if scope is None:
            scope = ScopeOrm(scope_name=sn, display_name=sn)
            session.add(scope)
            session.flush()
        scopes.append(scope)
    return scopes


def get_role_scopes(session: Session, role_name: str) -> list[ScopeDTO]:
    role = session.get(RoleOrm, role_name)
    if role is None:
        raise RoleNotFoundError(f"Role not found: {role_name}", role_name=role_name)
    return [scope_to_dto(s) for s in role.scopes]


def set_role_scopes(session: Session, role_name: str, scope_names: list[str]) -> list[ScopeDTO]:
    role = session.get(RoleOrm, role_name)
    if role is None:
        raise RoleNotFoundError(f"Role not found: {role_name}", role_name=role_name)

    role.scopes = _ensure_scopes(session, scope_names)
    session.flush()
    return [scope_to_dto(s) for s in role.scopes]
