from datetime import datetime, timedelta, timezone
from typing import Any, TypeVar

from fastapi import APIRouter, Body, Depends, HTTPException, status
from fastapi.encoders import jsonable_encoder
from fastapi.requests import Request
from fastapi.responses import JSONResponse, Response
from jose import JWTError
from pydantic import BaseModel
from sqlalchemy.orm import Session
from starlette.background import BackgroundTask
from zen_auth.claims import Claims
from zen_auth.claims.base import log_audit_fail, log_audit_success
from zen_auth.dto import VerifyTokenDTO
from zen_auth.errors import (
    ClaimSourceError,
    InvalidCredentialsError,
    InvalidTokenError,
    UserNotFoundError,
    UserVerificationError,
)
from zen_auth.logger import LOGGER

from ....claims_self import ClaimsSelf
from ....persistence.session import get_session
from ....usecases import rbac_checks, user_service
from ..url_names import (
    VERIFY_TOKEN_API,
    VERIFY_USER_API,
    VERIFY_USER_ROLE_API,
    VERIFY_USER_ROLE_OR_SCOPE_API,
    VERIFY_USER_SCOPE_API,
)

router = APIRouter(prefix="", tags=["verify"])

T = TypeVar("T")


class VerifyResponse(JSONResponse):
    def __init__(
        self,
        *,
        data: T,
        request: Request,
        status_code: int = status.HTTP_200_OK,
        headers: dict[str, str] | None = None,
        media_type: str | None = None,
        background: BackgroundTask | None = None,
    ) -> None:
        meta = {
            "req_id": getattr(request, "req_id", "--"),
            "timestamp": datetime.now(tz=timezone(timedelta(hours=9))).isoformat(
                sep="T", timespec="milliseconds"
            ),
        }
        payload: dict[str, Any] = {
            "data": jsonable_encoder(data),
            "meta": meta,
        }
        super().__init__(
            content=payload,
            status_code=status_code,
            headers=headers,
            media_type=media_type,
            background=background,
        )


# Backward-compatible aliases for older names.
# NOTE: The HTTP JSON shape is the contract (data/meta), not this class name.
DataResponse = VerifyResponse
SuccessResponse = VerifyResponse


class VerifyUserRoleDTO(BaseModel):
    user_name: str
    role_name: str | None = None
    required_roles: list[str] | None = None


class VerifyUserRoleResultDTO(BaseModel):
    user_name: str
    role_name: str | None = None
    has_role: bool


class VerifyUserScopeDTO(BaseModel):
    user_name: str
    scope_name: str | None = None
    required_scopes: list[str] | None = None


class VerifyUserScopeResultDTO(BaseModel):
    user_name: str
    scope_name: str | None = None
    allowed: bool


class VerifyUserRoleOrScopeDTO(BaseModel):
    user_name: str
    required_roles: list[str] | None = None
    required_scopes: list[str] | None = None


class VerifyUserRoleOrScopeResultDTO(BaseModel):
    user_name: str
    has_access: bool
    has_role: bool
    allowed: bool


@router.post("/user", name=VERIFY_USER_API)
def _verify_user(
    req: Request,
    user: Claims.UserPassDTO = Body(),
    session: Session = Depends(get_session),
) -> Response:
    try:
        user_dto = user_service.verify_user(session, user.user_name, user.password)
        token = ClaimsSelf.from_user(user_dto).token

        log_audit_success(
            msg="verify user success",
            user_name=user_dto.user_name,
            roles=user_dto.roles,
            required_context={"action": "verify_user"},
            request=req,
        )
        return VerifyResponse(data=Claims.TokenDTO(token=token), request=req)
    except (UserNotFoundError, UserVerificationError) as e:
        LOGGER.error("Username or password is incorrect. (user: %s)", user.user_name, exc_info=True)

        log_audit_fail(
            msg="verify user failed (invalid credentials)",
            user_name=user.user_name,
            roles=None,
            required_context={"action": "verify_user"},
            request=req,
        )
        raise InvalidCredentialsError("Invalid username or password", user_name=user.user_name) from e
    except Exception as e:
        LOGGER.exception("Unexpected error verifying user: %s", user.user_name)

        log_audit_fail(
            msg="verify user failed (exception)",
            user_name=user.user_name,
            roles=None,
            required_context={"action": "verify_user", "error": str(e)},
            request=req,
        )
        raise ClaimSourceError("Auth backend error", code="internal") from e


@router.post("/token", name=VERIFY_TOKEN_API)
def _verify_token(
    req: Request,
    token: Claims.TokenDTO = Body(),
    session: Session = Depends(get_session),
) -> Response:
    user_name: str = "--"
    try:
        claims, user = ClaimsSelf._verify_token_with_session(session, token.token)
        user_name = user.user_name
        return VerifyResponse(data=VerifyTokenDTO(token=claims.token, user=user), request=req)
    except JWTError as e:
        LOGGER.debug("Invalid or expired token: (user: %s)", user_name, exc_info=True)

        log_audit_fail(
            msg="verify token failed (invalid)",
            user_name=user_name,
            roles=None,
            required_context={"action": "verify_token", "kind": "invalid"},
            request=req,
        )
        raise InvalidTokenError(
            f"Invalid or expired token: (user: {user_name})", user_name=user_name, kind="invalid"
        ) from e
    except UserNotFoundError as e:
        LOGGER.debug("User not found during token verify: (user: %s)", user_name, exc_info=True)

        log_audit_fail(
            msg="verify token failed (user not found)",
            user_name=user_name,
            roles=None,
            required_context={"action": "verify_token", "kind": "user_not_found"},
            request=req,
        )
        raise InvalidTokenError(
            f"User not found: (user: {user_name})", user_name=user_name, kind="user_not_found"
        ) from e
    except Exception as e:
        LOGGER.error("Unexpected error during token verify: %s", e, exc_info=True)

        log_audit_fail(
            msg="verify token failed (exception)",
            user_name=user_name,
            roles=None,
            required_context={"action": "verify_token", "error": str(e)},
            request=req,
        )
        raise ClaimSourceError("Auth backend error", code="internal") from e


@router.post("/user/role", name=VERIFY_USER_ROLE_API)
def _verify_user_role(
    req: Request,
    payload: VerifyUserRoleDTO = Body(),
    session: Session = Depends(get_session),
) -> Response:
    try:
        if payload.role_name:
            has_role = rbac_checks.user_has_role(session, payload.user_name, payload.role_name)
        elif payload.required_roles:
            user = user_service.get_user(session, payload.user_name)
            has_role = rbac_checks.has_required_roles(user.roles, payload.required_roles)
        else:
            has_role = False

        if has_role:
            log_audit_success(
                msg="verify user role success",
                user_name=payload.user_name,
                roles=None,
                required_context={
                    "action": "verify_user_role",
                    "role_name": payload.role_name,
                    "required_roles": payload.required_roles,
                    "has_role": has_role,
                },
                request=req,
            )
        else:
            log_audit_fail(
                msg="verify user role denied",
                user_name=payload.user_name,
                roles=None,
                required_context={
                    "action": "verify_user_role",
                    "role_name": payload.role_name,
                    "required_roles": payload.required_roles,
                    "has_role": has_role,
                },
                request=req,
            )
        return VerifyResponse(
            data=VerifyUserRoleResultDTO(
                user_name=payload.user_name,
                role_name=payload.role_name,
                has_role=has_role,
            ),
            request=req,
            status_code=status.HTTP_200_OK if has_role else status.HTTP_403_FORBIDDEN,
        )
    except Exception as e:
        LOGGER.exception(
            "Unexpected error verifying user role: user=%s role=%s",
            payload.user_name,
            payload.role_name,
        )

        log_audit_fail(
            msg="verify user role failed (exception)",
            user_name=payload.user_name,
            roles=None,
            required_context={
                "action": "verify_user_role",
                "role_name": payload.role_name,
                "required_roles": payload.required_roles,
                "error": str(e),
            },
            request=req,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Auth backend error"
        ) from e


@router.post("/user/scope", name=VERIFY_USER_SCOPE_API)
def _verify_user_scope(
    req: Request,
    payload: VerifyUserScopeDTO = Body(),
    session: Session = Depends(get_session),
) -> Response:
    try:
        if payload.scope_name:
            allowed = rbac_checks.user_allowed_scope(session, payload.user_name, payload.scope_name)
        elif payload.required_scopes:
            allowed = rbac_checks.has_required_scopes(session, payload.user_name, payload.required_scopes)
        else:
            allowed = False

        if allowed:
            log_audit_success(
                msg="verify user scope success",
                user_name=payload.user_name,
                roles=None,
                required_context={
                    "action": "verify_user_scope",
                    "scope_name": payload.scope_name,
                    "required_scopes": payload.required_scopes,
                    "allowed": allowed,
                },
                request=req,
            )
        else:
            log_audit_fail(
                msg="verify user scope denied",
                user_name=payload.user_name,
                roles=None,
                required_context={
                    "action": "verify_user_scope",
                    "scope_name": payload.scope_name,
                    "required_scopes": payload.required_scopes,
                    "allowed": allowed,
                },
                request=req,
            )
        return VerifyResponse(
            data=VerifyUserScopeResultDTO(
                user_name=payload.user_name,
                scope_name=payload.scope_name,
                allowed=allowed,
            ),
            request=req,
            status_code=status.HTTP_200_OK if allowed else status.HTTP_403_FORBIDDEN,
        )
    except Exception as e:
        LOGGER.exception(
            "Unexpected error verifying user scope: user=%s scope=%s",
            payload.user_name,
            payload.scope_name,
        )

        log_audit_fail(
            msg="verify user scope failed (exception)",
            user_name=payload.user_name,
            roles=None,
            required_context={
                "action": "verify_user_scope",
                "scope_name": payload.scope_name,
                "required_scopes": payload.required_scopes,
                "error": str(e),
            },
            request=req,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Auth backend error"
        ) from e


@router.post("/user/role_or_scope", name=VERIFY_USER_ROLE_OR_SCOPE_API)
def _verify_user_role_or_scope(
    req: Request,
    payload: VerifyUserRoleOrScopeDTO = Body(),
    session: Session = Depends(get_session),
) -> Response:
    required_roles = payload.required_roles or []
    required_scopes = payload.required_scopes or []

    try:
        has_role = False
        allowed = False
        user_roles_for_log: list[str] | None = None

        if required_roles:
            user = user_service.get_user(session, payload.user_name)
            user_roles_for_log = list(user.roles)
            has_role = rbac_checks.has_required_roles(user.roles, required_roles)

        if required_scopes:
            allowed = rbac_checks.has_required_scopes(session, payload.user_name, required_scopes)

        has_access = bool(has_role or allowed)

        if has_access:
            log_audit_success(
                msg="verify user role_or_scope success",
                user_name=payload.user_name,
                roles=user_roles_for_log,
                required_context={
                    "action": "verify_user_role_or_scope",
                    "required_roles": required_roles,
                    "required_scopes": required_scopes,
                    "has_role": bool(has_role),
                    "allowed": bool(allowed),
                    "has_access": has_access,
                },
                request=req,
            )
        else:
            log_audit_fail(
                msg="verify user role_or_scope denied",
                user_name=payload.user_name,
                roles=user_roles_for_log,
                required_context={
                    "action": "verify_user_role_or_scope",
                    "required_roles": required_roles,
                    "required_scopes": required_scopes,
                    "has_role": bool(has_role),
                    "allowed": bool(allowed),
                    "has_access": has_access,
                },
                request=req,
            )

        return VerifyResponse(
            data=VerifyUserRoleOrScopeResultDTO(
                user_name=payload.user_name,
                has_access=has_access,
                has_role=bool(has_role),
                allowed=bool(allowed),
            ),
            request=req,
            status_code=status.HTTP_200_OK if has_access else status.HTTP_403_FORBIDDEN,
        )
    except Exception as e:
        LOGGER.exception(
            "Unexpected error verifying user role_or_scope: user=%s",
            payload.user_name,
        )

        log_audit_fail(
            msg="verify user role_or_scope failed (exception)",
            user_name=payload.user_name,
            roles=user_roles_for_log,
            required_context={
                "action": "verify_user_role_or_scope",
                "required_roles": required_roles,
                "required_scopes": required_scopes,
                "error": str(e),
            },
            request=req,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Auth backend error"
        ) from e
