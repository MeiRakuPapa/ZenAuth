from typing import Any, Callable, Iterable

from fastapi import Depends, Header
from fastapi.requests import Request
from fastapi.responses import Response
from jose import JWTError
from sqlalchemy.orm import Session
from typing_extensions import Self
from zen_auth.claims.base import (
    ERROR_UNKNOWN,
    Claims,
    _extract_bearer,
    _utcnow,
    log_audit_fail,
)
from zen_auth.config import ZENAUTH_CONFIG
from zen_auth.dto import UserDTO, VerifyTokenDTO
from zen_auth.errors import (
    ClaimError,
    InvalidTokenError,
    MissingRequiredRolesError,
    MissingRequiredRolesOrScopesError,
    MissingRequiredScopesError,
    UserNotFoundError,
)
from zen_auth.logger import LOGGER

from .config import ZENAUTH_SERVER_CONFIG
from .persistence.session import get_session
from .usecases import rbac_checks, user_service


class ClaimsSelf(Claims):
    """DB-backed `Claims` implementation.

    Validates JWTs locally and loads users via SQLAlchemy `Session`.
    """

    @classmethod
    def get_user_dto(cls, session: Session, user_name: str) -> UserDTO:
        return user_service.get_user(session, user_name)

    @property
    def auth_user(self) -> UserDTO:
        """Not supported without a DB session; use `ClaimsSelf.guard`."""

        raise RuntimeError("auth_user requires DB session; use ClaimsSelf.guard dependency")

    @classmethod
    def from_user_name(cls, user_name: str) -> Self:
        """Not supported without a DB session; use `ClaimsSelf.guard`."""

        raise RuntimeError("from_user_name requires DB session; use ClaimsSelf.guard dependency")

    @classmethod
    def verify_token(cls, token: str) -> VerifyTokenDTO:
        """Not supported without a DB session; use the `/verify/token` endpoint."""
        raise RuntimeError("verify_token requires DB session; use /verify/token endpoint")

    @classmethod
    def _verify_token_with_session(cls, session: Session, token: str) -> tuple[Self, UserDTO]:
        claims = cls.from_token(token)
        cls._validate_claims(claims)

        user = user_service.get_user(session, claims.sub)
        if claims.policy_epoch < user.policy_epoch:
            raise JWTError("Policy updated")

        now_ts = int(_utcnow().timestamp())
        if claims.exp - now_ts < ZENAUTH_SERVER_CONFIG().refresh_window_sec:
            refreshed = cls.from_user(user).token
            claims = cls.from_token(refreshed)
        return claims, user

    @classmethod
    def role(
        cls,
        *required_roles: str,
        **kwargs: Any,
    ) -> Callable[..., UserDTO]:
        """FastAPI dependency that enforces required roles using local DB state."""

        _ = kwargs
        guard = cls.guard()

        def dep(req: Request, user: UserDTO = Depends(guard)) -> UserDTO:
            roles = [r for r in required_roles if r]
            ok = rbac_checks.has_required_roles(user.roles, roles)
            if not ok:
                log_audit_fail(
                    "Rbac check failed.", user.user_name, user.roles, required_context=roles, request=req
                )
                raise MissingRequiredRolesError(
                    f"Rbac checke failed. (user: {user.user_name})",
                    user_name=user.user_name,
                    roles=set(user.roles),
                    required=roles,
                )
            return user

        return dep

    @classmethod
    def scope(
        cls,
        *required_scopes: str,
        **kwargs: Any,
    ) -> Callable[..., UserDTO]:
        """FastAPI dependency that enforces required scopes using local DB state."""

        _ = kwargs
        guard = cls.guard()

        def dep(
            req: Request,
            user: UserDTO = Depends(guard),
            session: Session = Depends(get_session),
        ) -> UserDTO:
            scopes = [s for s in required_scopes if s]
            if not scopes:
                log_audit_fail(
                    "Scope check failed.", user.user_name, user.roles, required_context=scopes, request=req
                )
                raise MissingRequiredScopesError(
                    f"Scope check failed. (user: {user.user_name})",
                    user_name=user.user_name,
                    roles=set(user.roles),
                    required=scopes,
                )
            ok = rbac_checks.has_required_scopes(session, user.user_name, scopes)
            if ok:
                return user

            log_audit_fail(
                "Scope check failed.", user.user_name, user.roles, required_context=scopes, request=req
            )
            raise MissingRequiredScopesError(
                f"Scope check failed. (user: {user.user_name})",
                user_name=user.user_name,
                roles=set(user.roles),
                required=scopes,
            )

        return dep

    @classmethod
    def role_or_scope(
        cls,
        *,
        roles: Iterable[str] = (),
        scopes: Iterable[str] = (),
        **kwargs: Any,
    ) -> Callable[..., UserDTO]:
        """FastAPI dependency that allows access if either role OR scope matches."""

        _ = kwargs
        role_list = [r for r in roles if r]
        scope_list = [s for s in scopes if s]
        guard = cls.guard()

        def dep(
            req: Request,
            user: UserDTO = Depends(guard),
            session: Session = Depends(get_session),
        ) -> UserDTO:
            ok_role = rbac_checks.has_required_roles(user.roles, role_list) if role_list else False
            ok_scope = (
                rbac_checks.has_required_scopes(session, user.user_name, scope_list) if scope_list else False
            )
            if ok_role or ok_scope:
                return user

            raise MissingRequiredRolesOrScopesError(
                f"Role/scope check failed. (user: {user.user_name})",
                user_name=user.user_name,
                roles=set(user.roles),
                required_roles=role_list,
                required_scopes=scope_list,
            )

        return dep

    @classmethod
    def guard(cls, **kwargs: Any) -> Callable[..., UserDTO]:
        """FastAPI dependency that authenticates a request using local DB state.

        Raises:
            InvalidTokenError: Missing/invalid/expired token.
            ClaimError: Claim validation failures.
        """

        def dep(
            req: Request,
            resp: Response,
            authorization: str | None = Header(default=None),
            session: Session = Depends(get_session),
        ) -> UserDTO:
            claims: Claims | None = None
            user_name = "--"
            try:
                cookie_val = req.cookies.get(ZENAUTH_CONFIG().cookie_name)
                token = cookie_val or _extract_bearer(authorization)

                if not token:
                    raise InvalidTokenError("No token.", kind="no_token")

                claims, user = cls._verify_token_with_session(session, token)
                user_name = claims.sub

                cls.set_cookie(resp, claims.token)

                return user
            except ClaimError:
                raise
            except UserNotFoundError as e:
                raise InvalidTokenError(
                    f"User not found. (user: {user_name})", user_name=user_name, kind="user_not_found"
                ) from e
            except (JWTError, ValueError) as e:
                raise InvalidTokenError(
                    f"Invalid token. (user: {user_name})", user_name=user_name, kind="invalid"
                ) from e
            except Exception as e:
                LOGGER.error(ERROR_UNKNOWN, exc_info=e)
                raise RuntimeError(ERROR_UNKNOWN) from e

        return dep

    @classmethod
    def verify_user(
        cls,
        req: Request,
        resp: Response,
        user_name: str,
        password: str,
        **kwargs: Any,
    ) -> Response:
        """Not used in the server; use `user_service.verify_user` with a Session."""
        raise RuntimeError(
            "ClaimsSelf.verify_user is no longer used; call user_service.verify_user with a Session"
        )
