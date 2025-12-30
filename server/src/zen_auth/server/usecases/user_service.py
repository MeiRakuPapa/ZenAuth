from __future__ import annotations

import datetime as DT

from passlib.context import CryptContext
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from zen_auth.dto import UserDTO, UserDTOForCreate, UserDTOForUpdate
from zen_auth.errors import (
    UserAlreadyExistsError,
    UserNotFoundError,
    UserVerificationError,
)

from ..persistence.models import RoleOrm, UserOrm

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _iso(dt: DT.datetime | None) -> str | None:
    return dt.isoformat() if dt is not None else None


def _ensure_roles(session: Session, role_names: list[str]) -> list[RoleOrm]:
    roles: list[RoleOrm] = []
    for rn in role_names:
        role = session.get(RoleOrm, rn)
        if role is None:
            role = RoleOrm(role_name=rn, display_name=rn)
            session.add(role)
            session.flush()
        roles.append(role)
    return roles


def user_to_dto(user: UserOrm) -> UserDTO:
    return UserDTO(
        user_name=user.user_name,
        password=None,
        roles=[r.role_name for r in user.roles],
        real_name=user.real_name,
        division=user.division,
        description=user.description,
        policy_epoch=user.policy_epoch,
        created_at=_iso(user.created_at),
        updated_at=_iso(user.updated_at),
    )


def get_user(session: Session, user_name: str) -> UserDTO:
    user = session.get(UserOrm, user_name)
    if user is None:
        raise UserNotFoundError(f"User not found: {user_name}", user_name=user_name)
    return user_to_dto(user)


def list_users_page(session: Session, page: int = 1, page_size: int = 50) -> tuple[int, list[UserDTO]]:
    count = session.execute(select(func.count()).select_from(UserOrm)).scalar_one()
    num_pages = (count - 1) // page_size + 1 if count else 1

    users = session.scalars(
        select(UserOrm).order_by(UserOrm.user_name).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return num_pages, [user_to_dto(u) for u in users]


def create_user(session: Session, user: UserDTOForCreate, *, already_hashed: bool = False) -> UserDTO:
    if not user.user_name or user.user_name.strip() == "":
        raise ValueError("Username cannot be empty or whitespace.")
    if len(user.user_name) > 255:
        raise ValueError("Username cannot exceed 255 characters.")
    if not user.password or user.password.strip() == "":
        raise ValueError("Password cannot be empty or whitespace.")

    if session.get(UserOrm, user.user_name) is not None:
        raise UserAlreadyExistsError(f"User already exists: {user.user_name}")

    roles = _ensure_roles(session, user.roles)

    obj = UserOrm(
        user_name=user.user_name,
        password=user.password if already_hashed else pwd_ctx.hash(user.password),
        real_name=user.real_name,
        division=user.division,
        description=user.description,
        policy_epoch=user.policy_epoch,
        roles=roles,
    )
    session.add(obj)
    session.flush()
    return user_to_dto(obj)


def update_user(session: Session, user: UserDTOForUpdate, *, already_hashed: bool = False) -> UserDTO:
    obj = session.get(UserOrm, user.user_name)
    if obj is None:
        raise UserNotFoundError(f"User not found: {user.user_name}", user_name=user.user_name)

    epoch_change = False
    if user.password is not None:
        obj.password = user.password if already_hashed else pwd_ctx.hash(user.password)
        epoch_change = True
    if user.roles is not None:
        obj.roles = _ensure_roles(session, user.roles)
        epoch_change = True
    if user.division is not None:
        obj.division = user.division
        epoch_change = True

    if user.real_name is not None:
        obj.real_name = user.real_name
    if user.description is not None:
        obj.description = user.description

    if epoch_change:
        obj.policy_epoch += 1

    session.flush()
    return user_to_dto(obj)


def delete_user(session: Session, user_name: str) -> None:
    obj = session.get(UserOrm, user_name)
    if obj is None:
        raise UserNotFoundError(f"User not found: {user_name}", user_name=user_name)
    session.delete(obj)
    session.flush()


def verify_user(session: Session, user_name: str, password: str) -> UserDTO:
    obj = session.get(UserOrm, user_name)
    if obj is None:
        raise UserNotFoundError(f"User not found: {user_name}", user_name=user_name)
    if not pwd_ctx.verify(password, obj.password):
        raise UserVerificationError(f"Invalid credentials: {user_name}", user_name=user_name)
    return user_to_dto(obj)


def change_password(session: Session, user_name: str, new_password: str) -> UserDTO:
    if not new_password or new_password.strip() == "":
        raise ValueError("Password cannot be empty or whitespace.")

    obj = session.get(UserOrm, user_name)
    if obj is None:
        raise UserNotFoundError(f"User not found: {user_name}", user_name=user_name)

    obj.password = pwd_ctx.hash(new_password)
    obj.policy_epoch += 1
    session.flush()
    return user_to_dto(obj)
