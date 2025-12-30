from pydantic import BaseModel, Field


class ScopeDTO(BaseModel):
    """Scope DTO used across API/service/persistence layers."""

    scope_name: str
    display_name: str
    roles: list[str] = Field(default_factory=list)
    description: str | None = None
    created_at: str | None = None
    updated_at: str | None = None

    def __str__(self) -> str:
        return f"#<Scope {self.scope_name}>"

    def __repr__(self) -> str:
        return self.__str__()


class ScopeDTOForCreate(BaseModel):
    """Input DTO for creating a scope."""

    scope_name: str
    display_name: str
    roles: list[str] = Field(default_factory=list)
    description: str | None = None

    def __str__(self) -> str:
        return f"#<Scope {self.scope_name}>"

    def __repr__(self) -> str:
        return self.__str__()


class ScopeDTOForUpdate(BaseModel):
    """Input DTO for updating a scope."""

    display_name: str | None = None
    roles: list[str] | None = None
    description: str | None = None
