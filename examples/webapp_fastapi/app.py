from __future__ import annotations

from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from zen_auth.claims import Claims
from zen_auth.dto import UserDTO
from zen_auth.errors import (
    ClaimError,
    ClaimSourceError,
    InvalidCredentialsError,
    InvalidTokenError,
    MissingRequiredRolesError,
    MissingRequiredRolesOrScopesError,
    MissingRequiredScopesError,
)
from zen_html import H

app = FastAPI(title="ZenAuth Example WebApp")

APP_ID = "example_webapp"


def _html_doc(title: str, *content: H) -> HTMLResponse:
    doc = H.html(
        children=[
            H.head(
                H.meta(charset="utf-8"),
                H.meta(name="viewport", content="width=device-width, initial-scale=1"),
                H.title(title),
            ),
            H.body(
                H.h1(title),
                *content,
            ),
        ]
    )

    html = "<!doctype html>" + "".join(doc.to_token())
    return HTMLResponse(html)


def _links(req: Request) -> H:
    login_url = str(req.url_for("start_login"))
    protected_url = str(req.url_for("protected"))
    protected_admin_url = str(req.url_for("protected_admin"))
    protected_scope_url = str(req.url_for("protected_scope"))
    protected_role_or_scope_url = str(req.url_for("protected_role_or_scope"))
    fake_role_url = str(req.url_for("protected_fake_role"))
    fake_scope_url = str(req.url_for("protected_fake_scope"))
    fake_role_or_scope_url = str(req.url_for("protected_fake_role_or_scope"))
    logout_url = str(req.url_for("logout"))

    return H.ul(
        H.li(H.a("Login (redirect to ZenAuth UI)", href=login_url)),
        H.li(H.a("After login / Protected", href=protected_url)),
        H.li(H.a("Role protected (admin)", href=protected_admin_url)),
        H.li(H.a("Scope protected (example:read)", href=protected_scope_url)),
        H.li(H.a("Role OR Scope protected", href=protected_role_or_scope_url)),
        H.li(H.a("Role protected (fake_role)", href=fake_role_url)),
        H.li(H.a("Scope protected (fake_scope)", href=fake_scope_url)),
        H.li(H.a("Role OR Scope protected (fake)", href=fake_role_or_scope_url)),
        H.li(H.a("Logout (clear cookie)", href=logout_url)),
    )


# Test endpoints for undefined role/scope/role_or_scope
@app.get("/protected/fake_role", name="protected_fake_role")
def protected_fake_role(req: Request, user: UserDTO = Depends(Claims.role("fake_role"))) -> HTMLResponse:
    return _html_doc(
        "Role protected: fake_role",
        H.p("Logged in as: ", H.b(user.user_name)),
        H.p("This page requires role: fake_role (should always 403)"),
        H.p(H.a("Back", href=str(req.url_for("protected")))),
    )


@app.get("/protected/fake_scope", name="protected_fake_scope")
def protected_fake_scope(req: Request, user: UserDTO = Depends(Claims.scope("fake_scope"))) -> HTMLResponse:
    return _html_doc(
        "Scope protected: fake_scope",
        H.p("Logged in as: ", H.b(user.user_name)),
        H.p("This page requires scope: fake_scope (should always 403)"),
        H.p(H.a("Back", href=str(req.url_for("protected")))),
    )


@app.get("/protected/fake_role_or_scope", name="protected_fake_role_or_scope")
def protected_fake_role_or_scope(
    req: Request, user: UserDTO = Depends(Claims.role_or_scope(roles=["fake_role"], scopes=["fake_scope"]))
) -> HTMLResponse:
    return _html_doc(
        "Role OR Scope protected: fake_role or fake_scope",
        H.p("Logged in as: ", H.b(user.user_name)),
        H.p("This page requires role: fake_role OR scope: fake_scope (should always 403)"),
        H.p(H.a("Back", href=str(req.url_for("protected")))),
    )


def _dashboard(req: Request, user: UserDTO) -> HTMLResponse:
    roles = ", ".join(user.roles) if user.roles else "(none)"
    return _html_doc(
        "After login",
        H.p("Logged in as: ", H.b(user.user_name)),
        H.p("Roles: ", roles),
        H.h2("Try protected pages"),
        _links(req),
    )


@app.exception_handler(ClaimError)
def _claim_error_handler(req: Request, exc: ClaimError) -> HTMLResponse:
    status_code = 500
    title = "Auth error"
    details: list[H] = []

    if isinstance(exc, (InvalidTokenError, InvalidCredentialsError)):
        status_code = 401
        title = "Unauthorized"
    elif isinstance(
        exc,
        (
            MissingRequiredRolesError,
            MissingRequiredScopesError,
            MissingRequiredRolesOrScopesError,
        ),
    ):
        status_code = 403
        title = "Forbidden"
    elif isinstance(exc, ClaimSourceError):
        status_code = 502
        title = "Auth server error"
        if exc.code is not None:
            details.append(H.li(f"code: {exc.code}"))

    if getattr(exc, "user_name", None):
        details.append(H.li(f"user: {getattr(exc, 'user_name')}"))

    return HTMLResponse(
        _html_doc(
            title,
            H.p(str(exc)),
            (H.ul(*details) if details else H.div()),
            H.p(H.a("Back to top", href=str(req.url_for("top")))),
        ).body,
        status_code=status_code,
    )


@app.get("/", response_class=HTMLResponse)
def top(req: Request) -> HTMLResponse:
    return _html_doc(
        "ZenAuth Example WebApp",
        _links(req),
    )


@app.get("/auth/login", name="start_login")
def start_login(req: Request) -> RedirectResponse:
    url = Claims.login_page_url(req, app_id=APP_ID, title="Example WebApp Login")
    return RedirectResponse(url)


@app.get("/auth/logout", name="logout")
def logout(req: Request) -> Response:
    _ = req
    resp = RedirectResponse(url="/", status_code=303)
    Claims.logout(resp)
    return resp


@app.get("/protected", name="protected")
def protected(req: Request, user: UserDTO = Depends(Claims.guard())) -> HTMLResponse:
    return _dashboard(req, user)


@app.get("/after", name="after")
@app.get("/after_login", name="after_login")
def after_login(req: Request, user: UserDTO = Depends(Claims.guard())) -> HTMLResponse:
    return _dashboard(req, user)


@app.get("/protected/admin", name="protected_admin")
def protected_admin(req: Request, user: UserDTO = Depends(Claims.role("admin"))) -> HTMLResponse:
    return _html_doc(
        "Role protected: admin",
        H.p("Logged in as: ", H.b(user.user_name)),
        H.p("This page requires role: admin"),
        H.p(H.a("Back", href=str(req.url_for("protected")))),
    )


@app.get("/protected/scope", name="protected_scope")
def protected_scope(req: Request, user: UserDTO = Depends(Claims.scope("example:read"))) -> HTMLResponse:
    return _html_doc(
        "Scope protected: example:read",
        H.p("Logged in as: ", H.b(user.user_name)),
        H.p("This page requires scope: example:read"),
        H.p(H.a("Back", href=str(req.url_for("protected")))),
    )


@app.get("/protected/role_or_scope", name="protected_role_or_scope")
def protected_role_or_scope(
    req: Request,
    user: UserDTO = Depends(Claims.role_or_scope(roles=["admin"], scopes=["example:read"])),
) -> HTMLResponse:
    return _html_doc(
        "Role OR Scope protected",
        H.p("Logged in as: ", H.b(user.user_name)),
        H.p("This page allows either role=admin OR scope=example:read"),
        H.p(H.a("Back", href=str(req.url_for("protected")))),
    )
