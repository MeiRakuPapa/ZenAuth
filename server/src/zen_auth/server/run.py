from fastapi import FastAPI, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.requests import Request
from fastapi.responses import FileResponse, RedirectResponse
from zen_auth.errors import ClaimError
from zen_auth.logger import LOGGER

from . import ENV
from .api import router
from .api.util.error_redirect import error_redirect
from .api.util.req_id import RequestIDMiddleWare
from .api.v1.url_names import AUTH_LOGIN_PAGE, META_ENDPOINTS_API
from .config import ZENAUTH_SERVER_CONFIG
from .lifespan import lifespan
from .middleware import AccessLogWithTimeMiddleware, CSRFMiddleware


def _split_csv(value: str) -> list[str]:
    return [v.strip() for v in value.split(",") if v.strip()]


def create_app() -> FastAPI:
    app = FastAPI(
        title="ZenAuth Authentication", version=ENV.BUILD, docs_url=None, redoc_url=None, lifespan=lifespan
    )

    cors = ZENAUTH_SERVER_CONFIG()
    cors_origins_raw = cors.cors_allow_origins.strip()
    if cors_origins_raw:
        allow_origins = ["*"] if cors_origins_raw == "*" else _split_csv(cors_origins_raw)
        allow_methods = (
            ["*"] if cors.cors_allow_methods.strip() == "*" else _split_csv(cors.cors_allow_methods)
        )
        allow_headers = (
            ["*"] if cors.cors_allow_headers.strip() == "*" else _split_csv(cors.cors_allow_headers)
        )

        app.add_middleware(
            CORSMiddleware,
            allow_origins=allow_origins,
            allow_credentials=cors.cors_allow_credentials,
            allow_methods=allow_methods,
            allow_headers=allow_headers,
        )
    app.add_middleware(RequestIDMiddleWare)
    app.add_middleware(CSRFMiddleware)
    app.add_middleware(AccessLogWithTimeMiddleware)

    # app.mount("/static", StaticFiles(directory="static"), name="static")

    app.include_router(router)

    return app


app = create_app()


@app.get("/")
def _top(req: Request) -> RedirectResponse:
    return RedirectResponse(req.url_for(AUTH_LOGIN_PAGE), status_code=status.HTTP_303_SEE_OTHER)


@app.get("/favicon.ico")
def _favicon() -> FileResponse:
    return FileResponse("static/favicon.ico")


@app.get("/endpoints")
def _endpoints(req: Request) -> RedirectResponse:
    return RedirectResponse(req.url_for(META_ENDPOINTS_API), status_code=status.HTTP_303_SEE_OTHER)


@app.exception_handler(ClaimError)
def rbac_exception_handler(request: Request, exc: ClaimError) -> Response:
    # NOTE: Avoid redirect targets derived from user-controlled cookies.
    # Redirect to the login page (fixed server route).
    to = request.url_for(AUTH_LOGIN_PAGE)

    # Log full details for operators
    LOGGER.warning("Claim error: %s", exc, exc_info=True)

    # Prepare a short, safe message for end users. Avoid leaking internals.
    msg = str(exc) or "An authentication error occurred"
    msg = msg.replace("\n", " ")[:200]

    return error_redirect(to, msg)
