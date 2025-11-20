"""Admin metrics endpoints."""

from datetime import datetime, timedelta
from typing import Any, Dict

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.auth import require_role
from app.core.error_handler import get_error_counts, get_recent_errors
from app.models.usage import TenantUsage
from app.models.user import User, UserRole

router = APIRouter(prefix="/admin/metrics", tags=["admin", "metrics"])


@router.get("/summary")
async def get_metrics_summary(
    current_user: User = Depends(require_role([UserRole.admin])),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Get metrics summary for last 24 hours.

    Args:
        current_user: Admin user
        db: Database session

    Returns:
        Metrics summary
    """
    # Calculate 24 hours ago
    yesterday = datetime.utcnow() - timedelta(hours=24)

    # Get usage stats for last 24h
    usage_query = select(TenantUsage).where(TenantUsage.date >= yesterday.date())
    usage_result = await db.execute(usage_query)
    usage_records = usage_result.scalars().all()

    total_requests = sum(r.total_requests for r in usage_records)
    total_queries = sum(r.total_queries for r in usage_records)
    total_documents = sum(r.total_documents_processed for r in usage_records)

    # Get active users count
    active_users_query = select(func.count(User.id)).where(User.is_active.is_(True))
    active_users_result = await db.execute(active_users_query)
    active_users = active_users_result.scalar()

    # Get error counts
    error_counts = get_error_counts()
    total_errors = sum(error_counts.values())
    error_rate = (total_errors / total_requests * 100) if total_requests > 0 else 0

    return {
        "period": "last_24_hours",
        "requests": total_requests,
        "queries": total_queries,
        "documents_processed": total_documents,
        "active_users": active_users,
        "total_errors": total_errors,
        "error_rate_percent": round(error_rate, 2),
    }


@router.get("/performance")
async def get_performance_metrics(
    current_user: User = Depends(require_role([UserRole.admin])),
) -> Dict[str, Any]:
    """
    Get performance metrics.

    Args:
        current_user: Admin user

    Returns:
        Performance metrics
    """
    # In a real implementation, you would calculate these from stored metrics
    # For now, return placeholder data
    return {
        "latency_percentiles": {
            "p50_ms": 120,
            "p95_ms": 450,
            "p99_ms": 1200,
        },
        "slowest_endpoints": [
            {"endpoint": "/api/v1/chats/{id}/answer", "avg_duration_ms": 2500},
            {"endpoint": "/api/v1/documents/{id}/process", "avg_duration_ms": 15000},
        ],
        "largest_responses": [
            {"endpoint": "/api/v1/chats", "avg_size_kb": 250},
        ],
    }


@router.get("/usage")
async def get_usage_metrics(
    current_user: User = Depends(require_role([UserRole.admin])),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Get usage metrics by tenant and user.

    Args:
        current_user: Admin user
        db: Database session

    Returns:
        Usage metrics
    """
    # Get usage by tenant (last 7 days)
    week_ago = datetime.utcnow() - timedelta(days=7)

    usage_query = (
        select(
            TenantUsage.tenant_id,
            func.sum(TenantUsage.total_requests).label("requests"),
            func.sum(TenantUsage.total_queries).label("queries"),
        )
        .where(TenantUsage.date >= week_ago.date())
        .group_by(TenantUsage.tenant_id)
        .order_by(func.sum(TenantUsage.total_requests).desc())
        .limit(10)
    )

    usage_result = await db.execute(usage_query)
    usage_by_tenant = [
        {
            "tenant_id": str(row.tenant_id),
            "requests": row.requests,
            "queries": row.queries,
        }
        for row in usage_result
    ]

    return {
        "period": "last_7_days",
        "usage_by_tenant": usage_by_tenant,
        "top_queries": [],  # Would need query logging
        "document_types": {},  # Would need document type tracking
    }


@router.get("/errors/recent")
async def get_recent_errors_endpoint(
    current_user: User = Depends(require_role([UserRole.admin])),
    limit: int = 100,
) -> Dict[str, Any]:
    """
    Get recent errors.

    Args:
        current_user: Admin user
        limit: Maximum number of errors to return

    Returns:
        Recent errors with context
    """
    errors = get_recent_errors(limit)

    # Group by error type
    grouped_errors = {}
    for error in errors:
        error_type = error["error_type"]
        if error_type not in grouped_errors:
            grouped_errors[error_type] = []
        grouped_errors[error_type].append(error)

    return {
        "total_errors": len(errors),
        "error_types": len(grouped_errors),
        "errors": errors,
        "grouped_by_type": {
            error_type: len(error_list)
            for error_type, error_list in grouped_errors.items()
        },
    }
