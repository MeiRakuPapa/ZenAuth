from faker import Faker
from zen_auth.dto import UserDTOForCreate

from ..zen_auth.server.persistence.init_db import init_db
from ..zen_auth.server.persistence.session import (
    create_engine_from_dsn,
    create_sessionmaker,
    session_scope,
)
from ..zen_auth.server.usecases import user_service


def create_dummy_users(db_path: str, user_count: int = 100) -> None:
    fake = Faker()

    engine = create_engine_from_dsn(f"sqlite:///{db_path}")
    init_db(engine)
    session_factory = create_sessionmaker(engine)

    for i in range(user_count):
        password = fake.password()
        user_data = UserDTOForCreate(
            user_name=f"user_{i + 1}",
            password=password,
            roles=["user"],
            real_name=fake.name(),
            division=fake.company(),
            description=f"Password: {password}",
            policy_epoch=1,
        )
        with session_scope(session_factory) as session:
            user_service.create_user(session, user_data)

    print(f"Created {user_count} dummy users in {db_path}")


if __name__ == "__main__":
    create_dummy_users("dummy_users.db", user_count=100)
