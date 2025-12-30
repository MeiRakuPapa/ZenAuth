from pydantic import BaseModel


class RoleDTO(BaseModel):
    """Role DTO used across API/service/persistence layers."""

    role_name: str
    display_name: str
    description: str | None = None
    created_at: str | None = None
    updated_at: str | None = None

    def __str__(self) -> str:
        return f"#<Role {self.display_name}:{self.role_name}>"

    def __repr__(self) -> str:
        return self.__str__()


class RoleDTOForCreate(BaseModel):
    """Input DTO for creating a role."""

    role_name: str
    display_name: str
    description: str | None = None

    def __str__(self) -> str:
        return f"#<Role {self.display_name}:{self.role_name}>"

    def __repr__(self) -> str:
        return self.__str__()


class RoleDTOForUpdate(BaseModel):
    """Input DTO for updating a role."""

    display_name: str | None = None
    description: str | None = None

    def __str__(self) -> str:
        return f"#<Role Update: display_name={self.display_name}, description={self.description}>"

    def __repr__(self) -> str:
        return self.__str__()
