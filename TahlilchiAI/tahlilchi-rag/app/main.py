"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1 import api_router
from app.config import settings
from app.database import async_engine
from app.core.logging_config import setup_logging
from app.middleware.database import (
    DatabasePoolMonitorMiddleware,
    DatabaseTransactionMiddleware,
)
from app.middleware.performance import PerformanceMonitoringMiddleware
from app.middleware.prometheus import PrometheusMiddleware
from app.middleware.rate_limit import GlobalRateLimitMiddleware, RateLimitMiddleware
from app.middleware.tracing import RequestTracingMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan context manager.

    Handles startup and shutdown events.
    """
    # Startup
    print("🚀 Starting TahlilchiAI Custom Chats...")
    print(
        f"📊 Database: {settings.POSTGRES_SERVER}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
    )
    print(f"🌐 API Docs: http://{settings.HOST}:{settings.PORT}/docs")

    # Test database connection (non-blocking)
    try:
        async with async_engine.begin() as conn:
            await conn.run_sync(lambda _: None)
        print("✅ Database connection successful")
    except Exception as e:
        print(f"⚠️  Database connection failed: {e}")
        print("   Server will start anyway. Some features may not work.")

    yield

    # Shutdown
    print("👋 Shutting down TahlilchiAI Custom Chats...")
    await async_engine.dispose()


# Configure logging before app initialization
setup_logging()

# Initialize FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Multi-tenant RAG platform for custom chat experiences",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    lifespan=lifespan,
)

# Configure CORS (permissive for development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins in development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Monitor database pool (only in debug mode)
if settings.DEBUG:
    app.add_middleware(DatabasePoolMonitorMiddleware)

# Core middleware stack (order of addition matters)
app.add_middleware(DatabaseTransactionMiddleware)
app.add_middleware(GlobalRateLimitMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(PerformanceMonitoringMiddleware)
app.add_middleware(PrometheusMiddleware)
app.add_middleware(RequestTracingMiddleware)


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check() -> dict[str, str]:
    """
    Health check endpoint.

    Returns:
        dict: Health status and version information
    """
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
    }


# Root endpoint
@app.get("/", tags=["Root"])
async def root() -> dict[str, str]:
    """
    Root endpoint with API information.

    Returns:
        dict: Welcome message and API documentation link
    """
    return {
        "message": f"Welcome to {settings.PROJECT_NAME}",
        "version": settings.VERSION,
        "docs": "/docs",
        "health": "/health",
    }


# LLM health check endpoint
@app.get("/health/llm", tags=["Health"])
async def llm_health() -> dict[str, Any]:
    """Check if LLM (Ollama) is healthy."""
    from app.services.llm.ollama_client import OllamaClient

    client = OllamaClient()
    is_healthy = await client.health_check()

    if is_healthy:
        return {"status": "healthy", "provider": "ollama", "model": client.model}
    else:
        return {
            "status": "unhealthy",
            "provider": "ollama",
            "error": "Model not available",
        }


# Test UI redirect
@app.get("/test", tags=["Test UI"])
async def test_ui() -> RedirectResponse:
    """Redirect to test UI."""
    return RedirectResponse(url="/static/test-ui.html")


# Include API v1 router
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


# Mount static files (must be last to not override routes)
static_dir = Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc: Exception) -> JSONResponse:
    """
    Global exception handler for unhandled errors.

    Args:
        request: The request that caused the exception
        exc: The exception that was raised

    Returns:
        JSONResponse: Error response with status 500
    """
    print(f"❌ Unhandled error: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error": str(exc) if settings.DEBUG else "An unexpected error occurred",
        },
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
