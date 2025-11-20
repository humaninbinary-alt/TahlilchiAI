"""Database configuration and session management."""

from typing import AsyncGenerator

from sqlalchemy import create_engine, event, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings

# Convert postgresql+psycopg2:// to postgresql+psycopg:// for async support (using psycopg3)
async_database_url = str(settings.DATABASE_URL).replace(
    "postgresql+psycopg2://", "postgresql+psycopg://"
)

# Async engine for async operations
async_engine = create_async_engine(
    async_database_url,
    echo=settings.DEBUG,
    future=True,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Sync engine for migrations (Alembic doesn't support async yet)
sync_engine = create_engine(
    str(settings.DATABASE_URL),
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

# Sync session factory
SessionLocal = sessionmaker(
    sync_engine,
    autocommit=False,
    autoflush=False,
)

# Base class for models
Base = declarative_base()


@event.listens_for(Base.metadata, "before_create")
def _strip_sqlite_server_defaults(metadata, connection, **kwargs):  # noqa: ANN001
    """SQLite doesn't allow non-constant server defaults (e.g., gen_random_uuid())."""
    if connection.dialect.name != "sqlite":
        return

    for table in metadata.tables.values():
        for column in table.columns:
            default_clause = column.server_default
            if (
                default_clause is not None
                and hasattr(default_clause, "arg")
                and "gen_random_uuid" in str(default_clause.arg).lower()
            ):
                column.info["_original_server_default"] = default_clause
                column.server_default = None


@event.listens_for(Base.metadata, "after_create")
def _restore_server_defaults(metadata, connection, **kwargs):  # noqa: ANN001
    """Restore original server defaults after SQLite DDL is generated."""
    if connection.dialect.name != "sqlite":
        return

    for table in metadata.tables.values():
        for column in table.columns:
            original_default = column.info.pop("_original_server_default", None)
            if original_default is not None:
                column.server_default = original_default


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    [DEPRECATED] Prefer get_db for stricter transaction handling.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            # NO AUTO-COMMIT - Let endpoints control transactions
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def get_sync_session() -> Session:
    """
    Get sync database session (mainly for migrations).

    Returns:
        Session: SQLAlchemy sync session
    """
    db = SessionLocal()
    try:
        return db
    finally:
        db.close()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency to provide a clean async session per request with safety checks.
    """
    async with AsyncSessionLocal() as session:
        session.autoflush = False
        session.expire_on_commit = False

        try:
            # Ensure connection is healthy
            try:
                await session.execute(text("SELECT 1"))
            except Exception:
                await session.rollback()

            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
