from __future__ import annotations

from fastapi import APIRouter
from fastapi.requests import Request
from fastapi.responses import JSONResponse

from ..url_names import (
    AUTH_LOGIN_PAGE,
    META_ENDPOINTS_API,
    VERIFY_TOKEN_API,
    VERIFY_USER_API,
    VERIFY_USER_ROLE_API,
    VERIFY_USER_ROLE_OR_SCOPE_API,
    VERIFY_USER_SCOPE_API,
)

router = APIRouter(prefix="", tags=["meta"])


@router.get("/endpoints", name=META_ENDPOINTS_API)
def endpoints(req: Request) -> JSONResponse:
    """Return public API endpoints for clients.

    This is intended for service discovery so callers don't need to hardcode
    paths like `/verify/token`.
    """

    data = {
        "login_page": str(req.url_for(AUTH_LOGIN_PAGE)),
        "verify_token": str(req.url_for(VERIFY_TOKEN_API)),
        "verify_user": str(req.url_for(VERIFY_USER_API)),
        "verify_user_role": str(req.url_for(VERIFY_USER_ROLE_API)),
        "verify_user_scope": str(req.url_for(VERIFY_USER_SCOPE_API)),
        "verify_user_role_or_scope": str(req.url_for(VERIFY_USER_ROLE_OR_SCOPE_API)),
    }
    return JSONResponse(content={"data": data})
