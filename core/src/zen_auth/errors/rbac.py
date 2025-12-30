from __future__ import annotations


class RbacError(Exception):
    pass


class RoleError(RbacError):
    role_name: str | None

    def __init__(self, message: str, *, role_name: str | None = None) -> None:
        super().__init__(message)
        self.role_name = role_name


class RoleNotFoundError(RoleError):
    pass


class RoleAlreadyExistsError(RoleError):
    pass


class ScopeError(RbacError):
    scope_name: str | None

    def __init__(self, message: str, *, scope_name: str | None = None) -> None:
        super().__init__(message)
        self.scope_name = scope_name


class ScopeNotFoundError(ScopeError):
    pass


class ScopeAlreadyExistsError(ScopeError):
    pass
