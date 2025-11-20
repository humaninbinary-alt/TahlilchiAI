"""Unit tests for SQLAlchemy models."""

from uuid import uuid4

import pytest

from app.models.chat import Chat
from app.models.tenant import Tenant
from app.models.user import User, UserRole


@pytest.mark.unit
class TestUserModel:
    """Test User model."""

    def test_user_creation(self, test_tenant):
        """Test creating a user."""
        user = User(
            id=uuid4(),
            tenant_id=test_tenant.id,
            email="test@example.com",
            full_name="Test User",
            role=UserRole.member,
            password_hash="dummy",
            is_active=True,
        )

        assert user.email == "test@example.com"
        assert user.full_name == "Test User"
        assert user.role == UserRole.member
        assert user.is_active is True

    def test_set_password(self, test_tenant):
        """Test password hashing."""
        user = User(
            id=uuid4(),
            tenant_id=test_tenant.id,
            email="test@example.com",
            full_name="Test User",
            password_hash="dummy",
            is_active=True,
        )

        user.set_password("SecurePassword123")

        assert user.password_hash is not None
        assert user.password_hash != "SecurePassword123"
        assert len(user.password_hash) > 20

    def test_verify_password_correct(self, test_tenant):
        """Test password verification with correct password."""
        user = User(
            id=uuid4(),
            tenant_id=test_tenant.id,
            email="test@example.com",
            full_name="Test User",
            password_hash="dummy",
            is_active=True,
        )

        user.set_password("SecurePassword123")

        assert user.verify_password("SecurePassword123") is True

    def test_verify_password_incorrect(self, test_tenant):
        """Test password verification with incorrect password."""
        user = User(
            id=uuid4(),
            tenant_id=test_tenant.id,
            email="test@example.com",
            full_name="Test User",
            password_hash="dummy",
            is_active=True,
        )

        user.set_password("SecurePassword123")

        assert user.verify_password("WrongPassword") is False

    def test_user_repr(self, test_user):
        """Test user string representation."""
        repr_str = repr(test_user)

        assert "User" in repr_str
        assert str(test_user.id) in repr_str
        assert test_user.email in repr_str


@pytest.mark.unit
class TestTenantModel:
    """Test Tenant model."""

    def test_tenant_creation(self):
        """Test creating a tenant."""
        tenant = Tenant(
            id=uuid4(),
            name="Test Company",
            slug="test-company",
            is_active=True,
        )

        assert tenant.name == "Test Company"
        assert tenant.slug == "test-company"
        assert tenant.is_active is True

    def test_tenant_repr(self, test_tenant):
        """Test tenant string representation."""
        repr_str = repr(test_tenant)

        assert "Tenant" in repr_str
        assert test_tenant.name in repr_str


@pytest.mark.unit
class TestChatModel:
    """Test Chat model."""

    def test_chat_creation(self, test_tenant, test_user):
        """Test creating a chat."""
        chat = Chat(
            id=uuid4(),
            tenant_id=test_tenant.id,
            created_by=test_user.id,
            name="Test Chat",
            purpose="policy_qa",
            target_audience="staff",
            tone="formal_english",
            strictness="allow_reasoning",
            sensitivity="medium",
            document_types=[],
            document_languages=[],
            is_active=True,
        )

        assert chat.name == "Test Chat"
        assert chat.purpose == "policy_qa"
        assert chat.tone == "formal_english"
        assert chat.strictness == "allow_reasoning"
        assert chat.is_active is True

    def test_chat_repr(self, test_chat):
        """Test chat string representation."""
        repr_str = repr(test_chat)

        assert "Chat" in repr_str
        assert test_chat.name in repr_str
