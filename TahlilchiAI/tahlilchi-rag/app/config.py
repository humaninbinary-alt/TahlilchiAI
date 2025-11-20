"""Application configuration settings."""

from typing import Optional, Union

from pydantic import Field, FieldValidationInfo, PostgresDsn, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Project Info
    PROJECT_NAME: str = "TahlilchiAI Custom Chats"
    VERSION: str = "0.1.0"
    API_V1_PREFIX: str = "/api/v1"
    ENVIRONMENT: str = Field(default="development")
    LOG_LEVEL: str = Field(default="INFO")

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = False

    # Database
    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_PORT: int = 5432
    DATABASE_URL: Optional[PostgresDsn] = None

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_connection(cls, v: Optional[str], info) -> str:
        """Construct database URL from individual components if not provided."""
        if isinstance(v, str):
            return v

        # Build from components
        values = info.data
        return PostgresDsn.build(
            scheme="postgresql+psycopg2",
            username=values.get("POSTGRES_USER"),
            password=values.get("POSTGRES_PASSWORD"),
            host=values.get("POSTGRES_SERVER"),
            port=values.get("POSTGRES_PORT"),
            path=values.get("POSTGRES_DB", ""),
        ).unicode_string()

    # CORS
    BACKEND_CORS_ORIGINS: Union[str, list[str]] = (
        "http://localhost:3000,http://localhost:8000"
    )

    @field_validator("BACKEND_CORS_ORIGINS", mode="after")
    @classmethod
    def parse_cors_origins(cls, v) -> list[str]:
        """Parse CORS origins from comma-separated string or list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    # Security & Authentication
    SECRET_KEY: str = "change-me-secret-key"
    JWT_SECRET_KEY: str = "change-me-jwt-key"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Pagination
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100

    # Embedding settings
    EMBEDDING_MODEL: str = "intfloat/multilingual-e5-large"
    EMBEDDING_DIMENSION: int = 1024
    EMBEDDING_BATCH_SIZE: int = 32

    # Qdrant vector store
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: Optional[str] = None
    QDRANT_COLLECTION_PREFIX: str = "tahlilchi"

    # LLM settings
    LLM_PROVIDER: str = "ollama"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2.5:7b"
    LLM_TEMPERATURE: float = 0.7
    LLM_MAX_TOKENS: int = 1000
    LLM_TIMEOUT: int = 60  # seconds

    # Answer generation settings
    MAX_CONTEXT_LENGTH: int = 4000  # Max tokens in context
    CITATION_STYLE: str = "inline"  # inline or footnote

    # Celery settings
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    # Rate limiting
    REDIS_URL: str = "redis://localhost:6379/1"
    RATE_LIMIT_ENABLED: bool = True

    # Rate limit tiers (requests per hour)
    RATE_LIMIT_FREE_USER: int = 100
    RATE_LIMIT_FREE_TENANT: int = 1000
    RATE_LIMIT_FREE_UPLOADS: int = 10  # per day
    RATE_LIMIT_FREE_QUERIES: int = 50

    RATE_LIMIT_PRO_USER: int = 1000
    RATE_LIMIT_PRO_TENANT: int = 10000
    RATE_LIMIT_PRO_UPLOADS: int = 100  # per day
    RATE_LIMIT_PRO_QUERIES: int = 500

    # Cost-based rate limiting (credits per hour)
    RATE_LIMIT_FREE_CREDITS: int = 100
    RATE_LIMIT_PRO_CREDITS: int = 1000
    RATE_LIMIT_ENTERPRISE_CREDITS: int = 10000

    # Admin bypass
    ADMIN_BYPASS_TOKEN: str = "change-me-admin-token"

    @field_validator("SECRET_KEY", "JWT_SECRET_KEY", "ADMIN_BYPASS_TOKEN", mode="after")
    @classmethod
    def ensure_secret_values(
        cls, value: str, info: FieldValidationInfo
    ) -> str:  # type: ignore[override]
        """Ensure critical secrets are not left at insecure defaults."""
        env_value = str(info.data.get("ENVIRONMENT", "development")).lower()
        insecure_defaults = {
            "change-me-secret-key",
            "change-me-jwt-key",
            "change-me-admin-token",
        }
        if env_value == "production" and value in insecure_defaults:
            raise ValueError(
                f"{info.field_name} must be overridden with a secure environment value"
            )
        if len(value) < 16:
            raise ValueError(f"{info.field_name} must be at least 16 characters long")
        return value

    class Config:
        """Pydantic configuration."""

        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"


# Global settings instance
settings = Settings()
