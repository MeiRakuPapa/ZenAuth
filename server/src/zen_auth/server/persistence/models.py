from __future__ import annotations

import datetime as DT

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Table, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_name", String(255), ForeignKey("users.user_name"), primary_key=True),
    Column("role_name", String(255), ForeignKey("roles.role_name"), primary_key=True),
)


role_scopes = Table(
    "role_scopes",
    Base.metadata,
    Column("role_name", String(255), ForeignKey("roles.role_name"), primary_key=True),
    Column("scope_name", String(255), ForeignKey("scopes.scope_name"), primary_key=True),
)


class UserOrm(Base):
    __tablename__ = "users"

    user_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    password: Mapped[str] = mapped_column(String(255), nullable=False)

    real_name: Mapped[str] = mapped_column(String, nullable=False, default="")
    division: Mapped[str] = mapped_column(String, nullable=False, default="")
    description: Mapped[str] = mapped_column(String, nullable=False, default="")
    policy_epoch: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    created_at: Mapped[DT.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[DT.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    roles: Mapped[list[RoleOrm]] = relationship(
        "RoleOrm",
        secondary=user_roles,
        back_populates="users",
        lazy="selectin",
    )


class RoleOrm(Base):
    __tablename__ = "roles"

    role_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)

    created_at: Mapped[DT.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[DT.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    users: Mapped[list[UserOrm]] = relationship(
        "UserOrm",
        secondary=user_roles,
        back_populates="roles",
        lazy="selectin",
    )

    scopes: Mapped[list[ScopeOrm]] = relationship(
        "ScopeOrm",
        secondary=role_scopes,
        back_populates="roles",
        lazy="selectin",
    )


class ScopeOrm(Base):
    __tablename__ = "scopes"

    scope_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)

    created_at: Mapped[DT.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[DT.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    roles: Mapped[list[RoleOrm]] = relationship(
        "RoleOrm",
        secondary=role_scopes,
        back_populates="scopes",
        lazy="selectin",
    )


class ClientAppOrm(Base):
    __tablename__ = "client_apps"

    app_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    return_to: Mapped[str] = mapped_column(String, nullable=False)

    created_at: Mapped[DT.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[DT.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
