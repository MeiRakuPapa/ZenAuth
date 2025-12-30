import signal
import sys
import threading
from contextlib import asynccontextmanager
from types import FrameType
from typing import AsyncIterator

from fastapi import FastAPI
from zen_auth.logger import LOGGER

from .persistence.init_db import init_db
from .persistence.session import get_engine


def __handle_signal(sig: int, _frame: FrameType | None) -> None:
    LOGGER.warning(f"Signal received: {signal.Signals(sig).name}")
    sys.exit(0)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # `signal.signal()` only works on the main thread. In tests (e.g. Starlette
    # TestClient) the lifespan may run in a worker thread.
    if threading.current_thread() is threading.main_thread():
        signal.signal(signal.SIGTERM, __handle_signal)
        signal.signal(signal.SIGINT, __handle_signal)

    try:
        init_db(get_engine())
    except Exception as e:
        LOGGER.exception("Failed to initialize database", exc_info=e)
        raise

    yield
