"""API tests for authentication endpoints."""

import pytest
from httpx import AsyncClient

from tests.utils import assert_valid_response, assert_valid_uuid


@pytest.mark.asyncio
@pytest.mark.auth
class TestAuthEndpoints:
    """Test authentication API endpoints."""

    async def test_register_user_with_valid_data_returns_201(
        self, async_client: AsyncClient, test_tenant
    ):
        """Test user registration with valid data."""
        payload = {
            "email": "newuser@example.com",
            "password": "SecurePass123",
            "full_name": "New User",
            "tenant_id": str(test_tenant.id),
        }

        response = await async_client.post("/api/v1/auth/register", json=payload)

        assert_valid_response(response, 201)
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert data["full_name"] == "New User"
        assert "password" not in data
        assert_valid_uuid(data["id"])

    async def test_register_user_with_weak_password_returns_400(
        self, async_client: AsyncClient, test_tenant
    ):
        """Test registration with weak password."""
        payload = {
            "email": "newuser@example.com",
            "password": "weak",
            "full_name": "New User",
            "tenant_id": str(test_tenant.id),
        }

        response = await async_client.post("/api/v1/auth/register", json=payload)

        assert response.status_code == 400

    async def test_register_user_with_duplicate_email_returns_400(
        self, async_client: AsyncClient, test_user, test_tenant
    ):
        """Test registration with existing email."""
        payload = {
            "email": test_user.email,
            "password": "SecurePass123",
            "full_name": "Duplicate User",
            "tenant_id": str(test_tenant.id),
        }

        response = await async_client.post("/api/v1/auth/register", json=payload)

        assert response.status_code == 400

    async def test_login_with_valid_credentials_returns_tokens(
        self, async_client: AsyncClient, test_user
    ):
        """Test login with valid credentials."""
        payload = {"email": test_user.email, "password": "TestPassword123"}

        response = await async_client.post("/api/v1/auth/login", json=payload)

        assert_valid_response(response, 200)
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == test_user.email

    async def test_login_with_invalid_password_returns_401(
        self, async_client: AsyncClient, test_user
    ):
        """Test login with wrong password."""
        payload = {"email": test_user.email, "password": "WrongPassword"}

        response = await async_client.post("/api/v1/auth/login", json=payload)

        assert response.status_code == 401

    async def test_login_with_nonexistent_email_returns_401(
        self, async_client: AsyncClient
    ):
        """Test login with non-existent email."""
        payload = {"email": "nonexistent@example.com", "password": "Password123"}

        response = await async_client.post("/api/v1/auth/login", json=payload)

        assert response.status_code == 401

    async def test_refresh_token_with_valid_token_returns_new_access_token(
        self, async_client: AsyncClient, test_user
    ):
        """Test refreshing access token."""
        # First login
        login_response = await async_client.post(
            "/api/v1/auth/login",
            json={"email": test_user.email, "password": "TestPassword123"},
        )
        refresh_token = login_response.json()["refresh_token"]

        # Refresh
        response = await async_client.post(
            "/api/v1/auth/refresh", json={"refresh_token": refresh_token}
        )

        assert_valid_response(response, 200)
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    async def test_refresh_token_with_invalid_token_returns_401(
        self, async_client: AsyncClient
    ):
        """Test refresh with invalid token."""
        response = await async_client.post(
            "/api/v1/auth/refresh", json={"refresh_token": "invalid.token.here"}
        )

        assert response.status_code == 401

    async def test_get_current_user_with_valid_token_returns_user(
        self, async_client: AsyncClient, auth_headers, test_user
    ):
        """Test getting current user info."""
        response = await async_client.get("/api/v1/auth/me", headers=auth_headers)

        assert_valid_response(response, 200)
        data = response.json()
        assert data["email"] == test_user.email
        assert data["id"] == str(test_user.id)

    async def test_get_current_user_without_token_returns_401(
        self, async_client: AsyncClient
    ):
        """Test getting current user without auth."""
        response = await async_client.get("/api/v1/auth/me")

        assert response.status_code == 401

    async def test_logout_with_valid_token_returns_200(
        self, async_client: AsyncClient, auth_headers
    ):
        """Test logout."""
        response = await async_client.post("/api/v1/auth/logout", headers=auth_headers)

        assert_valid_response(response, 200)
