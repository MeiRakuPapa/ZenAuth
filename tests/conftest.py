# mypy: disable-error-code=no-untyped-def
import sys
from pathlib import Path

import pytest

# Ensure monorepo src roots are importable during tests.
_REPO_ROOT = Path(__file__).resolve().parents[1]
for _p in (
    _REPO_ROOT / "core" / "src",
    _REPO_ROOT / "client" / "src",
    _REPO_ROOT / "server" / "src",
):
    _p_str = str(_p)
    if _p_str not in sys.path:
        sys.path.insert(0, _p_str)

from zen_auth.config import ZENAUTH_CONFIG


@pytest.fixture(autouse=True)
def _zenauth_test_env(monkeypatch: pytest.MonkeyPatch):
    # Core config requires SECRET_KEY.
    monkeypatch.setenv("ZENAUTH_SECRET_KEY", "**TEST**")
    monkeypatch.setenv("ZENAUTH_AUTH_SERVER_ORIGIN", "http://testserver")
    ZENAUTH_CONFIG.cache_clear()
    yield
    ZENAUTH_CONFIG.cache_clear()
