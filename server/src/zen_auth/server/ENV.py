import datetime as DT
import os
from logging import getLogger

LOGGER = getLogger("app")
MODE = os.getenv("MODE", "dev")
STARTED = DT.datetime.now()
BUILD = os.getenv("BUILD", "unknown")


# UI asset URLs (can be overridden via env vars)
BOOTSTRAP_JS = os.getenv(
    "BOOTSTRAP_JS", "https://cdn.jsdelivr.net/npm/bootstrap@5.3.8/dist/js/bootstrap.bundle.min.js"
)
BOOTSTRAP_CSS = os.getenv(
    "BOOTSTRAP_CSS", "https://cdn.jsdelivr.net/npm/bootstrap@5.3.8/dist/css/bootstrap.min.css"
)
BOOTSTRAP_ICONS_CSS = os.getenv(
    "BOOTSTRAP_ICONS_CSS", "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.5/font/bootstrap-icons.min.css"
)
HTMX_JS = os.getenv("HTMX_JS", "https://cdn.jsdelivr.net/npm/htmx.org@2.0.8/dist/htmx.min.js")


SPEC = dict(
    image=os.getenv("IMAGE_NAME", "unknown"),
    container_image=os.getenv("CONTAINER_IMAGE_NAME", "unknown"),
    app_name=os.getenv("METADATA_NAME", "unknown"),
    namespace=os.getenv("METADATA_NAMESPACE", "unknown"),
    version=os.getenv("VERSION", "unknown"),
    revision=os.getenv("REVISION", "unknown"),
    authored=os.getenv("COMMITTED", "unknown"),
    created=os.getenv("CREATED", "unknown"),
    started=str(STARTED),
    build=BUILD,
)
