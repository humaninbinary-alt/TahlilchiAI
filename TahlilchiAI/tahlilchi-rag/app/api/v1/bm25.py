"""API endpoints for BM25 sparse indexing operations."""

from typing import Any, Dict, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_chat_with_access, get_db
from app.core.auth import get_current_user
from app.core.exceptions import BM25Error, BM25IndexNotFoundError
from app.models.user import User
from app.services.bm25_service import BM25Service
from app.services.tokenizer import MultilingualTokenizer

router = APIRouter(prefix="/chats/{chat_id}/bm25", tags=["bm25"])


class BM25SearchRequest(BaseModel):
    """Request schema for BM25 search."""

    query: str
    top_k: int = 10


class BM25SearchResponse(BaseModel):
    """Response schema for BM25 search."""

    results: List[Dict[str, Any]]
    total: int


@router.post("/build", status_code=202)
async def build_bm25_index(
    chat_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Build BM25 sparse index for a chat.

    This creates a keyword-based search index for exact matching.
    Should be called after documents are parsed and indexed.

    Args:
        chat_id: Chat UUID
        current_user: Authenticated user (enforces tenant)
        db: Database session

    Returns:
        Dict with build statistics

    Raises:
        HTTPException: If index building fails
    """
    await get_chat_with_access(
        chat_id=chat_id,
        tenant_id=current_user.tenant_id,
        db=db,
        user=current_user,
    )

    tokenizer = MultilingualTokenizer()
    bm25_service = BM25Service(db, tokenizer)

    try:
        result = await bm25_service.build_index(chat_id, current_user.tenant_id)
        return result
    except BM25Error as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search", response_model=BM25SearchResponse)
async def search_bm25(
    chat_id: UUID,
    request: BM25SearchRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Search using BM25 sparse index (keyword-based).

    Good for:
    - Exact phrases
    - Technical terms
    - Article numbers, IDs
    - Uzbek/Russian/English queries

    Args:
        chat_id: Chat UUID
        request: Search request with query and top_k
        current_user: Authenticated user
        db: Database session

    Returns:
        Search results with scores and metadata

    Raises:
        HTTPException: If search fails or index not found
    """
    await get_chat_with_access(
        chat_id=chat_id,
        tenant_id=current_user.tenant_id,
        db=db,
        user=current_user,
    )

    tokenizer = MultilingualTokenizer()
    bm25_service = BM25Service(db, tokenizer)

    try:
        results = await bm25_service.search(
            chat_id=chat_id,
            tenant_id=current_user.tenant_id,
            query=request.query,
            top_k=request.top_k,
        )
        return BM25SearchResponse(results=results, total=len(results))
    except BM25IndexNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except BM25Error as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/", status_code=204)
async def delete_bm25_index(
    chat_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete BM25 index for a chat.

    Args:
        chat_id: Chat UUID
        current_user: Authenticated user
        db: Database session

    Raises:
        HTTPException: If index not found
    """
    await get_chat_with_access(
        chat_id=chat_id,
        tenant_id=current_user.tenant_id,
        db=db,
        user=current_user,
    )

    tokenizer = MultilingualTokenizer()
    bm25_service = BM25Service(db, tokenizer)

    success = await bm25_service.delete_index(chat_id, current_user.tenant_id)
    if not success:
        raise HTTPException(status_code=404, detail="BM25 index not found")
    return None
