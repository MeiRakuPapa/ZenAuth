"""Server-side configuration loaded from environment variables.

This module contains settings that are only meaningful for the ZenAuth server
runtime (e.g., DB connectivity).
"""

from functools import lru_cache
from typing import ClassVar

from pydantic_settings import BaseSettings
from zen_auth.errors import ConfigError


class ZenAuthServerConfig(BaseSettings):
    """ZenAuth server settings.

    Values are loaded from env vars prefixed with `ZENAUTH_SERVER_` and an optional `.env` file.

    Note: In container environments, configuration is typically provided via
    environment variables / injected secrets, so `.env` is usually unnecessary.

    Note: Unlike core settings, these are only required when running the server.
    """

    _ENV_PREFIX: ClassVar[str] = "ZENAUTH_SERVER_"

    model_config = dict(env_prefix=_ENV_PREFIX, env_file=".env", extra="allow")

    dsn: str = ""
    refresh_window_sec: int = 300

    # --- CORS (disabled/locked-down recommended in production) ---
    # Comma-separated list of allowed origins. Use "*" for any origin.
    # Use an empty string to disable CORS middleware entirely.
    cors_allow_origins: str = ""
    cors_allow_credentials: bool = False
    cors_allow_methods: str = "*"
    cors_allow_headers: str = "*"

    # --- CSRF protection (recommended when using cookie-based auth from browsers) ---
    # When enabled, requests with the auth cookie must include a same-origin
    # (or trusted-origin) Origin/Referer header for unsafe methods.
    csrf_protect: bool = True
    # Comma-separated list of trusted origins (e.g. https://app.example).
    # If empty, falls back to CORS allow-origins (if set and not "*") or same-origin.
    csrf_trusted_origins: str = ""
    # If true, allows requests without Origin/Referer (not recommended).
    csrf_allow_no_origin: bool = False

    # --- Optional: bootstrap an initial admin account (recommended: disabled in production) ---
    # When enabled, creates the user only if it does not already exist.
    bootstrap_admin: bool = False
    bootstrap_admin_user: str = "admin"
    bootstrap_admin_password: str | None = None

    def model_post_init(self, context: object) -> None:
        if not self.dsn or not self.dsn.strip():
            raise ConfigError(f"{self._ENV_PREFIX}DSN must be set")

        if self.bootstrap_admin:
            if not self.bootstrap_admin_user or not self.bootstrap_admin_user.strip():
                raise ConfigError(f"{self._ENV_PREFIX}BOOTSTRAP_ADMIN_USER must be set")
            if not self.bootstrap_admin_password or not self.bootstrap_admin_password.strip():
                raise ConfigError(f"{self._ENV_PREFIX}BOOTSTRAP_ADMIN_PASSWORD must be set")


@lru_cache
def ZENAUTH_SERVER_CONFIG() -> ZenAuthServerConfig:
    return ZenAuthServerConfig()
