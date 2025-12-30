import os

from dotenv import load_dotenv

# Local development helper: load environment variables from `.env` if present.
# In container environments, prefer passing env vars / secrets via the platform.
load_dotenv(".env")
os.environ.setdefault("ZENAUTH_SERVER_DSN", "sqlite+aiosqlite:///./dummy_users.db")

if __name__ == "__main__":
    from uvicorn import run
    from zen_auth.config.config import ZENAUTH_CONFIG
    from zen_auth.logger import LOGGER

    from .src.zen_auth.server.run import app

    LOGGER.info("ZenAuth config loaded (redacted): %s", ZENAUTH_CONFIG().safe_dict())

    run(app, host="0.0.0.0", port=8000, log_level="debug")
