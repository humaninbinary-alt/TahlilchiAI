"""Unit tests for JWT service."""

from uuid import uuid4

import pytest
from jose import JWTError

from app.services.auth.jwt_service import JWTService


@pytest.mark.unit
class TestJWTService:
    """Test JWT token service."""

    def test_create_access_token(self):
        """Test creating access token."""
        user_id = uuid4()
        tenant_id = uuid4()
        role = "admin"

        token = JWTService.create_access_token(user_id, tenant_id, role)

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 50

    def test_create_refresh_token(self):
        """Test creating refresh token."""
        user_id = uuid4()

        token = JWTService.create_refresh_token(user_id)

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 50

    def test_verify_access_token(self):
        """Test verifying valid access token."""
        user_id = uuid4()
        tenant_id = uuid4()
        role = "member"

        token = JWTService.create_access_token(user_id, tenant_id, role)
        payload = JWTService.verify_token(token, token_type="access")

        assert payload["sub"] == str(user_id)
        assert payload["tenant_id"] == str(tenant_id)
        assert payload["role"] == role
        assert payload["type"] == "access"

    def test_verify_refresh_token(self):
        """Test verifying valid refresh token."""
        user_id = uuid4()

        token = JWTService.create_refresh_token(user_id)
        payload = JWTService.verify_token(token, token_type="refresh")

        assert payload["sub"] == str(user_id)
        assert payload["type"] == "refresh"

    def test_verify_token_wrong_type(self):
        """Test verifying token with wrong type."""
        user_id = uuid4()
        tenant_id = uuid4()

        token = JWTService.create_access_token(user_id, tenant_id, "member")

        with pytest.raises(ValueError, match="Invalid token type"):
            JWTService.verify_token(token, token_type="refresh")

    def test_verify_invalid_token(self):
        """Test verifying invalid token."""
        with pytest.raises(JWTError):
            JWTService.verify_token("invalid.token.here", token_type="access")

    def test_decode_token(self):
        """Test decoding token without verification."""
        user_id = uuid4()
        tenant_id = uuid4()

        token = JWTService.create_access_token(user_id, tenant_id, "admin")
        payload = JWTService.decode_token(token)

        assert payload["sub"] == str(user_id)
        assert payload["tenant_id"] == str(tenant_id)
