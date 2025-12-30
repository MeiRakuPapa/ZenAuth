"""FastAPI example application.

Expose the ASGI `app` at package level so it can be launched with:
`python -m uvicorn examples.webapp_fastapi:app`
"""

from .app import app

__all__ = ["app"]
