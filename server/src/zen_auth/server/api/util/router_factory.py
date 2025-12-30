import inspect
from enum import Enum

from fastapi import APIRouter


def APIRouterFactory(*, prefix: str | None = None, tags: list[str | Enum] | None = None) -> APIRouter:
    caller = inspect.stack()[1]
    module = inspect.getmodule(caller[0])
    package = module.__name__ if module else ""
    pkg_name = package.split(".")[-1] if package else "default"

    router = APIRouter(
        prefix=prefix or f"/{pkg_name}",
        tags=tags or [pkg_name],
    )

    return router
