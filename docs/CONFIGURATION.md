# Configuration

ZenAuth is configured via environment variables.

- Core library variables use the `ZENAUTH_` prefix.
- Server runtime variables use the `ZENAUTH_SERVER_` prefix.

## Minimum required (server)

- `ZENAUTH_SECRET_KEY` (required): Secret key used to sign/verify JWTs.
- `ZENAUTH_AUTH_SERVER_ORIGIN` (required): Public origin of the ZenAuth server (e.g. `https://auth.example.com`)
- `ZENAUTH_SERVER_DSN` (required): SQLAlchemy DSN for the ZenAuth server database.
  - Example (SQLite): `sqlite+pysqlite:///./zenauth.db`

## Common core options (`ZENAUTH_`)

- `ZENAUTH_COOKIE_NAME` (default: `access_token`)
- `ZENAUTH_EXPIRE_MIN` (default: `15`)
- `ZENAUTH_ALGORITHM` (default: `HS256`)
- `ZENAUTH_SAMESITE` (default: `lax`) — one of `lax`, `none`, `strict`
- `ZENAUTH_SECURE` (default: `false`) — cookie `Secure` flag
- `ZENAUTH_AUTH_SERVER_ORIGIN` (required) — remote verification URLs are generated against this origin

## Common server options (`ZENAUTH_SERVER_`)

- `ZENAUTH_SERVER_REFRESH_WINDOW_SEC` (default: `300`)

### CORS (server)

- `ZENAUTH_SERVER_CORS_ALLOW_ORIGINS` (default: empty) — comma-separated origins, `*` for any, empty string disables CORS middleware
- `ZENAUTH_SERVER_CORS_ALLOW_CREDENTIALS` (default: `false`) — set `true` if you need cookies/credentials from the browser
- `ZENAUTH_SERVER_CORS_ALLOW_METHODS` (default: `*`) — comma-separated methods or `*`
- `ZENAUTH_SERVER_CORS_ALLOW_HEADERS` (default: `*`) — comma-separated headers or `*`

Note: If you enable credentials, do not use `*` origins; list explicit origins instead.

### CSRF (server)

When using cookie-based auth from browsers, CSRF protection is recommended.

- `ZENAUTH_SERVER_CSRF_PROTECT` (default: `true`) — enable Origin/Referer checks for unsafe methods when the auth cookie is present
- `ZENAUTH_SERVER_CSRF_TRUSTED_ORIGINS` (default: empty) — comma-separated trusted origins; if empty uses CORS allow-origins (when set and not `*`) or same-origin
- `ZENAUTH_SERVER_CSRF_ALLOW_NO_ORIGIN` (default: `false`) — allow requests missing Origin/Referer (not recommended)

## Logging options

- `ZENAUTH_AUDIT_INCLUDE_TOKEN_TIMESTAMPS` (default: `false`) — when `true`, audit logs may include `token_iat` / `token_exp` extracted from the current request token.

### Optional: bootstrap an initial admin user (opt-in)

This is intended for development/demo use.

- `ZENAUTH_SERVER_BOOTSTRAP_ADMIN` (default: `false`)
- `ZENAUTH_SERVER_BOOTSTRAP_ADMIN_USER` (default: `admin`)
- `ZENAUTH_SERVER_BOOTSTRAP_ADMIN_PASSWORD` (required when bootstrap is enabled)

Recommended:
- Change the password immediately after first login.
- Do not enable this in production.

## `.env` (optional)

The settings loader supports reading a `.env` file if present, but in container environments it’s common to inject variables via the platform (Kubernetes Secret, ECS task env, etc.).
