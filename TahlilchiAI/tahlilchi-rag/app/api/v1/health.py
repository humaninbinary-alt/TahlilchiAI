"""Health check endpoints for monitoring."""

import logging
import time
from datetime import datetime
from typing import Any, Dict

import httpx
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.config import settings
from app.core.auth import require_role
from app.models.user import User, UserRole

router = APIRouter(tags=["health"])
logger = logging.getLogger(__name__)

# Track application start time
app_start_time = datetime.utcnow()


@router.get("/health")
async def health_check() -> Dict[str, str]:
    """
    Basic health check for load balancer.

    Returns:
        Simple healthy status
    """
    return {"status": "healthy"}


@router.get("/health/live")
async def liveness_check() -> Dict[str, str]:
    """
    Liveness probe - checks if API can respond.

    Returns:
        Status indicating API is alive
    """
    return {"status": "alive"}


@router.get("/health/ready")
async def readiness_check(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """
    Readiness probe - checks if all dependencies are healthy.

    Args:
        db: Database session

    Returns:
        Detailed status of all dependencies
    """
    checks = {}
    all_healthy = True

    # Check database
    try:
        start = time.time()
        await db.execute(text("SELECT 1"))
        latency = (time.time() - start) * 1000
        checks["database"] = {"status": "up", "latency_ms": round(latency, 2)}
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        checks["database"] = {"status": "down", "error": str(e)}
        all_healthy = False

    # Check Redis
    try:
        from app.services.rate_limiter import rate_limiter

        start = time.time()
        if rate_limiter.available:
            rate_limiter.redis_client.ping()
            latency = (time.time() - start) * 1000
            checks["redis"] = {"status": "up", "latency_ms": round(latency, 2)}
        else:
            checks["redis"] = {"status": "unavailable"}
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        checks["redis"] = {"status": "down", "error": str(e)}
        # Redis is optional, don't mark as unhealthy

    # Check Qdrant
    try:
        start = time.time()
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{settings.QDRANT_URL}/health", timeout=5.0)
            latency = (time.time() - start) * 1000
            if response.status_code == 200:
                checks["qdrant"] = {"status": "up", "latency_ms": round(latency, 2)}
            else:
                checks["qdrant"] = {
                    "status": "degraded",
                    "status_code": response.status_code,
                }
    except Exception as e:
        logger.error(f"Qdrant health check failed: {e}")
        checks["qdrant"] = {"status": "down", "error": str(e)}
        all_healthy = False

    # Check Ollama
    try:
        start = time.time()
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.OLLAMA_BASE_URL}/api/tags", timeout=5.0
            )
            latency = (time.time() - start) * 1000
            if response.status_code == 200:
                checks["ollama"] = {"status": "up", "latency_ms": round(latency, 2)}
            else:
                checks["ollama"] = {
                    "status": "degraded",
                    "status_code": response.status_code,
                }
    except Exception as e:
        logger.error(f"Ollama health check failed: {e}")
        checks["ollama"] = {"status": "down", "error": str(e)}
        all_healthy = False

    # Overall status
    overall_status = "healthy" if all_healthy else "unhealthy"

    return {
        "status": overall_status,
        "checks": checks,
    }


@router.get("/health/detailed")
async def detailed_health_check(
    current_user: User = Depends(require_role([UserRole.admin])),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Detailed health check for admin monitoring.

    Args:
        current_user: Admin user
        db: Database session

    Returns:
        Comprehensive system status
    """
    # Get basic checks
    basic_checks = await readiness_check(db)

    # Calculate uptime
    uptime_seconds = (datetime.utcnow() - app_start_time).total_seconds()

    # Get error counts
    from app.core.error_handler import get_error_counts

    error_counts = get_error_counts()
    total_errors = sum(error_counts.values())

    # Get metrics summary (if available)
    metrics_summary = {}
    try:
        from app.services.metrics import active_requests, requests_total

        metrics_summary = {
            "active_requests": active_requests._value.get(),
            "total_requests": (
                requests_total._metrics.get().__len__()
                if hasattr(requests_total, "_metrics")
                else 0
            ),
        }
    except Exception as e:
        logger.warning(f"Failed to get metrics summary: {e}")

    return {
        **basic_checks,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "uptime_seconds": round(uptime_seconds, 2),
        "error_counts": error_counts,
        "total_errors": total_errors,
        "metrics": metrics_summary,
    }
