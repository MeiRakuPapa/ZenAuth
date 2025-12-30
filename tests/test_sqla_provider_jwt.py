# mypy: disable-error-code=no-untyped-def
from typing import cast

import pytest
from jose import jwt
from zen_auth.dto import UserDTOForCreate
from zen_auth.errors import UserVerificationError
from zen_auth.server.persistence.init_db import init_db
from zen_auth.server.persistence.session import (
    create_engine_from_dsn,
    create_sessionmaker,
    session_scope,
)
from zen_auth.server.usecases import user_service

SECRET_KEY = "mysecretkey"
ALGORITHM = "HS256"


def create_jwt(user_name: str, roles: list[str]) -> str:
    payload = {"sub": user_name, "roles": roles}
    return cast(str, jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM))


def decode_jwt(token: str) -> dict:  # type: ignore[type-arg]
    return cast(dict, jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM]))  # type: ignore[type-arg]


def test_sqla_provider_with_jwt():
    dsn = "sqlite:///test_sqla_provider_jwt.db"
    engine = create_engine_from_dsn(dsn)
    init_db(engine)
    session_factory = create_sessionmaker(engine)

    # Create a user
    user_data = UserDTOForCreate(
        user_name="jwt_user",
        password="jwt_password",
        roles=["user"],
        real_name="JWT User",
        division="Test Division",
        description="Test Description",
        policy_epoch=1,
    )
    with session_scope(session_factory) as session:
        user_service.create_user(session, user_data)

    # Verify the user and generate JWT
    with session_scope(session_factory) as session:
        verified_user = user_service.verify_user(session, "jwt_user", "jwt_password")
    token = create_jwt(verified_user.user_name, verified_user.roles)

    # Decode and verify the JWT
    decoded_payload = decode_jwt(token)
    assert decoded_payload["sub"] == "jwt_user"
    assert decoded_payload["roles"] == ["user"]

    # Attempt to verify with incorrect password
    with pytest.raises(UserVerificationError):
        with session_scope(session_factory) as session:
            user_service.verify_user(session, "jwt_user", "wrong_password")

    # Cleanup: Dispose engine and remove DB file
    try:
        engine.dispose()
    except Exception:
        pass
    import os

    os.remove("test_sqla_provider_jwt.db")


if __name__ == "__main__":
    pytest.main()
