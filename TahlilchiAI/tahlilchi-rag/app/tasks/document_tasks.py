"""Background tasks for document processing and indexing."""

import logging
from typing import Any, Dict
from uuid import UUID

from celery import chain
from sqlalchemy import select

from app.celery_app import celery_app
from app.database import AsyncSessionLocal
from app.models.document import Document
from app.models.job import Job
from app.services.bm25_service import BM25Service
from app.services.document_processor import DocumentProcessor
from app.services.embedding_service import EmbeddingService
from app.services.graph.graph_service import GraphService
from app.services.indexing_service import IndexingService
from app.services.tokenizer import MultilingualTokenizer
from app.services.vector_store import QdrantVectorStore

logger = logging.getLogger(__name__)


async def update_job_status(
    job_id: str,
    status: str,
    progress: int = 0,
    result: Dict[str, Any] | None = None,
    error_message: str | None = None,
) -> None:
    """Update job status in database."""
    async with AsyncSessionLocal() as db:
        try:
            query = select(Job).where(Job.id == job_id)
            result_obj = await db.execute(query)
            job = result_obj.scalar_one_or_none()

            if job:
                job.status = status
                job.progress = progress
                if result:
                    job.result = result
                if error_message:
                    job.error_message = error_message

                await db.commit()
        except Exception as e:
            logger.error(f"Failed to update job status: {e}")
            await db.rollback()


async def update_document_status(
    document_id: UUID, status: str, error_message: str | None = None
) -> None:
    """Update document status in database."""
    async with AsyncSessionLocal() as db:
        try:
            query = select(Document).where(Document.id == document_id)
            result = await db.execute(query)
            doc = result.scalar_one_or_none()

            if doc:
                doc.status = status
                if error_message:
                    doc.error_message = error_message

                await db.commit()
        except Exception as e:
            logger.error(f"Failed to update document status: {e}")
            await db.rollback()


@celery_app.task(
    bind=True, max_retries=3, name="app.tasks.document_tasks.process_document"
)
def process_document_task(self, document_id: str, tenant_id: str) -> Dict[str, Any]:
    """
    Process document: parse PDF/DOCX into atomic units.

    Args:
        self: Celery task instance
        document_id: Document UUID
        tenant_id: Tenant UUID

    Returns:
        Dict with processing results
    """
    import asyncio

    job_id = self.request.id
    logger.info(f"Starting document processing: {document_id}")

    async def _process():
        try:
            # Update job status
            await update_job_status(job_id, "processing", progress=10)
            await update_document_status(UUID(document_id), "processing")

            # Initialize processor
            async with AsyncSessionLocal() as db:
                processor = DocumentProcessor(db)

                # Update progress
                self.update_state(
                    state="PROGRESS",
                    meta={"current": 30, "total": 100, "status": "Parsing document..."},
                )
                await update_job_status(job_id, "processing", progress=30)

                # Process document
                atomic_units = await processor.process_document(
                    document_id=UUID(document_id), tenant_id=UUID(tenant_id)
                )

                # Update progress
                self.update_state(
                    state="PROGRESS",
                    meta={
                        "current": 90,
                        "total": 100,
                        "status": f"Created {len(atomic_units)} atomic units",
                    },
                )
                await update_job_status(job_id, "processing", progress=90)

                # Mark as processed
                await update_document_status(UUID(document_id), "processed")

                result = {
                    "document_id": document_id,
                    "atomic_units_count": len(atomic_units),
                    "status": "processed",
                }

                await update_job_status(
                    job_id, "completed", progress=100, result=result
                )

                logger.info(
                    f"Document processing completed: {document_id}, {len(atomic_units)} units"
                )
                return result

        except Exception as e:
            logger.error(f"Document processing failed: {e}")
            await update_document_status(
                UUID(document_id), "failed", error_message=str(e)
            )
            await update_job_status(job_id, "failed", progress=0, error_message=str(e))

            # Retry if not max retries
            if self.request.retries < self.max_retries:
                raise self.retry(exc=e, countdown=60)  # Retry after 1 minute

            raise

    return asyncio.run(_process())


@celery_app.task(
    bind=True, max_retries=3, name="app.tasks.document_tasks.index_document"
)
def index_document_task(
    self, document_id: str, tenant_id: str, chat_id: str
) -> Dict[str, Any]:
    """
    Index document: embed, store in Qdrant, build BM25, build graph.

    Args:
        self: Celery task instance
        document_id: Document UUID
        tenant_id: Tenant UUID
        chat_id: Chat UUID

    Returns:
        Dict with indexing results
    """
    import asyncio

    job_id = self.request.id
    logger.info(f"Starting document indexing: {document_id}")

    async def _index():
        try:
            # Update job status
            await update_job_status(job_id, "processing", progress=10)
            await update_document_status(UUID(document_id), "indexing")

            async with AsyncSessionLocal() as db:
                # Initialize services
                embedding_service = EmbeddingService()
                vector_store = QdrantVectorStore()
                tokenizer = MultilingualTokenizer()
                bm25_service = BM25Service(db, tokenizer)
                graph_service = GraphService(db)

                indexing_service = IndexingService(
                    db=db,
                    embedding_service=embedding_service,
                    vector_store=vector_store,
                    bm25_service=bm25_service,
                    graph_service=graph_service,
                )

                # Update progress - Embedding
                self.update_state(
                    state="PROGRESS",
                    meta={
                        "current": 30,
                        "total": 100,
                        "status": "Generating embeddings...",
                    },
                )
                await update_job_status(job_id, "processing", progress=30)

                # Index document
                stats = await indexing_service.index_document(
                    document_id=UUID(document_id),
                    tenant_id=UUID(tenant_id),
                    chat_id=UUID(chat_id),
                )

                # Update progress - Complete
                await update_job_status(job_id, "processing", progress=90)

                # Mark as indexed
                await update_document_status(UUID(document_id), "indexed")

                result = {
                    "document_id": document_id,
                    "vectors_indexed": stats.get("vectors_indexed", 0),
                    "bm25_indexed": stats.get("bm25_indexed", False),
                    "graph_nodes": stats.get("graph_nodes", 0),
                    "status": "indexed",
                }

                await update_job_status(
                    job_id, "completed", progress=100, result=result
                )

                logger.info(f"Document indexing completed: {document_id}")
                return result

        except Exception as e:
            logger.error(f"Document indexing failed: {e}")
            await update_document_status(
                UUID(document_id), "failed", error_message=str(e)
            )
            await update_job_status(job_id, "failed", progress=0, error_message=str(e))

            # Retry if not max retries
            if self.request.retries < self.max_retries:
                raise self.retry(exc=e, countdown=60)

            raise

    return asyncio.run(_index())


@celery_app.task(bind=True, name="app.tasks.document_tasks.process_and_index_document")
def process_and_index_document_task(
    self, document_id: str, tenant_id: str, chat_id: str
) -> Dict[str, Any]:
    """
    Complete pipeline: process then index document.

    Args:
        self: Celery task instance
        document_id: Document UUID
        tenant_id: Tenant UUID
        chat_id: Chat UUID

    Returns:
        Dict with complete pipeline results
    """
    job_id = self.request.id
    logger.info(f"Starting complete document pipeline: {document_id}")

    # Chain tasks: process → index
    workflow = chain(
        process_document_task.s(document_id, tenant_id),
        index_document_task.s(document_id, tenant_id, chat_id),
    )

    # Execute chain
    result = workflow.apply_async()

    return {
        "job_id": job_id,
        "document_id": document_id,
        "workflow_id": result.id,
        "status": "pipeline_started",
    }
