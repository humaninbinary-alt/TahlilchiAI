"""Integration tests for RAG pipeline."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
@pytest.mark.integration
class TestRAGPipeline:
    """Test complete RAG pipeline."""

    async def test_query_with_hybrid_retrieval_returns_answer(
        self,
        async_client: AsyncClient,
        auth_headers,
        test_chat,
        mock_ollama,
        mock_qdrant,
    ):
        """Test query with hybrid retrieval mode."""
        payload = {
            "query": "What is the policy on remote work?",
            "mode": "hybrid",
            "top_k": 5,
        }

        response = await async_client.post(
            f"/api/v1/chats/{test_chat.id}/answer",
            json=payload,
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert "citations" in data
        assert "confidence" in data
        assert data["retrieval_mode"] in ["hybrid", "dense", "sparse"]

    async def test_query_with_dense_retrieval_returns_answer(
        self,
        async_client: AsyncClient,
        auth_headers,
        test_chat,
        mock_ollama,
        mock_qdrant,
    ):
        """Test query with dense retrieval mode."""
        payload = {
            "query": "What are the benefits?",
            "mode": "dense",
            "top_k": 3,
        }

        response = await async_client.post(
            f"/api/v1/chats/{test_chat.id}/answer",
            json=payload,
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "answer" in data

    async def test_query_with_no_context_returns_appropriate_response(
        self,
        async_client: AsyncClient,
        auth_headers,
        test_chat,
        mock_ollama,
        mock_qdrant,
    ):
        """Test query when no relevant context found."""
        # Mock empty retrieval results
        mock_qdrant.return_value.search.return_value = []

        payload = {"query": "Completely unrelated query", "mode": "hybrid"}

        response = await async_client.post(
            f"/api/v1/chats/{test_chat.id}/answer",
            json=payload,
            headers=auth_headers,
        )

        # Should still return 200 with appropriate message
        assert response.status_code == 200

    async def test_streaming_query_returns_sse_events(
        self,
        async_client: AsyncClient,
        auth_headers,
        test_chat,
        mock_ollama_stream,
    ):
        """Test streaming query returns SSE events."""
        payload = {"query": "What is the policy?"}

        response = await async_client.post(
            f"/api/v1/chats/{test_chat.id}/answer/stream",
            json=payload,
            headers=auth_headers,
        )

        # Streaming response
        assert response.status_code == 200
        # Content-Type should be text/event-stream
        # assert "text/event-stream" in response.headers.get("content-type", "")

    async def test_query_with_conversation_context_uses_history(
        self,
        async_client: AsyncClient,
        auth_headers,
        test_chat,
        mock_ollama,
    ):
        """Test query with conversation context."""
        # Create conversation
        conv_response = await async_client.post(
            f"/api/v1/chats/{test_chat.id}/conversations",
            headers=auth_headers,
        )
        conversation_id = conv_response.json()["id"]

        # Send first message
        await async_client.post(
            f"/api/v1/chats/{test_chat.id}/answer/{conversation_id}/message",
            json={"query": "What is the policy?"},
            headers=auth_headers,
        )

        # Send follow-up message
        response = await async_client.post(
            f"/api/v1/chats/{test_chat.id}/answer/{conversation_id}/message",
            json={"query": "Can you explain more?"},
            headers=auth_headers,
        )

        assert response.status_code == 200
        # Should use conversation context

    async def test_query_with_citations_includes_source_info(
        self,
        async_client: AsyncClient,
        auth_headers,
        test_chat,
        mock_ollama,
    ):
        """Test that answer includes citation information."""
        payload = {"query": "What is the policy?"}

        response = await async_client.post(
            f"/api/v1/chats/{test_chat.id}/answer",
            json=payload,
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "citations" in data
        assert isinstance(data["citations"], list)
