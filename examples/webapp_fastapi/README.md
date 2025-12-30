# ZenAuth Example WebApp (FastAPI)

This is a minimal WebApp example that uses ZenAuthServer as an authentication server.

- Redirects to the ZenAuth hosted login UI (`/zen_auth/v1/auth/login_page`) via `/auth/login`
- Shows the logged-in username on `/protected` (also available at `/after_login`)
- Provides links to role/scope-protected pages (to demonstrate authorization failures)
- Protects pages using `Claims.guard()` / `Claims.role()` / `Claims.scope()`
- Generates HTML with ZenHtml (`zen_html`)

## Prerequisites

- ZenAuthServer is running (e.g. `http://localhost:8000`)
- The WebApp can access ZenAuthServer discovery (`/zen_auth/v1/meta/endpoints`)

## Run

Start ZenAuthServer first, then start this WebApp.

### WebApp

```bash
export ZENAUTH_AUTH_SERVER_ORIGIN="http://localhost:8000"
uvicorn examples.webapp_fastapi.app:app --reload --port 9000
```

- WebApp: `http://localhost:9000/`
- ZenAuthServer: `http://localhost:8000/`

## Configure `return_to` (important)

ZenAuthServer resolves the post-login redirect destination from `app_id` (open redirect prevention).
For this example to land on a page that shows the username, set the client app's `return_to` to:

- `http://localhost:9000/after_login` (recommended)

Then access the WebApp and click **Login**.

## ZenAuthServer setup (admin UI)

You typically need to configure **app**, **user**, **role**, and **scope** on ZenAuthServer to fully exercise this example.

1. Ensure you can sign in to the ZenAuth admin UI:
	- Admin UI: `http://localhost:8000/zen_auth/v1/admin/`

	- If you don't have an admin user yet, start ZenAuthServer with bootstrap admin enabled.
	  - See: [README.md](../../README.md) (environment variables for `ZENAUTH_SERVER_BOOTSTRAP_ADMIN*`)
2. Create/update the client app mapping (Apps):
	- `app_id`: `example_webapp`
	- `return_to`: `http://localhost:9000/after_login`
3. Create a scope (Scopes):
	- `example:read`
4. Create/update a user (Users) and assign permissions:
	- For `/protected/admin`: give the user role `admin`
	- For `/protected/scope`: give the user scope `example:read`

After that, go to `http://localhost:9000/` and click **Login**.

## Role/scope pages

From `/after_login` (or `/protected`), try:

- `/protected/admin` (requires role: `admin`)
- `/protected/scope` (requires scope: `example:read`)
- `/protected/role_or_scope` (requires either role `admin` or scope `example:read`)

### Test with undefined role/scope

- `/protected/fake_role` (requires role: `fake_role`, which is not defined)
- `/protected/fake_scope` (requires scope: `fake_scope`, which is not defined)
- `/protected/fake_role_or_scope` (requires either role `fake_role` or scope `fake_scope`, neither defined)

If authorization fails (including when the required role/scope does not exist), the app renders a simple HTML error page with status 403 Forbidden. This is safe and expected.

## Notes

- Cookies are scoped to a domain. In local dev, browsers send cookies to `localhost` even if ports differ.
- If your WebApp and ZenAuthServer are on different domains in production, you cannot share cookies; choose a different deployment/architecture.
