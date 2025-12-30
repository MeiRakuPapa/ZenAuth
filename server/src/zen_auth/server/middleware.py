import logging
import time
from typing import Awaitable, Callable
from urllib.parse import urlparse

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from zen_auth.config import ZENAUTH_CONFIG

from .config import ZENAUTH_SERVER_CONFIG


def _split_csv(value: str) -> list[str]:
    return [v.strip() for v in value.split(",") if v.strip()]


def _origin_from_url(url: str) -> str | None:
    try:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return None
        return f"{parsed.scheme}://{parsed.netloc}"
    except Exception:
        return None


class CSRFMiddleware(BaseHTTPMiddleware):
    _UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        cfg = ZENAUTH_SERVER_CONFIG()
        if not cfg.csrf_protect:
            return await call_next(request)

        if request.method.upper() not in self._UNSAFE_METHODS:
            return await call_next(request)

        auth_cookie_name = ZENAUTH_CONFIG().cookie_name
        if auth_cookie_name not in request.cookies:
            return await call_next(request)

        # Resolve trusted origins.
        trusted_raw = cfg.csrf_trusted_origins.strip()
        if trusted_raw:
            trusted = set(_split_csv(trusted_raw))
        else:
            cors_raw = cfg.cors_allow_origins.strip()
            if cors_raw and cors_raw != "*":
                trusted = set(_split_csv(cors_raw))
            else:
                host = request.headers.get("host")
                request_origin = f"{request.url.scheme}://{host}" if host else None
                trusted = {request_origin} if request_origin else set()

        origin = request.headers.get("origin")
        if origin:
            if origin not in trusted:
                return Response(status_code=403, content="CSRF verification failed (origin)")
            return await call_next(request)

        referer = request.headers.get("referer")
        if referer:
            ref_origin = _origin_from_url(referer)
            if not ref_origin or ref_origin not in trusted:
                return Response(status_code=403, content="CSRF verification failed (referer)")
            return await call_next(request)

        if cfg.csrf_allow_no_origin:
            return await call_next(request)

        return Response(status_code=403, content="CSRF verification failed (missing origin)")


class AccessLogWithTimeMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:

        start: float = time.perf_counter()
        response: Response = await call_next(request)
        duration_ms: float = (time.perf_counter() - start) * 1000.0
        client_addr = request.client.host if request.client else "-"

        request_line: str = (
            f"{request.method} {request.url.path} " f"HTTP/{request.scope.get('http_version', '1.1')}"
        )

        logging.getLogger("access").info(
            request_line,
            extra={
                "client_addr": client_addr,
                "request_line": request_line,
                "status_code": response.status_code,
                "duration_ms": f"{duration_ms:.2f}",
            },
        )

        return response
