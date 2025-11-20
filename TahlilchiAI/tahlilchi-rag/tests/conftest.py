"""Pytest configuration and fixtures for testing."""

import asyncio
from typing import AsyncGenerator, Dict, Generator
from uuid import uuid4

import pytest
import pytest_asyncio
from faker import Faker
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_async_session, get_db
from app.main import app
from app.models.chat import Chat
from app.models.chat_access import ChatAccess
from app.models.tenant import Tenant
from app.models.user import User, UserRole
from app.services.auth.jwt_service import JWTService

# Initialize Faker
fake = Faker()

# Test database URL (in-memory SQLite for speed)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def test_db() -> AsyncGenerator[AsyncSession, None]:
    """Create test database and session."""
    # Create async engine
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    if engine.dialect.name == "sqlite":

        @event.listens_for(engine.sync_engine, "connect")
        def _register_sqlite_functions(dbapi_connection, connection_record):  # noqa: ANN001
            dbapi_connection.create_function(
                "gen_random_uuid", 0, lambda: str(uuid4())
            )

    # Create tables (drop first to avoid conflicts)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    # Create session factory
    async_session_maker = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    # Create session
    async with async_session_maker() as session:
        yield session

    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def async_client(test_db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create async test client."""

    # Override database dependency
    async def override_get_db():
        yield test_db

    app.dependency_overrides[get_async_session] = override_get_db
    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


# ============================================================================
# Data Factories
# ============================================================================


@pytest_asyncio.fixture
async def test_tenant(test_db: AsyncSession) -> Tenant:
    """Create test tenant."""
    tenant = Tenant(
        id=uuid4(),
        name=fake.company(),
        slug=fake.slug(),
        is_active=True,
    )
    test_db.add(tenant)
    await test_db.commit()
    await test_db.refresh(tenant)
    return tenant


@pytest_asyncio.fixture
async def test_user(test_db: AsyncSession, test_tenant: Tenant) -> User:
    """Create test user with member role."""
    user = User(
        id=uuid4(),
        tenant_id=test_tenant.id,
        email=fake.email(),
        full_name=fake.name(),
        role=UserRole.member,
        is_active=True,
    )
    user.set_password("TestPassword123")
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest_asyncio.fixture
async def admin_user(test_db: AsyncSession, test_tenant: Tenant) -> User:
    """Create test user with admin role."""
    user = User(
        id=uuid4(),
        tenant_id=test_tenant.id,
        email=fake.email(),
        full_name=fake.name(),
        role=UserRole.admin,
        is_active=True,
    )
    user.set_password("AdminPassword123")
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest_asyncio.fixture
async def manager_user(test_db: AsyncSession, test_tenant: Tenant) -> User:
    """Create test user with manager role."""
    user = User(
        id=uuid4(),
        tenant_id=test_tenant.id,
        email=fake.email(),
        full_name=fake.name(),
        role=UserRole.manager,
        is_active=True,
    )
    user.set_password("ManagerPassword123")
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_chat(
    test_db: AsyncSession, test_tenant: Tenant, test_user: User
) -> Chat:
    """Create test chat."""
    chat = Chat(
        id=uuid4(),
        tenant_id=test_tenant.id,
        created_by=test_user.id,
        name=fake.catch_phrase(),
        purpose="policy_qa",
        tone="formal_english",
        strictness="allow_reasoning",
        target_audience="staff",
        sensitivity="medium",
        document_types=[],
        document_languages=[],
        is_active=True,
    )
    access = ChatAccess(
        tenant_id=test_tenant.id,
        user_id=test_user.id,
        chat_id=chat.id,
        granted_by=test_user.id,
    )
    test_db.add_all([chat, access])
    await test_db.commit()
    await test_db.refresh(chat)
    return chat


# ============================================================================
# Auth Fixtures
# ============================================================================


@pytest.fixture
def auth_headers(test_user: User) -> Dict[str, str]:
    """Generate auth headers with JWT token."""
    token = JWTService.create_access_token(
        test_user.id, test_user.tenant_id, test_user.role.value
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_auth_headers(admin_user: User) -> Dict[str, str]:
    """Generate auth headers for admin user."""
    token = JWTService.create_access_token(
        admin_user.id, admin_user.tenant_id, admin_user.role.value
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def manager_auth_headers(manager_user: User) -> Dict[str, str]:
    """Generate auth headers for manager user."""
    token = JWTService.create_access_token(
        manager_user.id, manager_user.tenant_id, manager_user.role.value
    )
    return {"Authorization": f"Bearer {token}"}


# ============================================================================
# Mock Fixtures
# ============================================================================


@pytest.fixture
def mock_ollama(mocker):
    """Mock Ollama LLM client."""
    mock = mocker.patch("app.services.llm.ollama_client.OllamaClient.generate")
    mock.return_value = (
        "This is a mocked LLM response with citations [Doc: test.pdf, Page: 1]"
    )
    return mock


@pytest.fixture
def mock_ollama_stream(mocker):
    """Mock Ollama streaming."""

    async def mock_stream(*args, **kwargs):
        for token in ["This ", "is ", "a ", "test ", "response"]:
            yield token

    mock = mocker.patch("app.services.llm.ollama_client.OllamaClient.generate_stream")
    mock.return_value = mock_stream()
    return mock


@pytest.fixture
def mock_qdrant(mocker):
    """Mock Qdrant vector store."""
    mock = mocker.patch("app.services.vector_store.QdrantVectorStore")
    return mock


@pytest.fixture
def mock_redis(mocker):
    """Mock Redis for rate limiting."""
    mock = mocker.patch("app.services.rate_limiter.redis.from_url")
    mock_client = mocker.MagicMock()
    mock_client.ping.return_value = True
    mock_client.get.return_value = None
    mock_client.incr.return_value = 1
    mock.return_value = mock_client
    return mock


@pytest.fixture
def mock_celery(mocker):
    """Mock Celery tasks."""
    mock = mocker.patch(
        "app.tasks.document_tasks.process_and_index_document_task.delay"
    )
    mock.return_value.id = str(uuid4())
    return mock


@pytest.fixture
def mock_embedding_service(mocker):
    """Mock embedding service."""
    mock = mocker.patch("app.services.embedding_service.EmbeddingService.embed_texts")
    # Return dummy embeddings
    mock.return_value = [[0.1] * 1024]
    return mock


# ============================================================================
# Utility Fixtures
# ============================================================================


@pytest.fixture
def sample_pdf_content() -> bytes:
    """Generate sample PDF content."""
    # Minimal PDF structure
    return b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n%%EOF"


@pytest.fixture
def sample_text_content() -> str:
    """Generate sample text content."""
    return fake.text(max_nb_chars=500)
