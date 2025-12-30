# Usage

## Run ZenAuth server

1) Set required environment variables:

- `ZENAUTH_SECRET_KEY`
- `ZENAUTH_SERVER_DSN`

2) Start Uvicorn:

```bash
uvicorn zen_auth.server.run:app --host 0.0.0.0 --port 8000
```

## Use ZenAuth in your WebApp (server-side)

Example: validate tokens by calling the ZenAuth server from another FastAPI app.

```python
from fastapi import Depends, FastAPI

from zen_auth.claims import Claims
from zen_auth.dto import UserDTO

app = FastAPI()

AUTH_VERIFY_TOKEN_URL = "http://auth-server:8000/zen_auth/api/verify/token"


@app.get("/protected")
def protected(user: UserDTO = Depends(Claims.guard(url=AUTH_VERIFY_TOKEN_URL))):
    return {"ok": True, "user_name": user.user_name}
```

Notes:
- Tokens are read from cookie or `Authorization: Bearer <token>`.

## Claims: FastAPI dependencies

`Claims` provides FastAPI dependencies for authentication and authorization.

### Authenticate (any logged-in user)

Use `Claims.guard()` to require a valid token and get the authenticated user.

This dependency also refreshes the auth cookie on the outgoing response.

```python
from fastapi import Depends, FastAPI

from zen_auth.claims import Claims
from zen_auth.dto import UserDTO

app = FastAPI()


@app.get("/protected")
def protected(user: UserDTO = Depends(Claims.guard())):
    return {"ok": True, "user_name": user.user_name}
```

### Login / logout (cookie helpers)

`Claims.verify_user(...)` verifies username/password via the ZenAuth server and sets the auth cookie.

```python
from fastapi import FastAPI, Request, Response
from pydantic import BaseModel

from zen_auth.claims import Claims

app = FastAPI()


class LoginBody(BaseModel):
    user_name: str
    password: str


@app.post("/login")
def login(req: Request, resp: Response, body: LoginBody) -> Response:
    return Claims.verify_user(req, resp, body.user_name, body.password)


@app.post("/logout")
def logout(resp: Response) -> dict:
    Claims.logout(resp)
    return {"ok": True}
```

### Redirect to the ZenAuth login UI

If your WebApp wants to use the ZenAuth-hosted login page, redirect the user to
`/zen_auth/v1/auth/login_page` with `app_id`.

For security (open redirect prevention), the login page does not accept a
user-controlled "return_to" URL. Instead, the auth server resolves the
post-login destination from the given `app_id`.

```python
from fastapi import Request
from fastapi.responses import RedirectResponse

from zen_auth.claims import Claims


@app.get("/auth/login")
def start_login(req: Request) -> RedirectResponse:
    url = Claims.login_page_url(req, app_id="my_app")
    return RedirectResponse(url)
```

### Require roles (RBAC)

Use `Claims.role(...)` to enforce roles.

It accepts multiple role names and allows access if the user has **any** of them (OR).

Example: allow users with either `admin` OR `viewer`:

```python
@app.get("/admin")
def admin_or_viewer(user: UserDTO = Depends(Claims.role("admin", "viewer"))):
    return {"ok": True}

Notes:
- ZenAuthServer returns `200 OK` when access is allowed, and `403 Forbidden` when the user lacks the required role(s).
- `Claims` treats `403` as a normal authorization failure (not an upstream/server error). Other non-`200` responses are treated as upstream errors (`ClaimSourceError`).
```

### Require scopes

Use `Claims.scope(...)` to enforce scopes.

It accepts multiple scope names and allows access if the user has **any** of them (OR).

```python
@app.get("/reports")
def reports(user: UserDTO = Depends(Claims.scope("read:reports"))):
    return {"ok": True}

Notes:
- ZenAuthServer returns `200 OK` when access is allowed, and `403 Forbidden` when the user lacks the required scope(s).
- `Claims` treats `403` as a normal authorization failure (not an upstream/server error). Other non-`200` responses are treated as upstream errors (`ClaimSourceError`).
```

### Require role OR scope

Use `Claims.role_or_scope(...)` when you want a single dependency that allows access if either:

- the user has any of the specified roles, OR
- the user has any of the specified scopes.

```python
@app.get("/support")
def support(
    user: UserDTO = Depends(Claims.role_or_scope(roles=("admin", "support"), scopes=("support:read",))),
):
    return {"ok": True}

Notes:
- If the auth server exposes `verify_user_role_or_scope` via discovery (`/zen_auth/v1/meta/endpoints`), `Claims.role_or_scope(...)` calls that combined endpoint.
- Otherwise it falls back to calling role and scope verification separately.
- The combined endpoint follows the same convention: `200 OK` = allowed, `403 Forbidden` = denied.
```

### Pointing Claims at the auth server

When calling the ZenAuth server from another service, set:

- `ZENAUTH_AUTH_SERVER_ORIGIN` (example: `https://auth.example.com`)

`Claims` will use this origin when constructing auth-server URLs.

### Exceptions (minimal)

`Claims.guard()` / `Claims.role()` / `Claims.scope()` raise exceptions under `zen_auth.errors` (notably `ClaimError` and subclasses) when verification fails or when the auth server cannot be reached.

How to translate these into HTTP responses or UI behavior is intentionally left to the WebApp.
