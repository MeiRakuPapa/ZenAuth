class UserError(Exception):
    """Base exception for user-domain errors."""


class UserNotFoundError(UserError):
    user_name: str | None = None

    def __init__(self, message: str, *, user_name: str | None = None) -> None:
        super().__init__(message)
        self.user_name = user_name


class UserAlreadyExistsError(UserError):
    pass


class UserVerificationError(UserError):
    user_name: str | None = None

    def __init__(self, message: str, *, user_name: str | None = None) -> None:
        super().__init__(message)
        self.user_name = user_name
