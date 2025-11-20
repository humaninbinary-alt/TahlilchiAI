"""API endpoints for adaptive query router."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.auth import get_current_user
from app.core.exceptions import RouterError
from app.models.user import User
from app.schemas.router import RouterRequest, RoutingDecision
from app.services.router.adaptive_router import AdaptiveRouter

router = APIRouter(prefix="/router", tags=["router"])


@router.post("/route", response_model=RoutingDecision)
async def route_query(
    request: RouterRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RoutingDecision:
    """
    Analyze query and get optimal retrieval strategy.

    This endpoint is useful for:
    - Debugging routing decisions
    - Understanding why a certain mode was chosen
    - Testing query classification

    In production, routing happens automatically in the chat endpoint.

    Args:
        request: RouterRequest with query and chat_id
        tenant_id: Tenant identifier (from auth)
        db: Database session

    Returns:
        RoutingDecision with selected strategy and reasoning

    Raises:
        HTTPException: If routing fails
    """
    adaptive_router = AdaptiveRouter(db)

    try:
        decision = await adaptive_router.route(request, current_user.tenant_id)
        return decision

    except RouterError as e:
        raise HTTPException(status_code=500, detail=str(e))
