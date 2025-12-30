import json
import re

from fastapi import Depends, Form, Path, Query, Request, status
from fastapi.responses import RedirectResponse, Response
from sqlalchemy.orm import Session
from zen_auth.claims.base import log_audit_fail, log_audit_success
from zen_auth.dto import UserDTO, UserDTOForCreate, UserDTOForUpdate
from zen_auth.errors import UserAlreadyExistsError, UserNotFoundError
from zen_auth.logger import LOGGER

from ....claims_self import ClaimsSelf
from ....persistence.session import get_session
from ....usecases import role_service, user_service
from ...util.router_factory import APIRouterFactory
from .._tmp_lib import ErrorResponse, HResponse, SuccessResponse
from ..ui_ids import ADM_CHANGE_PW_ID, ADM_CREATE_USER_ID, ADM_EDIT_USER_ID
from ..url_names import (
    ADM_CHANGE_PW_API,
    ADM_CHANGE_PW_CONTENT,
    ADM_CREATE_USER_API,
    ADM_CREATE_USER_CONTENT,
    ADM_DELETE_USER_API,
    ADM_EDIT_USER_CONTENT,
    ADM_UPDATE_USER_API,
    ADM_USER_LIST_CONTENT,
)
from .user_tmpl import (
    ChangePasswordAdminDialog,
    CreateUserDialog,
    EditUserDialog,
    UserList,
)

router = APIRouterFactory(tags=["admin", "user"])


PAGE_SIZE = 20
PW_LEN = 10
STRONG_PW = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).+$")


def _role_map(session: Session) -> dict[str, str]:
    roles = role_service.list_roles(session)
    return {r.role_name: (r.display_name or r.role_name) for r in roles}


@router.get("", name=ADM_USER_LIST_CONTENT)
def _user_list_page(
    req: Request,
    page: int = Query(1, ge=1),
    session: Session = Depends(get_session),
    user: UserDTO = Depends(ClaimsSelf.role_or_scope(roles=["admin"], scopes=["edit:auth_server"])),
) -> Response:
    num_pages, user_list = user_service.list_users_page(session, page, page_size=PAGE_SIZE)
    role_map = _role_map(session)

    x = list(user_list)
    x.sort(key=lambda u: u.user_name)

    if num_pages < page:
        return RedirectResponse(
            url=str(req.url_for(ADM_USER_LIST_CONTENT)) + f"?page={num_pages}",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    return HResponse(UserList(x, req=req, page=page, num_pages=num_pages, role_map=role_map))


@router.get("/create", name=ADM_CREATE_USER_CONTENT)
def _create_user_page(
    req: Request,
    token: str | None = Query(None),
    session: Session = Depends(get_session),
    user: UserDTO = Depends(ClaimsSelf.role_or_scope(roles=["admin"], scopes=["edit:auth_server"])),
) -> Response:
    _ = token
    return HResponse(CreateUserDialog(role_map=_role_map(session), dialog_id=ADM_CREATE_USER_ID, req=req))


@router.post("/create", name=ADM_CREATE_USER_API)
def _create_user(
    req: Request,
    user_name: str = Form(""),
    real_name: str = Form(""),
    description: str = Form(""),
    division: str = Form(""),
    roles: str = Form(""),
    password: str = Form(""),
    confirm_password: str = Form(""),
    session: Session = Depends(get_session),
    user: UserDTO = Depends(ClaimsSelf.role_or_scope(roles=["admin"], scopes=["edit:auth_server"])),
) -> Response:
    _roles: list[str] = [r["value"] if isinstance(r, dict) else r for r in json.loads(roles)] if roles else []

    errors: list[str] = []
    if not _roles:
        errors.append("No roles specified.")
    if user_name == "":
        errors.append("Username is required.")
    if division == "":
        errors.append("Division is required.")
    if password != confirm_password:
        errors.append("Passwords do not match.")
    if len(password) < PW_LEN:
        errors.append(f"Password must be at least {PW_LEN} characters long.")
    if not STRONG_PW.match(password):
        errors.append("Password must include uppercase, lowercase, and numbers.")

    cu = UserDTOForCreate(
        user_name=user_name,
        password=password,
        real_name=real_name,
        division=division,
        description=description,
        roles=_roles,
    )

    if errors:
        log_audit_fail(
            msg="create user failed (validation)",
            user_name=user.user_name,
            roles=user.roles,
            required_context={"action": "create", "target": user_name},
            request=req,
        )
        return ErrorResponse(errors)

    try:
        user_service.create_user(session, cu)
        list_url = req.url_for(ADM_USER_LIST_CONTENT)
        log_audit_success(
            msg="create user success",
            user_name=user.user_name,
            roles=user.roles,
            required_context={"action": "create", "target": user_name},
            request=req,
        )
        LOGGER.debug("create user %s success. redirect to: %s", user_name, list_url)
        return RedirectResponse(list_url, status_code=status.HTTP_303_SEE_OTHER)
    except UserAlreadyExistsError:
        log_audit_fail(
            msg="create user failed (already exists)",
            user_name=user.user_name,
            roles=user.roles,
            required_context={"action": "create", "target": user_name},
            request=req,
        )
        return ErrorResponse("User already exists.", status.HTTP_409_CONFLICT)
    except ValueError as e:
        log_audit_fail(
            msg=f"create user failed (value error): {e}",
            user_name=user.user_name,
            roles=user.roles,
            required_context={"action": "create", "target": user_name},
            request=req,
        )
        return ErrorResponse(str(e), status.HTTP_400_BAD_REQUEST)
    except Exception:
        LOGGER.exception("Create user error: %s", user_name)
        log_audit_fail(
            msg="create user failed (exception)",
            user_name=user.user_name,
            roles=user.roles,
            required_context={"action": "create", "target": user_name},
            request=req,
        )
        return ErrorResponse("Failed to create user.", status.HTTP_500_INTERNAL_SERVER_ERROR)


@router.get("/edit/{user_name}", name=ADM_EDIT_USER_CONTENT)
def _update_user_page(
    req: Request,
    user_name: str = Path(min_length=1, max_length=10),
    page: int = Query(1),
    session: Session = Depends(get_session),
    user: UserDTO = Depends(ClaimsSelf.role_or_scope(roles=["admin"], scopes=["edit:auth_server"])),
) -> Response:
    try:
        user = user_service.get_user(session, user_name)
    except UserNotFoundError:
        LOGGER.debug("User not found when opening edit page: %s", user_name, exc_info=True)
        return ErrorResponse(f"User not found: {user_name}", status.HTTP_404_NOT_FOUND)

    return HResponse(
        EditUserDialog(
            req=req,
            user=user,
            role_map=_role_map(session),
            dialog_id=ADM_EDIT_USER_ID,
            page=page,
        )
    )


@router.post("/update", name=ADM_UPDATE_USER_API)
def _update_user(
    req: Request,
    user_name: str = Form(""),
    real_name: str = Form(""),
    description: str = Form(""),
    division: str = Form(""),
    roles: list[str] = Form(default_factory=list),
    page: int = Query(1),
    session: Session = Depends(get_session),
    user: UserDTO = Depends(ClaimsSelf.role_or_scope(roles=["admin"], scopes=["edit:auth_server"])),
) -> Response:
    try:
        errors: list[str] = []
        if not roles:
            errors.append("No roles specified.")
        if not user_name:
            errors.append("Username is required.")
        if not division:
            errors.append("Division is required.")

        if errors:
            log_audit_fail(
                msg="update user failed (validation)",
                user_name=user.user_name,
                roles=user.roles,
                required_context={"action": "update", "target": user_name},
                request=req,
            )
            return ErrorResponse(errors)

        _user = UserDTOForUpdate(
            user_name=user_name,
            roles=roles,
            real_name=real_name,
            description=description,
            division=division,
        )
        user_service.update_user(session, _user)
        list_url = req.url_for(ADM_USER_LIST_CONTENT).include_query_params(page=page)
        log_audit_success(
            msg="update user success",
            user_name=user.user_name,
            roles=user.roles,
            required_context={"action": "update", "target": user_name},
            request=req,
        )
        LOGGER.debug("update user %s success. redirect to: %s", user_name, list_url)
        return RedirectResponse(list_url, status_code=status.HTTP_303_SEE_OTHER)
    except UserNotFoundError:
        LOGGER.debug("Update failed - user not found: %s", user_name, exc_info=True)
        log_audit_fail(
            msg="update user failed (not found)",
            user_name=user.user_name,
            roles=user.roles,
            required_context={"action": "update", "target": user_name},
            request=req,
        )
        return ErrorResponse(f"User not found: {user_name}", status.HTTP_404_NOT_FOUND)
    except ValueError as e:
        log_audit_fail(
            msg=f"update user failed (value error): {e}",
            user_name=user.user_name,
            roles=user.roles,
            required_context={"action": "update", "target": user_name},
            request=req,
        )
        return ErrorResponse(str(e), status.HTTP_400_BAD_REQUEST)
    except Exception:
        LOGGER.exception("Update user error: %s", user_name)
        log_audit_fail(
            msg="update user failed (exception)",
            user_name=user.user_name,
            roles=user.roles,
            required_context={"action": "update", "target": user_name},
            request=req,
        )
        return ErrorResponse("Failed to update user.", status.HTTP_500_INTERNAL_SERVER_ERROR)


@router.get("/change_password/{user_name}", name=ADM_CHANGE_PW_CONTENT)
def _change_password_page(
    req: Request,
    user_name: str = Path(),
    user: UserDTO = Depends(ClaimsSelf.role_or_scope(roles=["admin"], scopes=["edit:auth_server"])),
) -> Response:
    return HResponse(ChangePasswordAdminDialog(user_name=user_name, dialog_id=ADM_CHANGE_PW_ID, req=req))


@router.post("/change_password", name=ADM_CHANGE_PW_API)
def _change_password(
    req: Request,
    password: str = Form(...),
    password_confirm: str = Form(...),
    user: UserDTO = Depends(ClaimsSelf.role_or_scope(roles=["admin"], scopes=["edit:auth_server"])),
    session: Session = Depends(get_session),
) -> Response:
    _ = req
    if password != password_confirm:
        return ErrorResponse("The new passwords do not match.")

    try:
        user_service.change_password(session, user.user_name, password)
        return SuccessResponse()
    except UserNotFoundError:
        return ErrorResponse("User not found.", status.HTTP_404_NOT_FOUND)
    except ValueError as e:
        return ErrorResponse(str(e), status.HTTP_400_BAD_REQUEST)
    except Exception:
        LOGGER.exception("Failed to validate password for %s", user.user_name)
        return ErrorResponse("Failed to validate password.", status.HTTP_500_INTERNAL_SERVER_ERROR)


@router.delete("/delete/{user_name}", name=ADM_DELETE_USER_API)
def _delete_user(
    req: Request,
    user_name: str = Path(),
    page: int = Query(1),
    session: Session = Depends(get_session),
    user: UserDTO = Depends(ClaimsSelf.role_or_scope(roles=["admin"], scopes=["edit:auth_server"])),
) -> Response:
    LOGGER.debug("Delete User: %s", user_name)
    try:
        user_service.delete_user(session, user_name)
        log_audit_success(
            msg="delete user success",
            user_name=user.user_name,
            roles=user.roles,
            required_context={"action": "delete", "target": user_name},
            request=req,
        )
    except UserNotFoundError:
        LOGGER.debug("Delete failed - user not found: %s", user_name, exc_info=True)
        log_audit_fail(
            msg="delete user failed (not found)",
            user_name=user.user_name,
            roles=user.roles,
            required_context={"action": "delete", "target": user_name},
            request=req,
        )
        return ErrorResponse(f"User not found: {user_name}", status.HTTP_404_NOT_FOUND)

    list_url = req.url_for(ADM_USER_LIST_CONTENT).include_query_params(page=page)
    return RedirectResponse(list_url, status_code=status.HTTP_303_SEE_OTHER)
