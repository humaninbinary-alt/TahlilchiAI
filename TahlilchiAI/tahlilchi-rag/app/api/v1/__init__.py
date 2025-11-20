"""API v1 routes."""

from fastapi import APIRouter

from app.api.v1 import (
    answer,
    auth,
    bm25,
    chats,
    conversations,
    documents,
    graph,
    health,
    indexing,
    jobs,
    metrics_endpoint,
    retrieval,
    router,
)
from app.api.v1.admin import metrics as admin_metrics

api_router = APIRouter()

# Include routers
api_router.include_router(chats.router)
api_router.include_router(conversations.router)
api_router.include_router(documents.router)
api_router.include_router(indexing.router)
api_router.include_router(bm25.router)
api_router.include_router(graph.router)
api_router.include_router(retrieval.router)
api_router.include_router(router.router)
api_router.include_router(answer.router)
api_router.include_router(jobs.router)
api_router.include_router(auth.router)
api_router.include_router(health.router)
api_router.include_router(metrics_endpoint.router)
api_router.include_router(admin_metrics.router)
