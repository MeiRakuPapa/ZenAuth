import uuid
from typing import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

_ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"


class RequestIDMiddleWare(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        req_id = self._new_rec_id()
        request.state.req_id = req_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = req_id
        return response

    @staticmethod
    def _new_rec_id() -> str:
        def uuid2base62(u: uuid.UUID) -> str:
            num = u.int
            chars = []
            base = 62
            while num > 0:
                num, rem = divmod(num, base)
                chars.append(_ALPHABET[rem])
            return "".join(reversed(chars))

        return uuid2base62(uuid.uuid4())
