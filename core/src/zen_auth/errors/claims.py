from __future__ import annotations

from typing import Iterable


class ClaimError(Exception):
    """Base exception for claims/authn/authz related failures."""


class InvalidTokenError(ClaimError):
    """Token-level failures: missing, decode/signature, expired, policy mismatch."""

    user_name: str | None
    kind: str | None

    def __init__(self, message: str, *, user_name: str | None = None, kind: str | None = None) -> None:
        super().__init__(message)
        self.user_name = user_name
        self.kind = kind


class InvalidCredentialsError(ClaimError):
    """Authentication failures: invalid username or password (HTTP 401 semantics)."""

    user_name: str | None
    info: dict[str, object] | None

    def __init__(
        self,
        message: str,
        *,
        user_name: str | None = None,
        info: dict[str, object] | None = None,
    ) -> None:
        super().__init__(message)
        self.user_name = user_name
        self.info = info


class ClaimValidationError(ClaimError):
    """Payload structure/field validation failures."""

    field: str | None

    def __init__(self, message: str, *, field: str | None = None) -> None:
        super().__init__(message)
        self.field = field


class ClaimSourceError(ClaimError):
    """Errors contacting/parsing external auth sources.

    `code` can be one of: "timeout", "connection", "invalid_data", "internal".
    """

    code: str | None
    info: dict[str, object] | None

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        info: dict[str, object] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.info = info


class ClaimSerializationError(ClaimError):
    """JSON decode / DTO mapping failures for external responses."""

    info: dict[str, object] | None

    def __init__(self, message: str, *, info: dict[str, object] | None = None) -> None:
        super().__init__(message)
        self.info = info


class MissingRequiredRolesError(ClaimError):
    """RBAC failure: user lacks any of the required roles."""

    user_name: str | None
    roles: Iterable[str] | None
    required: Iterable[str] | None

    def __init__(
        self,
        message: str,
        *,
        user_name: str | None = None,
        roles: Iterable[str] | None = None,
        required: Iterable[str] | None = None,
    ) -> None:
        super().__init__(message)
        self.user_name = user_name
        self.roles = roles
        self.required = required


class MissingRequiredScopesError(ClaimError):
    """Scope authorization failure: user lacks any of the required scopes."""

    user_name: str | None
    roles: Iterable[str] | None
    required: Iterable[str] | None

    def __init__(
        self,
        message: str,
        *,
        user_name: str | None = None,
        roles: Iterable[str] | None = None,
        required: Iterable[str] | None = None,
    ) -> None:
        super().__init__(message)
        self.user_name = user_name
        self.roles = roles
        self.required = required


class MissingRequiredRolesOrScopesError(ClaimError):
    """Authorization failure: neither role nor scope requirements were satisfied."""

    user_name: str | None
    roles: Iterable[str] | None
    required_roles: Iterable[str] | None
    required_scopes: Iterable[str] | None

    def __init__(
        self,
        message: str,
        *,
        user_name: str | None = None,
        roles: Iterable[str] | None = None,
        required_roles: Iterable[str] | None = None,
        required_scopes: Iterable[str] | None = None,
    ) -> None:
        super().__init__(message)
        self.user_name = user_name
        self.roles = roles
        self.required_roles = required_roles
        self.required_scopes = required_scopes
