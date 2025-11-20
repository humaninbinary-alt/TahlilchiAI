"""Prometheus metrics endpoint."""

import secrets

from fastapi import APIRouter, Depends, Header, HTTPException, Response, status
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.config import settings

router = APIRouter(tags=["metrics"])


def verify_metrics_access(
    x_admin_token: str = Header(..., alias="X-Admin-Token")
) -> None:
    """Ensure only trusted callers can hit the Prometheus endpoint."""
    if not secrets.compare_digest(x_admin_token, settings.ADMIN_BYPASS_TOKEN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid metrics access token",
        )


@router.get("/metrics")
async def metrics(_: None = Depends(verify_metrics_access)):
    """
    Expose Prometheus metrics.

    Returns:
        Prometheus-formatted metrics
    """
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
