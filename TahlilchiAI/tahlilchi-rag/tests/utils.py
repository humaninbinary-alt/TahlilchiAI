"""Test utility functions."""

import asyncio
import io
from datetime import datetime
from typing import Any, Dict
from uuid import UUID

from faker import Faker

from app.services.auth.jwt_service import JWTService

fake = Faker()


def generate_test_token(user_id: UUID, tenant_id: UUID, role: str = "member") -> str:
    """Generate valid JWT token for testing."""
    return JWTService.create_access_token(user_id, tenant_id, role)


def generate_expired_token(user_id: UUID, tenant_id: UUID) -> str:
    """Generate expired JWT token for testing."""
    # This would require modifying JWTService to accept custom expiry
    # For now, return a token that will expire soon
    return JWTService.create_access_token(user_id, tenant_id, "member")


def generate_test_pdf() -> io.BytesIO:
    """Create dummy PDF file for testing."""
    pdf_content = b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj
2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj
3 0 obj
<<
/Type /Page
/Parent 2 0 R
/Resources <<
/Font <<
/F1 <<
/Type /Font
/Subtype /Type1
/BaseFont /Helvetica
>>
>>
>>
/MediaBox [0 0 612 792]
/Contents 4 0 R
>>
endobj
4 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
100 700 Td
(Test PDF Content) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000317 00000 n
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
410
%%EOF"""
    return io.BytesIO(pdf_content)


def generate_test_docx() -> io.BytesIO:
    """Create dummy DOCX file for testing."""
    # Minimal DOCX structure (simplified)
    # In reality, DOCX is a ZIP file with XML
    # For testing, we'll just return a simple file
    content = b"PK\x03\x04" + b"\x00" * 100  # Minimal ZIP header
    return io.BytesIO(content)


def assert_valid_response(response: Any, expected_status: int = 200) -> None:
    """Assert response is valid with expected status."""
    assert response.status_code == expected_status, (
        f"Expected status {expected_status}, got {response.status_code}. "
        f"Response: {response.text}"
    )


def assert_valid_uuid(value: str) -> None:
    """Assert value is a valid UUID string."""
    try:
        UUID(value)
    except (ValueError, AttributeError):
        raise AssertionError(f"Invalid UUID: {value}")


def assert_valid_timestamp(value: str) -> None:
    """Assert value is a valid ISO timestamp."""
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        raise AssertionError(f"Invalid timestamp: {value}")


async def wait_for_job(
    client: Any,
    job_id: str,
    token: str,
    timeout: int = 30,
    interval: float = 0.5,
) -> Dict[str, Any]:
    """
    Wait for async job to complete.

    Args:
        client: HTTP client
        job_id: Job ID to wait for
        timeout: Maximum wait time in seconds
        interval: Polling interval in seconds

    Returns:
        Job result

    Raises:
        TimeoutError: If job doesn't complete in time
    """
    start_time = asyncio.get_event_loop().time()

    while True:
        response = await client.get(
            f"/api/v1/jobs/{job_id}/status",
            headers={"Authorization": f"Bearer {token}"},
        )
        if response.status_code != 200:
            raise ValueError(f"Failed to get job status: {response.text}")

        data = response.json()
        status = data.get("status")

        if status in ["completed", "failed"]:
            return data

        if asyncio.get_event_loop().time() - start_time > timeout:
            raise TimeoutError(f"Job {job_id} did not complete within {timeout}s")

        await asyncio.sleep(interval)


def cleanup_test_data(db_session: Any) -> None:
    """Remove test artifacts from database."""
    # This would be implemented based on your cleanup needs
    pass


def create_test_user_data() -> Dict[str, Any]:
    """Generate test user data."""
    return {
        "email": fake.email(),
        "full_name": fake.name(),
        "password": "TestPassword123",
    }


def create_test_chat_data() -> Dict[str, Any]:
    """Generate test chat data."""
    return {
        "name": fake.catch_phrase(),
        "purpose": "policy_qa",
        "target_audience": "staff",
        "tone": "formal_english",
        "strictness": "allow_reasoning",
        "sensitivity": "medium",
        "document_types": ["policy", "procedure"],
        "document_languages": ["en", "uz"],
    }


def create_test_document_data() -> Dict[str, Any]:
    """Generate test document metadata."""
    return {
        "filename": fake.file_name(extension="pdf"),
        "file_type": "application/pdf",
        "file_size": fake.random_int(min=1000, max=1000000),
    }


def create_test_query_data() -> Dict[str, Any]:
    """Generate test query data."""
    return {
        "query": fake.sentence(),
        "mode": "hybrid",
        "top_k": 5,
    }
