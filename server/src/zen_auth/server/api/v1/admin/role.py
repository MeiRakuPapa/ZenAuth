from __future__ import annotations

import re
from typing import Any

from fastapi import APIRouter, Depends, Form, Path, Request, status
from fastapi.responses import RedirectResponse, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from zen_auth.claims.base import log_audit_fail, log_audit_success
from zen_auth.dto import RoleDTO, RoleDTOForCreate, RoleDTOForUpdate, UserDTO
from zen_auth.errors import RoleAlreadyExistsError, RoleNotFoundError
from zen_auth.logger import LOGGER

from ....claims_self import ClaimsSelf
from ....persistence.models import RoleOrm, role_scopes, user_roles
from ....persistence.session import get_session
from ....usecases import role_service
from .._tmp_lib import ErrorResponse, HResponse
from ..url_names import (
    ADM_CREATE_ROLE_API,
    ADM_CREATE_ROLE_CONTENT,
    ADM_DELETE_ROLE_API,
    ADM_EDIT_ROLE_CONTENT,
    ADM_ROLE_LIST_CONTENT,
    ADM_UPDATE_ROLE_API,
)
from .role_tmpl import CreateRoleDialog
from .role_tmpl import EditRoleDialog as _EditRoleDialog
from .role_tmpl import RoleList as _RoleList

RoleList: Any = _RoleList
EditRoleDialog: Any = _EditRoleDialog


router = APIRouter(prefix="/role", tags=["admin", "role"])

_VALID_NAME = re.compile(r"^[a-zA-Z0-9:_\-\.]+$")


def _role_user_counts(session: Session) -> dict[str, int]:
    rows = session.execute(
        select(user_roles.c.role_name, func.count(user_roles.c.user_name)).group_by(user_roles.c.role_name)
    ).all()
    return {role_name: int(cnt) for role_name, cnt in rows}


def _role_scope_counts(session: Session) -> dict[str, int]:
    rows = session.execute(
        select(role_scopes.c.role_name, func.count(role_scopes.c.scope_name)).group_by(
            role_scopes.c.role_name
        )
    ).all()
    return {role_name: int(cnt) for role_name, cnt in rows}


@router.get("", name=ADM_ROLE_LIST_CONTENT)
def _role_list(
    req: Request,
    session: Session = Depends(get_session),
    user: UserDTO = Depends(ClaimsSelf.role_or_scope(roles=["admin"], scopes=["edit:auth_server"])),
) -> Response:
    roles = role_service.list_roles(session)
    return HResponse(
        RoleList(
            roles,
            req=req,
            user_counts=_role_user_counts(session),
            scope_counts=_role_scope_counts(session),
        )
    )


@router.get("/create", name=ADM_CREATE_ROLE_CONTENT)
def _role_create_page(
    req: Request,
    user: UserDTO = Depends(ClaimsSelf.role_or_scope(roles=["admin"], scopes=["edit:auth_server"])),
) -> Response:
    return HResponse(CreateRoleDialog(req=req))


@router.post("/create", name=ADM_CREATE_ROLE_API)
def _role_create(
    req: Request,
    role_name: str = Form(""),
    display_name: str = Form(""),
    description: str = Form(""),
    session: Session = Depends(get_session),
    user: UserDTO = Depends(ClaimsSelf.role_or_scope(roles=["admin"], scopes=["edit:auth_server"])),
) -> Response:
    if not role_name or not _VALID_NAME.match(role_name):
        log_audit_fail(
            msg="create role failed (validation)",
            user_name=user.user_name,
            roles=user.roles,
            required_context={"action": "create", "target": role_name},
            request=req,
        )
        return ErrorResponse("Invalid role name.")
    if not display_name:
        display_name = role_name

    try:
        role_service.create_role(
            session,
            RoleDTOForCreate(
                role_name=role_name, display_name=display_name, description=(description or None)
            ),
        )
        log_audit_success(
            msg="create role success",
            user_name=user.user_name,
            roles=user.roles,
            required_context={"action": "create", "target": role_name},
            request=req,
        )
        return RedirectResponse(req.url_for(ADM_ROLE_LIST_CONTENT), status_code=status.HTTP_303_SEE_OTHER)
    except RoleAlreadyExistsError:
        log_audit_fail(
            msg="create role failed (already exists)",
            user_name=user.user_name,
            roles=user.roles,
            required_context={"action": "create", "target": role_name},
            request=req,
        )
        return ErrorResponse("Role already exists.", status.HTTP_409_CONFLICT)
    except ValueError as e:
        log_audit_fail(
            msg=f"create role failed (value error): {e}",
            user_name=user.user_name,
            roles=user.roles,
            required_context={"action": "create", "target": role_name},
            request=req,
        )
        return ErrorResponse(str(e), status.HTTP_400_BAD_REQUEST)
    except Exception:
        LOGGER.exception("Create role error: %s", role_name)
        log_audit_fail(
            msg="create role failed (exception)",
            user_name=user.user_name,
            roles=user.roles,
            required_context={"action": "create", "target": role_name},
            request=req,
        )
        return ErrorResponse("Failed to create role.", status.HTTP_500_INTERNAL_SERVER_ERROR)


@router.get("/edit/{role_name}", name=ADM_EDIT_ROLE_CONTENT)
def _role_edit_page(
    req: Request,
    role_name: str = Path(min_length=1, max_length=255),
    session: Session = Depends(get_session),
    user: UserDTO = Depends(ClaimsSelf.role_or_scope(roles=["admin"], scopes=["edit:auth_server"])),
) -> Response:
    try:
        role: RoleDTO = role_service.get_role(session, role_name)
        user_count = _role_user_counts(session).get(role_name, 0)
        scope_count = _role_scope_counts(session).get(role_name, 0)

        role_obj = session.get(RoleOrm, role_name)
        if role_obj is None:
            raise RoleNotFoundError("Role not found", role_name=role_name)

        users = sorted([u.user_name for u in role_obj.users])
        scopes = sorted(
            [
                (s.display_name if s.display_name and s.display_name != s.scope_name else s.scope_name)
                for s in role_obj.scopes
            ]
        )
        return HResponse(
            EditRoleDialog(
                req=req,
                role=role,
                user_count=user_count,
                scope_count=scope_count,
                users=users,
                scopes=scopes,
            )
        )
    except RoleNotFoundError:
        return ErrorResponse("Role not found.", status.HTTP_404_NOT_FOUND)


@router.post("/update", name=ADM_UPDATE_ROLE_API)
def _role_update(
    req: Request,
    role_name: str = Form(""),
    display_name: str = Form(""),
    description: str = Form(""),
    session: Session = Depends(get_session),
    user: UserDTO = Depends(ClaimsSelf.role_or_scope(roles=["admin"], scopes=["edit:auth_server"])),
) -> Response:
    try:
        role_service.update_role(
            session,
            role_name,
            RoleDTOForUpdate(display_name=(display_name or None), description=(description or None)),
        )
        log_audit_success(
            msg="update role success",
            user_name=user.user_name,
            roles=user.roles,
            required_context={"action": "update", "target": role_name},
            request=req,
        )
        return RedirectResponse(req.url_for(ADM_ROLE_LIST_CONTENT), status_code=status.HTTP_303_SEE_OTHER)
    except RoleNotFoundError:
        log_audit_fail(
            msg="update role failed (not found)",
            user_name=user.user_name,
            roles=user.roles,
            required_context={"action": "update", "target": role_name},
            request=req,
        )
        return ErrorResponse("Role not found.", status.HTTP_404_NOT_FOUND)
    except ValueError as e:
        log_audit_fail(
            msg=f"update role failed (value error): {e}",
            user_name=user.user_name,
            roles=user.roles,
            required_context={"action": "update", "target": role_name},
            request=req,
        )
        return ErrorResponse(str(e), status.HTTP_400_BAD_REQUEST)
    except Exception:
        LOGGER.exception("Update role error: %s", role_name)
        log_audit_fail(
            msg="update role failed (exception)",
            user_name=user.user_name,
            roles=user.roles,
            required_context={"action": "update", "target": role_name},
            request=req,
        )
        return ErrorResponse("Failed to update role.", status.HTTP_500_INTERNAL_SERVER_ERROR)


@router.delete("/delete/{role_name}", name=ADM_DELETE_ROLE_API)
def _role_delete(
    req: Request,
    role_name: str = Path(min_length=1, max_length=255),
    session: Session = Depends(get_session),
    user: UserDTO = Depends(ClaimsSelf.role_or_scope(roles=["admin"], scopes=["edit:auth_server"])),
) -> Response:
    _ = req
    try:
        role_service.delete_role(session, role_name)
        log_audit_success(
            msg="delete role success",
            user_name=user.user_name,
            roles=user.roles,
            required_context={"action": "delete", "target": role_name},
            request=req,
        )
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except RoleNotFoundError:
        log_audit_fail(
            msg="delete role failed (not found)",
            user_name=user.user_name,
            roles=user.roles,
            required_context={"action": "delete", "target": role_name},
            request=req,
        )
        return ErrorResponse("Role not found.", status.HTTP_404_NOT_FOUND)
