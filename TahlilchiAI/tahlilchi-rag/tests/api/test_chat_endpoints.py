"""API tests for chat endpoints."""

import pytest
from httpx import AsyncClient

from tests.utils import (assert_valid_response, assert_valid_uuid,
                         create_test_chat_data)


@pytest.mark.asyncio
class TestChatEndpoints:
    """Test chat API endpoints."""

    async def test_create_chat_with_valid_data_returns_201(
        self, async_client: AsyncClient, manager_auth_headers, test_tenant
    ):
        """Test creating chat with valid data."""
        payload = create_test_chat_data()

        response = await async_client.post(
            "/api/v1/chats", json=payload, headers=manager_auth_headers
        )

        assert_valid_response(response, 201)
        data = response.json()
        assert data["name"] == payload["name"]
        assert data["purpose"] == payload["purpose"]
        assert_valid_uuid(data["id"])

    async def test_create_chat_as_member_returns_403(
        self, async_client: AsyncClient, auth_headers
    ):
        """Test creating chat as member (insufficient permissions)."""
        payload = create_test_chat_data()

        response = await async_client.post(
            "/api/v1/chats", json=payload, headers=auth_headers
        )

        assert response.status_code == 403

    async def test_create_chat_without_auth_returns_401(
        self, async_client: AsyncClient
    ):
        """Test creating chat without authentication."""
        payload = create_test_chat_data()

        response = await async_client.post("/api/v1/chats", json=payload)

        assert response.status_code == 401

    async def test_list_chats_returns_paginated_results(
        self, async_client: AsyncClient, auth_headers, test_chat
    ):
        """Test listing chats."""
        response = await async_client.get("/api/v1/chats", headers=auth_headers)

        assert_valid_response(response, 200)
        data = response.json()
        assert "chats" in data
        assert "total" in data
        assert isinstance(data["chats"], list)
        assert data["total"] >= 1

    async def test_get_chat_by_id_returns_chat(
        self, async_client: AsyncClient, auth_headers, test_chat
    ):
        """Test getting specific chat."""
        response = await async_client.get(
            f"/api/v1/chats/{test_chat.id}", headers=auth_headers
        )

        assert_valid_response(response, 200)
        data = response.json()
        assert data["id"] == str(test_chat.id)
        assert data["name"] == test_chat.name

    async def test_get_nonexistent_chat_returns_404(
        self, async_client: AsyncClient, auth_headers
    ):
        """Test getting non-existent chat."""
        from uuid import uuid4

        response = await async_client.get(
            f"/api/v1/chats/{uuid4()}", headers=auth_headers
        )

        assert response.status_code == 404

    async def test_update_chat_as_admin_returns_200(
        self, async_client: AsyncClient, admin_auth_headers, test_chat
    ):
        """Test updating chat as admin."""
        payload = {"name": "Updated Chat Name"}

        response = await async_client.patch(
            f"/api/v1/chats/{test_chat.id}",
            json=payload,
            headers=admin_auth_headers,
        )

        assert_valid_response(response, 200)
        data = response.json()
        assert data["name"] == "Updated Chat Name"

    async def test_delete_chat_as_admin_returns_204(
        self, async_client: AsyncClient, admin_auth_headers, test_chat
    ):
        """Test deleting chat as admin."""
        response = await async_client.delete(
            f"/api/v1/chats/{test_chat.id}", headers=admin_auth_headers
        )

        assert response.status_code == 204

    async def test_delete_chat_as_member_returns_403(
        self, async_client: AsyncClient, auth_headers, test_chat
    ):
        """Test deleting chat as member (insufficient permissions)."""
        response = await async_client.delete(
            f"/api/v1/chats/{test_chat.id}", headers=auth_headers
        )

        assert response.status_code == 403
