import datetime as DT
import json
import time
from threading import Lock
from typing import Any, Callable, ClassVar, Iterable, Literal, TypeVar, cast
from urllib.parse import urlencode

import requests
from fastapi import Depends, Header, status
from fastapi.requests import Request
from fastapi.responses import Response
from jose import JWTError, jwt
from pydantic import BaseModel, PrivateAttr
from requests import exceptions as req_exc
from typing_extensions import Self

from ..config import ZENAUTH_CONFIG
from ..dto import UserDTO, VerifyTokenDTO
from ..errors import (
    ClaimError,
    ClaimSourceError,
    ClaimValidationError,
    InvalidCredentialsError,
    InvalidTokenError,
    MissingRequiredRolesError,
    MissingRequiredRolesOrScopesError,
    MissingRequiredScopesError,
    UserVerificationError,
)
from ..logger import AUDIT_LOGGER, LOGGER

TokenType = Literal["access"]

_RespT = TypeVar("_RespT", bound=Response)


# Define common error messages
ERROR_UNKNOWN = "An unknown error occurred."


def _as_dict(value: object, *, message: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ClaimSourceError(message, code="invalid_data")
    return value


def _extract_bool_field(data: dict[str, object], field: str, *, message: str) -> bool:
    value = data.get(field)
    if not isinstance(value, bool):
        raise ClaimSourceError(message, code="invalid_data")
    return value


def _build_role_or_scope_dep(
    cls: type["Claims"],
    guard: Callable[..., UserDTO],
    role_list: list[str],
    scope_list: list[str],
    *,
    role_url: str | None,
    scope_url: str | None,
    role_or_scope_url: str | None = None,
) -> Callable[..., UserDTO]:
    def dep(req: Request, user: UserDTO = Depends(guard)) -> UserDTO:
        return cls._role_or_scope_check(
            req,
            user,
            role_list=role_list,
            scope_list=scope_list,
            role_url=role_url,
            scope_url=scope_url,
            role_or_scope_url=role_or_scope_url,
        )

    return dep


def _token_data(req: Request) -> dict[str, str] | None:
    identity_config = ZENAUTH_CONFIG()
    token = req.cookies.get(identity_config.cookie_name) or _extract_bearer(req.headers.get("authorization"))
    if not token:
        return None
    try:
        token_data = jwt.decode(token, identity_config.secret_key, algorithms=[identity_config.algorithm])
        return cast(dict[str, str], token_data)
    except JWTError:
        return None


def log_audit_success(
    msg: str,
    user_name: str,
    roles: Iterable[str] | None = None,
    required_context: object = None,
    request: Request | None = None,
    include_token: bool = True,
) -> None:
    """Write a success entry to the audit logger.

    Args:
        msg: Human readable message.
        user_name: The username associated with the event.
        roles: The user's roles if available.
        required_context: Context for the operation (roles, scopes, etc).
        request: Optional Request object for additional context.
    """

    AUDIT_LOGGER.info(
        msg,
        extra={
            "user_name": user_name,
            "roles": roles,
            "result": "success",
            "required_context": required_context,
            "request": request,
            "token": _token_data(request) if (include_token and request) else None,
        },
    )


def log_audit_fail(
    msg: str,
    user_name: str,
    roles: Iterable[str] | None = None,
    required_context: object = None,
    request: Request | None = None,
    include_token: bool = True,
) -> None:
    """Write a failure entry to the audit logger.

    Args:
        msg: Human readable message.
        user_name: The username associated with the event.
        roles: The user's roles if available.
        required_context: Context for the operation (roles, scopes, etc).
        request: Optional Request object for additional context.
    """

    AUDIT_LOGGER.info(
        msg,
        extra={
            "user_name": user_name,
            "roles": roles,
            "result": "failure",
            "required_context": required_context,
            "request": request,
            "token": _token_data(request) if (include_token and request) else None,
        },
    )


class Claims(BaseModel):
    """JWT claims model with helper utilities.

    This model also provides FastAPI dependencies (`guard`, `role`, `scope`) for
    validating tokens and enforcing authorization.
    """

    class TokenDTO(BaseModel):
        token: str

    class UserPassDTO(BaseModel):
        user_name: str
        password: str

    _GET: ClassVar[Callable[..., requests.Response]] = requests.get
    _POST: ClassVar[Callable[..., requests.Response]] = requests.post

    _ENDPOINTS_CACHE_TTL_SEC: ClassVar[float] = 300.0
    _endpoints_cache_lock: ClassVar[Lock] = Lock()
    _endpoints_cache: ClassVar[dict[str, tuple[float, dict[str, str]]]] = {}

    typ: TokenType
    sub: str
    policy_epoch: int
    iat: int
    exp: int

    _auth_user: UserDTO | None = PrivateAttr(default=None)

    @property
    def username(self) -> str:
        """Return the subject (username) from the claims."""
        return self.sub

    @classmethod
    def from_user(cls, user: UserDTO) -> Self:
        """Create claims for a user using the current expiry configuration."""

        now = _utcnow()
        expire = now + DT.timedelta(minutes=ZENAUTH_CONFIG().expire_min)
        return cls(
            typ="access",
            sub=user.user_name,
            policy_epoch=user.policy_epoch,
            iat=int(now.timestamp()),
            exp=int(expire.timestamp()),
        )

    @classmethod
    def from_request(cls, req: Request) -> Self | None:
        """Create claims from a request.

        Returns `None` if no token is present. If a token is present but invalid,
        this method raises.
        """

        token = req.cookies.get(ZENAUTH_CONFIG().cookie_name) or _extract_bearer(
            req.headers.get("authorization")
        )
        return cls.from_token(token) if token is not None else None

    @classmethod
    def from_token(cls, token: str) -> Self:
        """Decode a JWT and validate it into a `Claims` instance.

        Raises:
            JWTError: If the JWT cannot be decoded/verified.
            pydantic.ValidationError: If the payload does not match the model.
        """

        data = jwt.decode(token, ZENAUTH_CONFIG().secret_key, algorithms=[ZENAUTH_CONFIG().algorithm])
        return cls.model_validate(data)

    @property
    def token(self) -> str:
        """Return an encoded JWT for these claims."""

        return cast(
            str,
            jwt.encode(self.model_dump(), ZENAUTH_CONFIG().secret_key, algorithm=ZENAUTH_CONFIG().algorithm),
        )

    @classmethod
    def _gen_url(cls, req: Request, path: str) -> str:
        # If an auth-server origin is configured, generate URLs against it.
        # This avoids assuming the auth server shares the same host as the
        # incoming request (common in microservice deployments).
        origin = ZENAUTH_CONFIG().auth_server_origin
        if origin is not None and origin.strip():
            origin = origin.rstrip("/")
            return f"{origin}/{path.lstrip('/')}"

        port = f":{req.url.port}" if req.url.port else ""
        path = path.lstrip("/")
        return f"{req.url.scheme}://{req.url.hostname}{port}/{path}"

    @classmethod
    def login_page_url(
        cls,
        req: Request,
        *,
        app_id: str | None = None,
        title: str | None = None,
    ) -> str:
        """Build the auth-server login page URL.

        This is a convenience helper for WebApps that want to redirect users to
        the ZenAuth login UI.

        The resulting URL points to the auth server's login page endpoint.

        For security (open redirect prevention), the login page does not accept
        a user-controlled return destination URL. Instead, pass `app_id` and
        let the auth server resolve the post-login destination.
        """

        endpoints = cls._peek_cached_endpoints(req)
        base = (
            endpoints["login_page"]
            if endpoints and "login_page" in endpoints
            else cls._endpoint_url(req, "login_page")
        )
        params: dict[str, str] = {}
        if app_id is not None:
            params["app_id"] = app_id
        if title is not None:
            params["title"] = title
        qs = urlencode(params)
        return f"{base}?{qs}" if qs else base

    @classmethod
    def _endpoints_discovery_url(cls, req: Request) -> str:
        # Server-side discovery endpoint.
        # (Default path: `/zen_auth/v1/meta/endpoints`)
        return cls._gen_url(req, "/zen_auth/v1/meta/endpoints")

    @classmethod
    def _peek_cached_endpoints(cls, req: Request) -> dict[str, str] | None:
        """Return cached endpoints if present/fresh, without performing discovery."""

        discovery_url = cls._endpoints_discovery_url(req)
        now = time.monotonic()
        with cls._endpoints_cache_lock:
            cached = cls._endpoints_cache.get(discovery_url)
            if cached is None:
                return None
            cached_at, cached_endpoints = cached
            if now - cached_at <= cls._ENDPOINTS_CACHE_TTL_SEC:
                return cached_endpoints
            return None

    @classmethod
    def _get_cached_endpoints(cls, req: Request) -> dict[str, str]:
        """Return cached endpoint URLs discovered from the auth server.

        The discovery call is cached process-wide for a short TTL.
        """

        discovery_url = cls._endpoints_discovery_url(req)
        now = time.monotonic()

        with cls._endpoints_cache_lock:
            cached = cls._endpoints_cache.get(discovery_url)
            if cached is not None:
                cached_at, cached_endpoints = cached
                if now - cached_at <= cls._ENDPOINTS_CACHE_TTL_SEC:
                    return cached_endpoints

        try:
            res = cls._GET(discovery_url, timeout=3.0)
        except req_exc.Timeout as e:
            raise ClaimSourceError("Auth server timeout", code="timeout") from e
        except req_exc.ConnectionError as e:
            raise ClaimSourceError("Auth server connection error", code="connection") from e
        except Exception as e:
            raise ClaimSourceError(ERROR_UNKNOWN, code="internal") from e

        if res.status_code != status.HTTP_200_OK:
            raise ClaimSourceError(
                "Auth server returned non-200 for endpoints discovery",
                code="invalid_data",
                info={"status_code": res.status_code, "url": discovery_url},
            )

        try:
            payload = res.json()
        except Exception as e:
            raise ClaimSourceError("Auth server returned invalid data", code="invalid_data") from e

        if not isinstance(payload, dict):
            raise ClaimSourceError("Auth server returned invalid data", code="invalid_data")
        data = payload.get("data")
        if not isinstance(data, dict):
            raise ClaimSourceError("Auth server returned invalid data", code="invalid_data")

        discovered: dict[str, str] = {}
        for k, v in data.items():
            if isinstance(k, str) and isinstance(v, str) and v.strip():
                discovered[k] = v

        required = {"verify_token", "verify_user", "verify_user_role", "verify_user_scope"}
        missing = sorted(required.difference(discovered.keys()))
        if missing:
            raise ClaimSourceError(
                "Auth server returned incomplete endpoints data",
                code="invalid_data",
                info={"missing": missing},
            )

        with cls._endpoints_cache_lock:
            cls._endpoints_cache[discovery_url] = (now, discovered)

        return discovered

    @classmethod
    def _endpoint_url(cls, req: Request, key: str) -> str:
        endpoints = cls._get_cached_endpoints(req)
        url = endpoints.get(key)
        if url is None:
            raise ClaimSourceError(
                "Auth server discovery missing endpoint",
                code="invalid_data",
                info={"key": key},
            )
        return url

    @classmethod
    def _get_token(cls, req: Request, authorization: str | None) -> str | None:
        return req.cookies.get(ZENAUTH_CONFIG().cookie_name) or _extract_bearer(authorization)

    @classmethod
    def _validate_token(cls, token: str) -> Self:
        if not token:
            raise InvalidTokenError("No token.")
        return cls.from_token(token)

    @classmethod
    def _validate_claims(cls, claims: Self) -> None:
        if claims.typ != "access":
            raise ClaimValidationError("Wrong jwt type")

        checks = {"sub": str, "exp": int, "policy_epoch": int, "iat": int}

        for field, typ in checks.items():
            if not isinstance(getattr(claims, field), typ):
                raise ClaimValidationError(
                    f"Invalid jwt payload: {field} must be {typ.__name__}", field=field
                )

    @classmethod
    def clear_cookie(cls, resp: "_RespT") -> "_RespT":
        """Delete the auth cookie from the response and return it."""
        resp.delete_cookie(ZENAUTH_CONFIG().cookie_name, path="/")
        return resp

    @classmethod
    def set_cookie(cls, resp: "_RespT", token: str) -> "_RespT":
        """Set the auth cookie on the response and return it."""

        resp.set_cookie(
            key=ZENAUTH_CONFIG().cookie_name,
            value=token,
            httponly=True,
            secure=ZENAUTH_CONFIG().secure,
            samesite=ZENAUTH_CONFIG().samesite,
            max_age=ZENAUTH_CONFIG().max_age,
            path="/",
        )
        return resp

    @staticmethod
    def logout(response: Response) -> None:
        """Convenience alias for `clear_cookie`."""
        Claims.clear_cookie(response)

    @classmethod
    def role(
        cls,
        *required_roles: str,
        **kwargs: Any,
    ) -> Callable[..., UserDTO]:
        """FastAPI dependency that enforces required roles.

        The user must have at least one of the specified roles (OR).

        Optional kwargs:
            url: Override `/verify/token` endpoint URL.
            role_url / rbac_url: Override `/verify/user/role` endpoint URL.
        """
        token_url = kwargs.get("url", None)
        role_url = kwargs.get("role_url", None) or kwargs.get("rbac_url", None)
        guard = cls.guard(url=token_url)

        def _verify_roles(req: Request, user_name: str) -> bool:
            nonlocal role_url
            if role_url is None:
                role_url = cls._endpoint_url(
                    req,
                    "verify_user_role",
                )

            roles = [r for r in required_roles if r]
            res = cls._POST(
                role_url,
                timeout=3.0,
                json={"user_name": user_name, "required_roles": roles},
            )
            if res.status_code == status.HTTP_403_FORBIDDEN:
                return False
            if res.status_code != status.HTTP_200_OK:
                raise ClaimSourceError(
                    "Auth server returned non-200 for role verify",
                    code="invalid_data",
                    info={"status_code": res.status_code},
                )

            res_dict: dict[str, object] = res.json()
            data = res_dict.get("data")
            if not isinstance(data, dict):
                raise ClaimSourceError("Auth server returned invalid data", code="invalid_data")
            has_role = data.get("has_role")
            if not isinstance(has_role, bool):
                raise ClaimSourceError("Auth server returned invalid data", code="invalid_data")
            return has_role

        def dep(req: Request, user: UserDTO = Depends(guard)) -> UserDTO:
            roles = [r for r in required_roles if r]
            if not roles:
                log_audit_fail(
                    "Role check failed.", user.user_name, user.roles, required_context=roles, request=req
                )
                raise MissingRequiredRolesError(
                    f"Role check failed. (user: {user.user_name})",
                    user_name=user.user_name,
                    roles=set(user.roles),
                    required=roles,
                )

            try:
                if _verify_roles(req, user.user_name):
                    return user

                log_audit_fail(
                    "Role check failed.", user.user_name, user.roles, required_context=roles, request=req
                )
                raise MissingRequiredRolesError(
                    f"Role check failed. (user: {user.user_name})",
                    user_name=user.user_name,
                    roles=set(user.roles),
                    required=roles,
                )
            except ClaimError:
                raise
            except req_exc.Timeout as e:
                raise ClaimSourceError("Auth server timeout", code="timeout") from e
            except req_exc.ConnectionError as e:
                raise ClaimSourceError("Auth server connection error", code="connection") from e
            except (ValueError, KeyError, json.JSONDecodeError) as e:
                raise ClaimSourceError("Auth server returned invalid data", code="invalid_data") from e
            except Exception as e:
                LOGGER.error(ERROR_UNKNOWN, exc_info=e)
                raise ClaimSourceError(ERROR_UNKNOWN, code="internal") from e

        return dep

    @classmethod
    def scope(
        cls,
        *required_scopes: str,
        **kwargs: Any,
    ) -> Callable[..., UserDTO]:
        """FastAPI dependency that enforces required scopes.

        The user must have at least one of the specified scopes (OR).

        Optional kwargs:
            url: Override `/verify/token` endpoint URL.
            scope_url: Override `/verify/user/scope` endpoint URL.
        """
        token_url = kwargs.get("url", None)
        scope_url = kwargs.get("scope_url", None)
        guard = cls.guard(url=token_url)

        def _user_allowed_any_scope(req: Request, user_name: str) -> bool:
            nonlocal scope_url
            if scope_url is None:
                scope_url = cls._endpoint_url(
                    req,
                    "verify_user_scope",
                )

            scopes = [s for s in required_scopes if s]
            res = cls._POST(
                scope_url,
                timeout=3.0,
                json={"user_name": user_name, "required_scopes": scopes},
            )
            if res.status_code == status.HTTP_403_FORBIDDEN:
                return False
            if res.status_code != status.HTTP_200_OK:
                raise ClaimSourceError(
                    "Auth server returned non-200 for scope verify",
                    code="invalid_data",
                    info={"status_code": res.status_code},
                )

            res_dict: dict[str, object] = res.json()
            data = res_dict.get("data")
            if not isinstance(data, dict):
                raise ClaimSourceError("Auth server returned invalid data", code="invalid_data")
            allowed = data.get("allowed")
            if not isinstance(allowed, bool):
                raise ClaimSourceError("Auth server returned invalid data", code="invalid_data")
            return allowed

        def dep(req: Request, user: UserDTO = Depends(guard)) -> UserDTO:
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

            try:
                if _user_allowed_any_scope(req, user.user_name):
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
            except ClaimError:
                raise
            except req_exc.Timeout as e:
                raise ClaimSourceError("Auth server timeout", code="timeout") from e
            except req_exc.ConnectionError as e:
                raise ClaimSourceError("Auth server connection error", code="connection") from e
            except (ValueError, KeyError, json.JSONDecodeError) as e:
                raise ClaimSourceError("Auth server returned invalid data", code="invalid_data") from e
            except Exception as e:
                LOGGER.error(ERROR_UNKNOWN, exc_info=e)
                raise ClaimSourceError(ERROR_UNKNOWN, code="internal") from e

        return dep

    @classmethod
    def role_or_scope(
        cls,
        *,
        roles: Iterable[str] = (),
        scopes: Iterable[str] = (),
        **kwargs: Any,
    ) -> Callable[..., UserDTO]:
        """FastAPI dependency that allows access if either role OR scope matches.

        This is useful when you want a single dependency for endpoints that can
        be accessed by either privileged roles or specific scopes.

        Args:
            roles: Allowed roles (any-of).
            scopes: Allowed scopes (any-of).
        """

        role_list = [r for r in roles if r]
        scope_list = [s for s in scopes if s]

        token_url = kwargs.get("url", None)
        role_url = kwargs.get("role_url", None) or kwargs.get("rbac_url", None)
        scope_url = kwargs.get("scope_url", None)
        role_or_scope_url = kwargs.get("role_or_scope_url", None)
        guard = cls.guard(url=token_url)

        return _build_role_or_scope_dep(
            cls,
            guard,
            role_list,
            scope_list,
            role_url=role_url,
            scope_url=scope_url,
            role_or_scope_url=role_or_scope_url,
        )

    @classmethod
    def _verify_user_roles_any(
        cls,
        req: Request,
        user_name: str,
        role_list: list[str],
        *,
        role_url: str | None,
    ) -> bool:
        if not role_list:
            return False

        url = role_url or cls._endpoint_url(req, "verify_user_role")
        res = cls._POST(url, timeout=3.0, json={"user_name": user_name, "required_roles": role_list})
        if res.status_code == status.HTTP_403_FORBIDDEN:
            return False
        if res.status_code != status.HTTP_200_OK:
            raise ClaimSourceError(
                "Auth server returned non-200 for role verify",
                code="invalid_data",
                info={"status_code": res.status_code},
            )

        res_dict = _as_dict(res.json(), message="Auth server returned invalid data")
        data = _as_dict(res_dict.get("data"), message="Auth server returned invalid data")
        return _extract_bool_field(data, "has_role", message="Auth server returned invalid data")

    @classmethod
    def _verify_user_scopes_any(
        cls,
        req: Request,
        user_name: str,
        scope_list: list[str],
        *,
        scope_url: str | None,
    ) -> bool:
        if not scope_list:
            return False

        url = scope_url or cls._endpoint_url(req, "verify_user_scope")
        res = cls._POST(url, timeout=3.0, json={"user_name": user_name, "required_scopes": scope_list})
        if res.status_code == status.HTTP_403_FORBIDDEN:
            return False
        if res.status_code != status.HTTP_200_OK:
            raise ClaimSourceError(
                "Auth server returned non-200 for scope verify",
                code="invalid_data",
                info={"status_code": res.status_code},
            )

        res_dict = _as_dict(res.json(), message="Auth server returned invalid data")
        data = _as_dict(res_dict.get("data"), message="Auth server returned invalid data")
        return _extract_bool_field(data, "allowed", message="Auth server returned invalid data")

    @classmethod
    def _role_or_scope_check(
        cls,
        req: Request,
        user: UserDTO,
        *,
        role_list: list[str],
        scope_list: list[str],
        role_url: str | None,
        scope_url: str | None,
        role_or_scope_url: str | None,
    ) -> UserDTO:
        if not role_list and not scope_list:
            raise MissingRequiredRolesOrScopesError(
                f"Role/scope check failed. (user: {user.user_name})",
                user_name=user.user_name,
                roles=set(user.roles),
                required_roles=role_list,
                required_scopes=scope_list,
            )

        try:
            combined_url = role_or_scope_url
            if combined_url is None:
                endpoints = cls._get_cached_endpoints(req)
                combined_url = endpoints.get("verify_user_role_or_scope")

            if combined_url:
                res = cls._POST(
                    combined_url,
                    timeout=3.0,
                    json={
                        "user_name": user.user_name,
                        "required_roles": role_list,
                        "required_scopes": scope_list,
                    },
                )
                if res.status_code == status.HTTP_200_OK:
                    has_access = True
                elif res.status_code == status.HTTP_403_FORBIDDEN:
                    has_access = False
                else:
                    raise ClaimSourceError(
                        "Auth server returned unexpected status for role_or_scope verify",
                        code="invalid_data",
                        info={"status_code": res.status_code},
                    )
            else:
                has_access = cls._verify_user_roles_any(
                    req, user.user_name, role_list, role_url=role_url
                ) or cls._verify_user_scopes_any(req, user.user_name, scope_list, scope_url=scope_url)

            if has_access:
                log_audit_success(
                    "Role/scope check success.",
                    user.user_name,
                    user.roles,
                    required_context={"roles": role_list, "scopes": scope_list},
                    request=req,
                )
                return user

            log_audit_fail(
                "Role/scope check failed.",
                user.user_name,
                user.roles,
                required_context={"roles": role_list, "scopes": scope_list},
                request=req,
            )
            raise MissingRequiredRolesOrScopesError(
                f"Role/scope check failed. (user: {user.user_name})",
                user_name=user.user_name,
                roles=set(user.roles),
                required_roles=role_list,
                required_scopes=scope_list,
            )
        except ClaimError:
            raise
        except req_exc.Timeout as e:
            raise ClaimSourceError("Auth server timeout", code="timeout") from e
        except req_exc.ConnectionError as e:
            raise ClaimSourceError("Auth server connection error", code="connection") from e
        except (ValueError, KeyError, json.JSONDecodeError) as e:
            raise ClaimSourceError("Auth server returned invalid data", code="invalid_data") from e
        except Exception as e:
            LOGGER.error(ERROR_UNKNOWN, exc_info=e)
            raise ClaimSourceError(ERROR_UNKNOWN, code="internal") from e

    @classmethod
    def guard(cls, **kwargs: Any) -> Callable[..., UserDTO]:
        """FastAPI dependency that authenticates a request.

        By default this calls the configured `/verify/token` endpoint, refreshes
        the cookie, and returns an authenticated `UserDTO`.

        Optional kwargs:
            url: Override the `/verify/token` endpoint URL.
        """
        url = kwargs.get("url", None)

        def dep(
            req: Request,
            resp: Response,
            authorization: str | None = Header(default=None),
        ) -> UserDTO:
            nonlocal url
            claims: Claims | None = None
            user_name: str = "--"
            try:
                if url is None:
                    url = cls._endpoint_url(
                        req,
                        "verify_token",
                    )

                token = cls._get_token(req, authorization)
                if not token:
                    raise InvalidTokenError("No token.", kind="no_token")
                claims = cls._validate_token(token)
                user_name = claims.username

                res = cls._POST(url, timeout=3.0, json={"token": token})
                if res.status_code != status.HTTP_200_OK:
                    raise InvalidTokenError(f"Invalid token. (user: {user_name})", user_name=user_name)

                res_dict: dict[str, object] = res.json()
                res_dto = VerifyTokenDTO.model_validate(res_dict["data"])

                cls.set_cookie(resp, res_dto.token)
                return res_dto.user
            except ClaimError:
                raise
            except req_exc.Timeout as e:
                raise ClaimSourceError("Auth server timeout", code="timeout") from e
            except req_exc.ConnectionError as e:
                raise ClaimSourceError("Auth server connection error", code="connection") from e
            except (JWTError, ValueError) as e:
                raise InvalidTokenError(f"{e}", kind="invalid") from e
            except (ValueError, KeyError, json.JSONDecodeError) as e:
                resp_text = None
                try:
                    resp_text = res.text
                except Exception:
                    resp_text = None
                raise ClaimSourceError(
                    "Auth server returned invalid data",
                    code="invalid_data",
                    info={"body": resp_text},
                ) from e
            except Exception as e:
                LOGGER.error(ERROR_UNKNOWN, exc_info=e)
                raise ClaimSourceError(ERROR_UNKNOWN, code="internal") from e

        return dep

    @classmethod
    def verify_user(
        cls,
        req: Request,
        resp: Response,
        user_name: str,
        password: str,
        **kwargs: Any,
        # url: str | None = None,
    ) -> Response:
        """Verify username/password via the `/verify/user` endpoint.

        On success, sets the auth cookie on `resp` and returns it.

        Optional kwargs:
            url: Override the `/verify/user` endpoint URL.
        """
        url = kwargs.get("url", None)
        try:
            if url is None:
                url = cls._endpoint_url(
                    req,
                    "verify_user",
                )

            res = cls._POST(url, timeout=3.0, json=dict(user_name=user_name, password=password))
            if res.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR:
                msg = f"Auth server internal error during user verification. (user: {user_name})"
                LOGGER.critical(msg)
                raise ClaimSourceError(msg, code="internal", info={"status_code": res.status_code})
            if res.status_code != status.HTTP_200_OK:
                raise InvalidCredentialsError(
                    f"Invalid user or password. (user: {user_name})",
                    user_name=user_name,
                    info={"user": user_name},
                )
            res_dict: dict[str, object] = res.json()
            res_dto = Claims.TokenDTO.model_validate(res_dict["data"])
            return cls.set_cookie(resp, res_dto.token)
        except UserVerificationError as e:
            raise InvalidCredentialsError(
                f"Invalid user or password. (user: {user_name})",
                user_name=user_name,
                info={"user": user_name},
            ) from e
        except req_exc.Timeout as e:
            raise ClaimSourceError("Auth server timeout", code="timeout") from e
        except req_exc.ConnectionError as e:
            raise ClaimSourceError("Auth server connection error", code="connection") from e
        except (ValueError, KeyError, json.JSONDecodeError) as e:
            resp_text = None
            try:
                resp_text = res.text
            except Exception:
                resp_text = None
            raise ClaimSourceError(
                "Auth server returned invalid data",
                code="invalid_data",
                info={"body": resp_text},
            ) from e
        except Exception as e:
            LOGGER.error(ERROR_UNKNOWN, exc_info=e)
            raise ClaimSourceError(ERROR_UNKNOWN, code="internal") from e


def _utcnow() -> DT.datetime:
    return DT.datetime.now(DT.timezone.utc)


def _extract_bearer(v: str | None) -> str | None:
    if not v:
        return None
    try:
        scheme, token = v.strip().split(" ", 1)
    except ValueError:
        return None
    return token if scheme.lower() == "bearer" and token else None
