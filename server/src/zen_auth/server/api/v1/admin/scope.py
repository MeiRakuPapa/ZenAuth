import re

from fastapi import APIRouter, Depends, Form, Path, Request, status
from fastapi.responses import RedirectResponse, Response
from sqlalchemy.orm import Session
from zen_auth.claims.base import log_audit_fail, log_audit_success
from zen_auth.dto import ScopeDTO, ScopeDTOForCreate, ScopeDTOForUpdate, UserDTO
from zen_auth.errors import ScopeAlreadyExistsError, ScopeNotFoundError
from zen_auth.logger import LOGGER

from ....claims_self import ClaimsSelf
from ....persistence.session import get_session
from ....usecases import role_service, scope_service
from .._tmp_lib import ErrorResponse, HResponse
from ..url_names import (
    ADM_CREATE_SCOPE_API,
    ADM_CREATE_SCOPE_CONTENT,
    ADM_DELETE_SCOPE_API,
    ADM_EDIT_SCOPE_CONTENT,
    ADM_SCOPE_LIST_CONTENT,
    ADM_UPDATE_SCOPE_API,
)
from .scope_tmpl import CreateScopeDialog, EditScopeDialog, ScopeList

router = APIRouter(prefix="/scope", tags=["admin", "scope"])

_VALID_NAME = re.compile(r"^[a-zA-Z0-9:_\-\.]+$")


def _role_map(session: Session) -> dict[str, str]:
    roles = role_service.list_roles(session)
    return {r.role_name: (r.display_name or r.role_name) for r in roles}


@router.get("", name=ADM_SCOPE_LIST_CONTENT)
def _scope_list(
    req: Request,
    session: Session = Depends(get_session),
    user: UserDTO = Depends(ClaimsSelf.role_or_scope(roles=["admin"], scopes=["edit:auth_server"])),
) -> Response:
    scopes = scope_service.list_scopes(session)
    return HResponse(ScopeList(scopes, req=req, role_map=_role_map(session)))


@router.get("/create", name=ADM_CREATE_SCOPE_CONTENT)
def _scope_create_page(
    req: Request,
    session: Session = Depends(get_session),
    user: UserDTO = Depends(ClaimsSelf.role_or_scope(roles=["admin"], scopes=["edit:auth_server"])),
) -> Response:
    return HResponse(CreateScopeDialog(req=req, role_map=_role_map(session)))


@router.post("/create", name=ADM_CREATE_SCOPE_API)
def _scope_create(
    req: Request,
    scope_name: str = Form(""),
    display_name: str = Form(""),
    description: str = Form(""),
    roles: list[str] = Form(default_factory=list),
    session: Session = Depends(get_session),
    user: UserDTO = Depends(ClaimsSelf.role_or_scope(roles=["admin"], scopes=["edit:auth_server"])),
) -> Response:
    if not scope_name or not _VALID_NAME.match(scope_name):
        log_audit_fail(
            msg="create scope failed (validation)",
            user_name=user.user_name,
            roles=user.roles,
            required_context={"action": "create", "target": scope_name},
            request=req,
        )
        return ErrorResponse("Invalid scope name.")
    if not display_name:
        display_name = scope_name

    try:
        scope_service.create_scope(
            session,
            ScopeDTOForCreate(
                scope_name=scope_name,
                display_name=display_name,
                description=(description or None),
                roles=roles,
            ),
        )
        log_audit_success(
            msg="create scope success",
            user_name=user.user_name,
            roles=user.roles,
            required_context={"action": "create", "target": scope_name},
            request=req,
        )
        return RedirectResponse(req.url_for(ADM_SCOPE_LIST_CONTENT), status_code=status.HTTP_303_SEE_OTHER)
    except ScopeAlreadyExistsError:
        log_audit_fail(
            msg="create scope failed (already exists)",
            user_name=user.user_name,
            roles=user.roles,
            required_context={"action": "create", "target": scope_name},
            request=req,
        )
        return ErrorResponse("Scope already exists.", status.HTTP_409_CONFLICT)
    except ValueError as e:
        log_audit_fail(
            msg=f"create scope failed (value error): {e}",
            user_name=user.user_name,
            roles=user.roles,
            required_context={"action": "create", "target": scope_name},
            request=req,
        )
        return ErrorResponse(str(e), status.HTTP_400_BAD_REQUEST)
    except Exception:
        LOGGER.exception("Create scope error: %s", scope_name)
        log_audit_fail(
            msg="create scope failed (exception)",
            user_name=user.user_name,
            roles=user.roles,
            required_context={"action": "create", "target": scope_name},
            request=req,
        )
        return ErrorResponse("Failed to create scope.", status.HTTP_500_INTERNAL_SERVER_ERROR)


@router.get("/edit/{scope_name}", name=ADM_EDIT_SCOPE_CONTENT)
def _scope_edit_page(
    req: Request,
    scope_name: str = Path(min_length=1, max_length=255),
    session: Session = Depends(get_session),
    user: UserDTO = Depends(ClaimsSelf.role_or_scope(roles=["admin"], scopes=["edit:auth_server"])),
) -> Response:
    try:
        scope: ScopeDTO = scope_service.get_scope(session, scope_name)
        return HResponse(EditScopeDialog(req=req, scope=scope, role_map=_role_map(session)))
    except ScopeNotFoundError:
        return ErrorResponse("Scope not found.", status.HTTP_404_NOT_FOUND)


@router.post("/update", name=ADM_UPDATE_SCOPE_API)
def _scope_update(
    req: Request,
    scope_name: str = Form(""),
    display_name: str = Form(""),
    description: str = Form(""),
    roles: list[str] = Form(default_factory=list),
    session: Session = Depends(get_session),
    user: UserDTO = Depends(ClaimsSelf.role_or_scope(roles=["admin"], scopes=["edit:auth_server"])),
) -> Response:
    try:
        scope_service.update_scope(
            session,
            scope_name,
            ScopeDTOForUpdate(
                display_name=(display_name or None),
                description=(description or None),
                roles=roles,
            ),
        )
        log_audit_success(
            msg="update scope success",
            user_name=user.user_name,
            roles=user.roles,
            required_context={"action": "update", "target": scope_name},
            request=req,
        )
        return RedirectResponse(req.url_for(ADM_SCOPE_LIST_CONTENT), status_code=status.HTTP_303_SEE_OTHER)
    except ScopeNotFoundError:
        log_audit_fail(
            msg="update scope failed (not found)",
            user_name=user.user_name,
            roles=user.roles,
            required_context={"action": "update", "target": scope_name},
            request=req,
        )
        return ErrorResponse("Scope not found.", status.HTTP_404_NOT_FOUND)
    except ValueError as e:
        log_audit_fail(
            msg=f"update scope failed (value error): {e}",
            user_name=user.user_name,
            roles=user.roles,
            required_context={"action": "update", "target": scope_name},
            request=req,
        )
        return ErrorResponse(str(e), status.HTTP_400_BAD_REQUEST)
    except Exception:
        LOGGER.exception("Update scope error: %s", scope_name)
        log_audit_fail(
            msg="update scope failed (exception)",
            user_name=user.user_name,
            roles=user.roles,
            required_context={"action": "update", "target": scope_name},
            request=req,
        )
        return ErrorResponse("Failed to update scope.", status.HTTP_500_INTERNAL_SERVER_ERROR)


@router.delete("/delete/{scope_name}", name=ADM_DELETE_SCOPE_API)
def _scope_delete(
    req: Request,
    scope_name: str = Path(min_length=1, max_length=255),
    session: Session = Depends(get_session),
    user: UserDTO = Depends(ClaimsSelf.role_or_scope(roles=["admin"], scopes=["edit:auth_server"])),
) -> Response:
    _ = req
    try:
        scope_service.delete_scope(session, scope_name)
        log_audit_success(
            msg="delete scope success",
            user_name=user.user_name,
            roles=user.roles,
            required_context={"action": "delete", "target": scope_name},
            request=req,
        )
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except ScopeNotFoundError:
        log_audit_fail(
            msg="delete scope failed (not found)",
            user_name=user.user_name,
            roles=user.roles,
            required_context={"action": "delete", "target": scope_name},
            request=req,
        )
        return ErrorResponse("Scope not found.", status.HTTP_404_NOT_FOUND)
