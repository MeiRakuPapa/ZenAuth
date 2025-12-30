from fastapi import APIRouter, Cookie, Depends, Form, Query, Request, status
from fastapi.responses import HTMLResponse, Response
from sqlalchemy.orm import Session
from zen_auth.claims.base import log_audit_fail, log_audit_success
from zen_auth.dto import UserDTO
from zen_auth.errors import UserNotFoundError, UserVerificationError

from ....claims_self import ClaimsSelf
from ....persistence.session import get_session
from ....usecases import app_service, user_service
from .._tmp_lib import ErrorResponse, HResponse, SuccessResponse
from ..ui_ids import AUTH_CHANGE_PW_ID, AUTH_LOGIN_ID
from ..url_names import (
    ADM_TOP_PAGE,
    AUTH_CANCEL_API,
    AUTH_CHANGE_PW_API,
    AUTH_CHANGE_PW_PAGE,
    AUTH_LOGIN_API,
    AUTH_LOGIN_PAGE,
    AUTH_LOGOUT_API,
)
from .auth_tmpl import ChangePasswordPage, LoginPage, NotFoundPage

router = APIRouter(prefix="", tags=["auth"])

LOGIN_APP_ID_COOKIE_NAME = "login_app_id"


def _default_return_to(req: Request) -> str:
    return str(req.url_for(ADM_TOP_PAGE))


def _resolve_return_to(req: Request, session: Session, app_id: str | None, default: str | None = None) -> str:
    if app_id is not None:
        resolved = app_service.get_return_to_for_app(session, app_id)
        if resolved is not None:
            return resolved
    return default or _default_return_to(req)


@router.get("/login_page", response_class=HTMLResponse, name=AUTH_LOGIN_PAGE)
def login_page(
    req: Request,
    app_id: str | None = Query(None),
    title: str | None = Query(None),
    session: Session = Depends(get_session),
) -> Response:
    if app_id is not None:
        app_id = app_id.strip()
        if not app_id:
            return HResponse(
                NotFoundPage(req=req, title="App Not Found", message="The specified APP_ID was not found."),
                status_code=status.HTTP_404_NOT_FOUND,
            )

        app = app_service.get_app(session, app_id)
        if app is None:
            return HResponse(
                NotFoundPage(req=req, title="App Not Found", message="The specified APP_ID was not found."),
                status_code=status.HTTP_404_NOT_FOUND,
            )

        # If app_id is specified, show its display name by default so the user
        # can tell which application they are logging into.
        title = title or f"Login to {app.display_name}"

    title = title or "Zen Auth Login"

    # NOTE:
    # We do NOT store return_to in a cookie (client-controlled). We store app_id and
    # resolve return_to server-side in /login and /cancel.
    resp = HResponse(
        LoginPage(
            req=req,
            dialog_title=title,
            dialog_id=AUTH_LOGIN_ID,
        )
    )
    if app_id is not None:
        resp.set_cookie(LOGIN_APP_ID_COOKIE_NAME, app_id)
    return resp


@router.post("/login", name=AUTH_LOGIN_API)
def login(
    req: Request,
    user_name: str = Form(...),
    password: str = Form(...),
    login_app_id: str | None = Cookie(None, alias=LOGIN_APP_ID_COOKIE_NAME),
    session: Session = Depends(get_session),
) -> Response:
    return_to = _resolve_return_to(req, session, login_app_id)
    try:
        resp = Response(status_code=status.HTTP_200_OK, headers={"HX-Redirect": return_to})
        user = user_service.verify_user(session, user_name, password)
        ClaimsSelf.set_cookie(resp, ClaimsSelf.from_user(user).token)
        resp.delete_cookie(LOGIN_APP_ID_COOKIE_NAME)

        log_audit_success(
            msg="login success",
            user_name=user.user_name,
            roles=user.roles,
            required_context={"action": "login", "app_id": login_app_id, "return_to": return_to},
            request=req,
            include_token=False,
        )
        return resp
    except (UserNotFoundError, UserVerificationError):
        log_audit_fail(
            msg="login failed (invalid credentials)",
            user_name=user_name,
            roles=None,
            required_context={"action": "login", "app_id": login_app_id, "return_to": return_to},
            request=req,
            include_token=False,
        )
        return ErrorResponse("Invalid username or password.")
    except Exception as e:
        log_audit_fail(
            msg="login failed (exception)",
            user_name=user_name,
            roles=None,
            required_context={
                "action": "login",
                "app_id": login_app_id,
                "return_to": return_to,
                "error": str(e),
            },
            request=req,
            include_token=False,
        )
        return ErrorResponse(f"Login failed: {e}")


@router.post("/cancel", name=AUTH_CANCEL_API)
def cancel(
    req: Request,
    login_app_id: str | None = Cookie(None, alias=LOGIN_APP_ID_COOKIE_NAME),
    session: Session = Depends(get_session),
) -> Response:
    return_to = _resolve_return_to(req, session, login_app_id)
    resp = Response(status_code=status.HTTP_200_OK, headers={"HX-Redirect": return_to})
    resp.delete_cookie(LOGIN_APP_ID_COOKIE_NAME)
    return resp


@router.post("/logout", name=AUTH_LOGOUT_API)
def logout(
    req: Request,
    user: UserDTO = Depends(ClaimsSelf.guard()),
) -> Response:
    # For HTMX clients, redirect to the login page after clearing cookies.
    # Keep the JSON success body for non-HTMX clients.
    res = SuccessResponse()
    res.headers["HX-Redirect"] = str(req.url_for(AUTH_LOGIN_PAGE))
    ClaimsSelf.logout(res)

    log_audit_success(
        msg="logout success",
        user_name=user.user_name,
        roles=user.roles,
        required_context={"action": "logout"},
        request=req,
    )
    return res


@router.get("/change_password_page", response_class=HTMLResponse, name=AUTH_CHANGE_PW_PAGE)
def _change_password_page(
    req: Request,
    app_id: str | None = Query(None),
    user: UserDTO = Depends(ClaimsSelf.guard()),
    session: Session = Depends(get_session),
) -> Response:
    if app_id is not None:
        app_id = app_id.strip()
        if not app_id or app_service.get_app(session, app_id) is None:
            return HResponse(
                NotFoundPage(req=req, title="App Not Found", message="The specified APP_ID was not found."),
                status_code=status.HTTP_404_NOT_FOUND,
            )

    resp = HResponse(
        ChangePasswordPage(
            req=req,
            user_name=user.user_name,
            dialog_id=AUTH_CHANGE_PW_ID,
        )
    )
    if app_id is not None:
        resp.set_cookie(LOGIN_APP_ID_COOKIE_NAME, app_id)
    return resp


@router.post("/change_password", name=AUTH_CHANGE_PW_API)
def _change_password(
    req: Request,
    password: str = Form(...),
    confirm_password: str = Form(...),
    login_app_id: str | None = Cookie(None, alias=LOGIN_APP_ID_COOKIE_NAME),
    user: UserDTO = Depends(ClaimsSelf.guard()),
    session: Session = Depends(get_session),
) -> Response:
    if password != confirm_password:
        log_audit_fail(
            msg="change password failed (confirmation mismatch)",
            user_name=user.user_name,
            roles=user.roles,
            required_context={"action": "change_password", "app_id": login_app_id},
            request=req,
        )
        return ErrorResponse("The new passwords do not match.")

    return_to = _resolve_return_to(req, session, login_app_id)
    try:
        user_service.change_password(session, user.user_name, password)
        resp = Response(status_code=status.HTTP_200_OK, headers={"HX-Redirect": return_to})
        resp.delete_cookie(LOGIN_APP_ID_COOKIE_NAME)

        log_audit_success(
            msg="change password success",
            user_name=user.user_name,
            roles=user.roles,
            required_context={"action": "change_password", "app_id": login_app_id, "return_to": return_to},
            request=req,
        )
        return resp
    except UserNotFoundError:
        log_audit_fail(
            msg="change password failed (user not found)",
            user_name=user.user_name,
            roles=user.roles,
            required_context={"action": "change_password", "app_id": login_app_id},
            request=req,
        )
        return ErrorResponse("User not found.", status.HTTP_404_NOT_FOUND)
    except ValueError as e:
        log_audit_fail(
            msg=f"change password failed (value error): {e}",
            user_name=user.user_name,
            roles=user.roles,
            required_context={"action": "change_password", "app_id": login_app_id},
            request=req,
        )
        return ErrorResponse(str(e), status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        log_audit_fail(
            msg="change password failed (exception)",
            user_name=user.user_name,
            roles=user.roles,
            required_context={"action": "change_password", "app_id": login_app_id, "error": str(e)},
            request=req,
        )
        return ErrorResponse(f"Failed to change password: {e}")
