from pydantic import BaseModel

from .user import UserDTO


class VerifyTokenDTO(BaseModel):
    token: str
    user: UserDTO
