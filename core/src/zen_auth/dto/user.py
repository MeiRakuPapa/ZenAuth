"""User-related DTOs and protocols."""

from typing import Iterable, Protocol, runtime_checkable

from pydantic import BaseModel


class UserDTO(BaseModel):
    """User DTO used across API/service/persistence layers."""

    user_name: str
    password: str | None = None
    roles: list[str]
    real_name: str
    division: str
    description: str
    policy_epoch: int
    created_at: str | None = None
    updated_at: str | None = None

    def __str__(self) -> str:
        return f"#<User {self.user_name}: roles={self.roles}>"

    def __repr__(self) -> str:
        return self.__str__()


class UserDTOForCreate(BaseModel):
    """Input DTO for creating a user."""

    user_name: str
    password: str
    roles: list[str]
    real_name: str = ""
    division: str = ""
    description: str = ""
    policy_epoch: int = 1

    def __str__(self) -> str:
        return f"#<UserCreate {self.user_name}: roles={self.roles}>"

    def __repr__(self) -> str:
        return self.__str__()


class UserDTOForUpdate(BaseModel):
    """Input DTO for updating a user (partial fields)."""

    user_name: str
    password: str | None = None
    roles: list[str] | None = None
    real_name: str | None = None
    division: str | None = None
    description: str | None = None

    def __str__(self) -> str:
        return f"#<UserUpdate {self.user_name}: roles={self.roles}>"

    def __repr__(self) -> str:
        return self.__str__()


@runtime_checkable
class UserOperationProtocol(Protocol):
    def all(self) -> Iterable[UserDTO]: ...
    def all_page(self, page: int = 1, page_size: int = 50) -> tuple[int, Iterable[UserDTO]]: ...
    def get(self, user_name: str) -> UserDTO: ...
    def create(self, user: UserDTOForCreate, already_hashed: bool = False) -> UserDTO: ...
    def update(self, user: UserDTOForUpdate, already_hashed: bool = False) -> UserDTO: ...
    def delete(self, user_name: str) -> None: ...
    def verify(self, user_name: str, password: str) -> UserDTO: ...
    def change_password(self, user_name: str, new_password: str) -> UserDTO: ...
    def change_password_verify(self, user_name: str, cur_password: str, new_password: str) -> UserDTO: ...

    def import_from_file(
        self, fn: str, encoding: str = "utf-8", delimiter: str = "\t", roles_delimiter: str = "|"
    ) -> None: ...

    def import_from_yaml(self, fn: str, encoding: str = "utf-8") -> None: ...
    def export(self, filename: str) -> None: ...
