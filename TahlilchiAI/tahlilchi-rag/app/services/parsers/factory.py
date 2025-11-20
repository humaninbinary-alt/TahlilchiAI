"""Parser factory for creating appropriate parser based on file type."""

import logging
from typing import Type

from app.core.exceptions import UnsupportedFileTypeError
from app.services.parsers.base import BaseDocumentParser
from app.services.parsers.docx_parser import DOCXParser
from app.services.parsers.pdf_parser import PDFParser

logger = logging.getLogger(__name__)


class ParserFactory:
    """
    Factory for creating appropriate parser based on file type.

    This factory pattern allows easy extension with new file types
    without modifying existing code.
    """

    _parsers: dict[str, Type[BaseDocumentParser]] = {
        "pdf": PDFParser,
        "docx": DOCXParser,
        "doc": DOCXParser,  # Treat .doc same as .docx
    }

    @classmethod
    def get_parser(cls, file_type: str) -> BaseDocumentParser:
        """
        Get parser instance for given file type.

        Args:
            file_type: File extension (pdf, docx, doc, etc.)

        Returns:
            Parser instance for the specified file type

        Raises:
            UnsupportedFileTypeError: If file type is not supported
        """
        file_type_lower = file_type.lower()
        parser_class = cls._parsers.get(file_type_lower)

        if not parser_class:
            supported = ", ".join(cls._parsers.keys())
            logger.error(f"Unsupported file type requested: {file_type}")
            raise UnsupportedFileTypeError(
                f"Unsupported file type: {file_type}. Supported types: {supported}"
            )

        logger.debug(f"Creating parser for file type: {file_type}")
        return parser_class()

    @classmethod
    def register_parser(
        cls, file_type: str, parser_class: Type[BaseDocumentParser]
    ) -> None:
        """
        Register a new parser for a file type.

        This allows extending the factory with custom parsers.

        Args:
            file_type: File extension to register
            parser_class: Parser class to use for this file type
        """
        cls._parsers[file_type.lower()] = parser_class
        logger.info(f"Registered parser for file type: {file_type}")

    @classmethod
    def get_supported_types(cls) -> list[str]:
        """
        Get list of supported file types.

        Returns:
            List of supported file extensions
        """
        return list(cls._parsers.keys())
