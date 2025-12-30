"""Application configuration loaded from environment variables."""

import logging
from functools import lru_cache
from typing import ClassVar, Literal

from pydantic_settings import BaseSettings
from zen_auth.errors import ConfigError

LogLevels = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

LOGGER = logging.getLogger("zen_auth")


class ZenAuthConfig(BaseSettings):
    """ZenAuth settings.

    Values are loaded from env vars prefixed with `ZENAUTH_` and an optional `.env` file.

    Note: In container environments, configuration is typically provided via
    environment variables / injected secrets, so `.env` is usually unnecessary.
    """

    _ENV_PREFIX: ClassVar[str] = "ZENAUTH_"

    model_config = dict(env_prefix=_ENV_PREFIX, env_file=".env", extra="allow")
    cookie_name: str = "access_token"
    expire_min: int = 15
    algorithm: str = "HS256"
    samesite: Literal["lax", "none", "strict"] = "lax"
    secure: bool = False
    secret_key: str | None = None

    # When set, remote verification URLs are generated against this origin
    # instead of the incoming request host.
    auth_server_origin: str | None = None

    def safe_dict(self) -> dict[str, object]:
        """Return a redacted representation safe for logs/diagnostics."""

        data: dict[str, object] = self.model_dump()
        for key in ("secret_key",):
            if data.get(key) is not None:
                data[key] = "***REDACTED***"
        return data

    def model_post_init(self, context: object) -> None:
        if not self.secret_key or not self.secret_key.strip():
            msg = f"{self._ENV_PREFIX}SECRET_KEY must be set"
            LOGGER.critical(msg)
            raise ConfigError(msg)

        if not self.auth_server_origin or not self.auth_server_origin.strip():
            msg = f"{self._ENV_PREFIX}AUTH_SERVER_ORIGIN must be set"
            LOGGER.critical(msg)
            raise ConfigError(msg)

        # Avoid logging secrets. Use safe_dict() if needed.
        LOGGER.debug("ZenAuthConfig loaded (redacted): %s", self.safe_dict())

    @property
    def max_age(self) -> int:
        return self.expire_min * 60


@lru_cache
def ZENAUTH_CONFIG() -> ZenAuthConfig:
    return ZenAuthConfig()
