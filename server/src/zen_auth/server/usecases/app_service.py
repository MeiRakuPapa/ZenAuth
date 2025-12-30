from __future__ import annotations

from urllib.parse import urlsplit

from sqlalchemy.orm import Session

from ..persistence.models import ClientAppOrm


def _validate_return_to(return_to: str) -> None:
    if not return_to or return_to.strip() == "":
        raise ValueError("return_to cannot be empty")

    # Allow either absolute http(s) URLs or absolute-path redirects.
    if return_to.startswith("/"):
        return

    parts = urlsplit(return_to)
    if parts.scheme not in {"http", "https"} or not parts.netloc:
        raise ValueError("return_to must be an absolute http(s) URL or an absolute path starting with '/'")


def get_return_to_for_app(session: Session, app_id: str) -> str | None:
    if not app_id or app_id.strip() == "":
        return None
    obj = session.get(ClientAppOrm, app_id)
    return obj.return_to if obj is not None else None


def list_apps(session: Session) -> list[ClientAppOrm]:
    return list(session.query(ClientAppOrm).order_by(ClientAppOrm.app_id).all())


def get_app(session: Session, app_id: str) -> ClientAppOrm | None:
    if not app_id or app_id.strip() == "":
        return None
    return session.get(ClientAppOrm, app_id)


def create_app(
    session: Session,
    *,
    app_id: str,
    display_name: str | None,
    description: str | None,
    return_to: str,
) -> ClientAppOrm:
    if not app_id or app_id.strip() == "":
        raise ValueError("app_id cannot be empty")
    if len(app_id) > 255:
        raise ValueError("app_id cannot exceed 255 characters")
    if session.get(ClientAppOrm, app_id) is not None:
        raise ValueError("app already exists")

    _validate_return_to(return_to)

    dn = (display_name or "").strip() or app_id
    obj = ClientAppOrm(app_id=app_id, display_name=dn, description=(description or None), return_to=return_to)
    session.add(obj)
    session.flush()
    return obj


def update_app(
    session: Session,
    *,
    app_id: str,
    display_name: str | None,
    description: str | None,
    return_to: str | None,
) -> ClientAppOrm:
    obj = session.get(ClientAppOrm, app_id)
    if obj is None:
        raise ValueError("app not found")

    if display_name is not None:
        dn = display_name.strip() or app_id
        obj.display_name = dn
    if description is not None:
        obj.description = description or None
    if return_to is not None:
        _validate_return_to(return_to)
        obj.return_to = return_to

    session.flush()
    return obj


def delete_app(session: Session, app_id: str) -> None:
    obj = session.get(ClientAppOrm, app_id)
    if obj is None:
        raise ValueError("app not found")
    session.delete(obj)
    session.flush()


def upsert_app(
    session: Session,
    *,
    app_id: str,
    display_name: str | None = None,
    description: str | None = None,
    return_to: str,
) -> ClientAppOrm:
    if not app_id or app_id.strip() == "":
        raise ValueError("app_id cannot be empty")
    if len(app_id) > 255:
        raise ValueError("app_id cannot exceed 255 characters")

    _validate_return_to(return_to)

    dn = (display_name or "").strip() or app_id

    obj = session.get(ClientAppOrm, app_id)
    if obj is None:
        obj = ClientAppOrm(
            app_id=app_id, display_name=dn, description=(description or None), return_to=return_to
        )
        session.add(obj)
    else:
        obj.display_name = dn
        obj.description = description or None
        obj.return_to = return_to
    session.flush()
    return obj
