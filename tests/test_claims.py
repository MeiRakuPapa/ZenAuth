# mypy: disable-error-code=no-untyped-def

import pytest
from zen_auth.claims.base import Claims
from zen_auth.dto import UserDTO

# Mock data for testing
mock_user = UserDTO(
    user_name="test_user",
    password=None,
    roles=["admin"],
    real_name="Test User",
    division="IT",
    description="Test user for claims",
    policy_epoch=1,
    created_at=None,
    updated_at=None,
)


def test_claims_username():
    """Test the username property of Claims."""
    claims = Claims(typ="access", sub="test_user", policy_epoch=1, iat=1234567890, exp=1234567990)
    assert claims.username == "test_user"


def test_claims_auth_user():
    """Test setting and getting the authenticated user."""
    claims = Claims(typ="access", sub="test_user", policy_epoch=1, iat=1234567890, exp=1234567990)
    claims._auth_user = mock_user
    assert claims._auth_user.user_name == "test_user"
