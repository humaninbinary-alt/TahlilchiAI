"""Main document processing orchestrator."""

import logging
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DocumentProcessingError
from app.models.atomic_unit import AtomicUnit
from app.models.document import Document
from app.services.language_detector import LanguageDetector
from app.services.parsers.base import ParsedUnit
from app.services.parsers.factory import ParserFactory
from app.services.storage_service import StorageService

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """
    Orchestrates the complete document processing pipeline.

    Pipeline steps:
    1. Load document from database
    2. Get file from storage
    3. Parse document into atomic units
    4. Detect language
    5. Save atomic units to database
    6. Update document status and metadata
    """

    def __init__(self, db: AsyncSession, storage_service: StorageService):
        """
        Initialize document processor.

        Args:
            db: Async database session
            storage_service: Storage service for file operations
        """
        self.db = db
        self.storage = storage_service
        self.language_detector = LanguageDetector()

    async def process_document(self, document_id: UUID, tenant_id: UUID) -> None:
        """
        Process a document through the full pipeline.

        Args:
            document_id: ID of document to process
            tenant_id: Tenant ID for isolation

        Raises:
            DocumentProcessingError: If processing fails
            ValueError: If document not found
        """
        document: Document | None = None

        try:
            # 1. Load document from DB
            document = await self._get_document(document_id, tenant_id)
            if not document:
                raise ValueError(
                    f"Document {document_id} not found for tenant {tenant_id}"
                )

            logger.info(
                f"Processing document {document_id}: {document.filename} "
                f"(type: {document.file_type}, size: {document.file_size})"
            )

            # Update status to processing
            document.status = "processing"
            await self.db.commit()

            # 2. Get file from storage
            file_path = self.storage.get_file_path(document.file_path)
            if not file_path.exists():
                raise FileNotFoundError(
                    f"Document file not found: {document.file_path}"
                )

            # 3. Parse document
            parser = ParserFactory.get_parser(document.file_type)
            parsed_units = parser.parse(file_path)

            logger.info(
                f"Parsed {len(parsed_units)} atomic units from document {document_id}"
            )

            # 4. Detect language
            # Sample first 10 units for language detection
            sample_text = " ".join([unit.text for unit in parsed_units[:10]])
            detected_lang = self.language_detector.detect_language(sample_text)

            logger.info(f"Detected language: {detected_lang}")

            # 5. Save atomic units to DB
            await self._save_atomic_units(
                parsed_units=parsed_units, document=document, tenant_id=tenant_id
            )

            # 6. Update document metadata
            document.detected_language = detected_lang
            document.word_count = sum(len(u.text.split()) for u in parsed_units)
            document.status = "processed"
            document.processed_at = datetime.utcnow()
            document.error_message = None  # Clear any previous errors

            await self.db.commit()

            logger.info(
                f"Successfully processed document {document_id}: "
                f"{len(parsed_units)} units, {document.word_count} words, language: {detected_lang}"
            )

        except Exception as e:
            logger.error(
                f"Document processing failed for {document_id}: {e}", exc_info=True
            )

            # Update document status to failed
            if document:
                document.status = "failed"
                document.error_message = str(e)[:1000]  # Truncate to fit DB column
                await self.db.commit()

            raise DocumentProcessingError(
                f"Processing failed for document {document_id}: {e}"
            )

    async def _get_document(
        self, document_id: UUID, tenant_id: UUID
    ) -> Document | None:
        """
        Load document from database with tenant isolation.

        Args:
            document_id: Document ID
            tenant_id: Tenant ID for isolation

        Returns:
            Document instance or None if not found
        """
        query = select(Document).where(
            Document.id == document_id, Document.tenant_id == tenant_id
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def _save_atomic_units(
        self, parsed_units: list[ParsedUnit], document: Document, tenant_id: UUID
    ) -> None:
        """
        Save parsed units to database as AtomicUnit records.

        Args:
            parsed_units: List of parsed units from parser
            document: Document model instance
            tenant_id: Tenant ID for isolation
        """
        atomic_units: list[AtomicUnit] = []

        for unit in parsed_units:
            atomic_unit = AtomicUnit(
                id=uuid4(),
                tenant_id=tenant_id,
                document_id=document.id,
                chat_id=document.chat_id,
                unit_type=unit.unit_type,
                text=unit.text,
                sequence=unit.sequence,
                level=unit.level,
                page_number=unit.page_number,
                section_title=unit.section_title,
                parent_id=None,  # Parent-child linking reserved for future hierarchy support
                metadata_json=unit.metadata or {},
            )
            atomic_units.append(atomic_unit)

        # Bulk insert for performance
        self.db.add_all(atomic_units)
        await self.db.flush()  # Flush but don't commit yet

        logger.debug(f"Saved {len(atomic_units)} atomic units to database")
