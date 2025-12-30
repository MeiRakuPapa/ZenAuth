# mypy: disable-error-code=no-untyped-def
# mypy: disable-error-code=call-arg

from zen_auth.config import ZenAuthConfig
from zen_auth.errors import ConfigError


def test_identity_config_defaults():
    """Test the default values of IdentityConfig."""
    # Avoid loading .env.* during tests; defaults + env fixture should apply.
    config = ZenAuthConfig(_env_file=None)
    assert config.cookie_name == "access_token"
    assert config.expire_min == 15
    assert config.algorithm == "HS256"
    assert config.samesite == "lax"
    assert config.secure is False
    assert config.secret_key == "**TEST**"


def test_identity_config_requires_secret_key(monkeypatch):
    monkeypatch.delenv("ZENAUTH_SECRET_KEY", raising=False)

    try:
        ZenAuthConfig(_env_file=None)
        assert False, "expected ConfigError"
    except ConfigError:
        assert True
