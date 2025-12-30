from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Path, Request
from fastapi import status as http_status
from fastapi.responses import RedirectResponse, Response
from sqlalchemy.orm import Session
from zen_auth.claims.base import log_audit_fail, log_audit_success
from zen_auth.dto import UserDTO
from zen_auth.logger import LOGGER

from ....claims_self import ClaimsSelf
from ....persistence.models import ClientAppOrm
from ....persistence.session import get_session
from ....usecases import app_service
from .._tmp_lib import ErrorResponse, HResponse
from ..url_names import (
    ADM_APP_LIST_CONTENT,
    ADM_CREATE_APP_API,
    ADM_CREATE_APP_CONTENT,
    ADM_DELETE_APP_API,
    ADM_EDIT_APP_CONTENT,
    ADM_UPDATE_APP_API,
)
from .client_app_tmpl import ClientAppList, CreateClientAppDialog, EditClientAppDialog

router = APIRouter(prefix="/app", tags=["admin", "client_app"])


def _to_dict(obj: ClientAppOrm) -> dict[str, str | None]:
    return {
        "app_id": obj.app_id,
        "display_name": obj.display_name,
        "description": obj.description,
        "return_to": obj.return_to,
    }


@router.get("", name=ADM_APP_LIST_CONTENT)
def _app_list(
    req: Request,
    session: Session = Depends(get_session),
    user: UserDTO = Depends(ClaimsSelf.role_or_scope(roles=["admin"], scopes=["edit:auth_server"])),
) -> Response:
    _ = user
    apps = [_to_dict(a) for a in app_service.list_apps(session)]
    return HResponse(ClientAppList(apps, req=req))


@router.get("/create", name=ADM_CREATE_APP_CONTENT)
def _app_create_page(
    req: Request,
    user: UserDTO = Depends(ClaimsSelf.role_or_scope(roles=["admin"], scopes=["edit:auth_server"])),
) -> Response:
    _ = user
    return HResponse(CreateClientAppDialog(req=req))


@router.post("/create", name=ADM_CREATE_APP_API)
def _app_create(
    req: Request,
    app_id: str = Form(""),
    display_name: str = Form(""),
    description: str = Form(""),
    return_to: str = Form(""),
    session: Session = Depends(get_session),
    user: UserDTO = Depends(ClaimsSelf.role_or_scope(roles=["admin"], scopes=["edit:auth_server"])),
) -> Response:
    try:
        app_service.create_app(
            session,
            app_id=app_id,
            display_name=display_name or None,
            description=description or None,
            return_to=return_to,
        )
        log_audit_success(
            msg="create app success",
            user_name=user.user_name,
            roles=user.roles,
            required_context={"action": "create", "target": app_id},
            request=req,
        )
        return RedirectResponse(req.url_for(ADM_APP_LIST_CONTENT), status_code=http_status.HTTP_303_SEE_OTHER)
    except ValueError as e:
        msg = str(e)
        if msg == "app already exists":
            log_audit_fail(
                msg="create app failed (already exists)",
                user_name=user.user_name,
                roles=user.roles,
                required_context={"action": "create", "target": app_id},
                request=req,
            )
            return ErrorResponse("App already exists.", http_status.HTTP_409_CONFLICT)
        log_audit_fail(
            msg=f"create app failed (value error): {msg}",
            user_name=user.user_name,
            roles=user.roles,
            required_context={"action": "create", "target": app_id},
            request=req,
        )
        return ErrorResponse(msg, http_status.HTTP_400_BAD_REQUEST)
    except Exception:
        LOGGER.exception("Create app error: %s", app_id)
        log_audit_fail(
            msg="create app failed (exception)",
            user_name=user.user_name,
            roles=user.roles,
            required_context={"action": "create", "target": app_id},
            request=req,
        )
        return ErrorResponse("Failed to create app.", http_status.HTTP_500_INTERNAL_SERVER_ERROR)


@router.get("/edit/{app_id}", name=ADM_EDIT_APP_CONTENT)
def _app_edit_page(
    req: Request,
    app_id: str = Path(min_length=1, max_length=255),
    session: Session = Depends(get_session),
    user: UserDTO = Depends(ClaimsSelf.role_or_scope(roles=["admin"], scopes=["edit:auth_server"])),
) -> Response:
    _ = user
    obj = app_service.get_app(session, app_id)
    if obj is None:
        return ErrorResponse("App not found.", http_status.HTTP_404_NOT_FOUND)
    return HResponse(EditClientAppDialog(req=req, app=_to_dict(obj)))


@router.post("/update", name=ADM_UPDATE_APP_API)
def _app_update(
    req: Request,
    app_id: str = Form(""),
    display_name: str = Form(""),
    description: str = Form(""),
    return_to: str = Form(""),
    session: Session = Depends(get_session),
    user: UserDTO = Depends(ClaimsSelf.role_or_scope(roles=["admin"], scopes=["edit:auth_server"])),
) -> Response:
    try:
        app_service.update_app(
            session,
            app_id=app_id,
            display_name=display_name,
            description=description,
            return_to=return_to,
        )
        log_audit_success(
            msg="update app success",
            user_name=user.user_name,
            roles=user.roles,
            required_context={"action": "update", "target": app_id},
            request=req,
        )
        return RedirectResponse(req.url_for(ADM_APP_LIST_CONTENT), status_code=http_status.HTTP_303_SEE_OTHER)
    except ValueError as e:
        msg = str(e)
        if msg == "app not found":
            log_audit_fail(
                msg="update app failed (not found)",
                user_name=user.user_name,
                roles=user.roles,
                required_context={"action": "update", "target": app_id},
                request=req,
            )
            return ErrorResponse("App not found.", http_status.HTTP_404_NOT_FOUND)
        log_audit_fail(
            msg=f"update app failed (value error): {msg}",
            user_name=user.user_name,
            roles=user.roles,
            required_context={"action": "update", "target": app_id},
            request=req,
        )
        return ErrorResponse(msg, http_status.HTTP_400_BAD_REQUEST)
    except Exception:
        LOGGER.exception("Update app error: %s", app_id)
        log_audit_fail(
            msg="update app failed (exception)",
            user_name=user.user_name,
            roles=user.roles,
            required_context={"action": "update", "target": app_id},
            request=req,
        )
        return ErrorResponse("Failed to update app.", http_status.HTTP_500_INTERNAL_SERVER_ERROR)


@router.delete("/delete/{app_id}", name=ADM_DELETE_APP_API)
def _app_delete(
    req: Request,
    app_id: str = Path(min_length=1, max_length=255),
    session: Session = Depends(get_session),
    user: UserDTO = Depends(ClaimsSelf.role_or_scope(roles=["admin"], scopes=["edit:auth_server"])),
) -> Response:
    _ = req
    try:
        app_service.delete_app(session, app_id)
        log_audit_success(
            msg="delete app success",
            user_name=user.user_name,
            roles=user.roles,
            required_context={"action": "delete", "target": app_id},
            request=req,
        )
        return Response(status_code=http_status.HTTP_204_NO_CONTENT)
    except ValueError:
        log_audit_fail(
            msg="delete app failed (not found)",
            user_name=user.user_name,
            roles=user.roles,
            required_context={"action": "delete", "target": app_id},
            request=req,
        )
        return ErrorResponse("App not found.", http_status.HTTP_404_NOT_FOUND)
