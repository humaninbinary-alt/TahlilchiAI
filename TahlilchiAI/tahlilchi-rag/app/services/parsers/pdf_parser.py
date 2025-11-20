"""PDF document parser with structure preservation."""

import logging
from pathlib import Path

import pypdf

from app.core.exceptions import FileCorruptedError, ParsingError
from app.services.parsers.base import BaseDocumentParser, ParsedUnit

logger = logging.getLogger(__name__)


class PDFParser(BaseDocumentParser):
    """
    PDF document parser with structure preservation.

    Parsing strategy:
    - Extract text page by page
    - Split into paragraphs using double newlines
    - Detect headings using heuristics (ALL CAPS, short lines)
    - Preserve page numbers for reference
    """

    def __init__(self) -> None:
        """Initialize PDF parser."""
        self.logger = logger

    def validate_file(self, file_path: Path) -> bool:
        """
        Validate PDF file is readable.

        Args:
            file_path: Path to PDF file

        Returns:
            True if file is valid

        Raises:
            FileCorruptedError: If PDF cannot be read
        """
        try:
            with open(file_path, "rb") as f:
                reader = pypdf.PdfReader(f)
                # Check if we can read page count
                page_count = len(reader.pages)
                self.logger.debug(f"PDF validation successful: {page_count} pages")
            return True
        except Exception as e:
            self.logger.error(f"PDF validation failed for {file_path}: {e}")
            raise FileCorruptedError(f"Cannot read PDF file: {e}")

    def parse(self, file_path: Path) -> list[ParsedUnit]:
        """
        Parse PDF into atomic units.

        Args:
            file_path: Path to PDF file

        Returns:
            List of ParsedUnit objects

        Raises:
            ParsingError: If parsing fails
            FileCorruptedError: If file is corrupted
        """
        self.validate_file(file_path)

        units: list[ParsedUnit] = []
        sequence = 0

        try:
            with open(file_path, "rb") as f:
                reader = pypdf.PdfReader(f)

                for page_num, page in enumerate(reader.pages, start=1):
                    text = page.extract_text()
                    if not text.strip():
                        self.logger.debug(f"Skipping empty page {page_num}")
                        continue

                    # Split into paragraphs
                    paragraphs = self._split_into_paragraphs(text)

                    for para in paragraphs:
                        if not para.strip():
                            continue

                        # Detect if this is a heading
                        unit_type = self._detect_unit_type(para)
                        level = 0 if unit_type == "heading" else 1

                        units.append(
                            ParsedUnit(
                                unit_type=unit_type,
                                text=para.strip(),
                                sequence=sequence,
                                level=level,
                                page_number=page_num,
                                section_title=None,  # Will be enriched later
                                parent_sequence=None,
                                metadata={"source": "pdf"},
                            )
                        )
                        sequence += 1

            self.logger.info(f"Parsed {len(units)} units from PDF: {file_path.name}")
            return units

        except Exception as e:
            self.logger.error(f"PDF parsing failed for {file_path}: {e}")
            raise ParsingError(f"Failed to parse PDF: {e}")

    def _split_into_paragraphs(self, text: str) -> list[str]:
        """
        Split text into paragraphs using double newlines.

        Args:
            text: Raw text from PDF page

        Returns:
            List of paragraph strings
        """
        return [p.strip() for p in text.split("\n\n") if p.strip()]

    def _detect_unit_type(self, text: str) -> str:
        """
        Simple heuristic to detect if text is a heading.

        Heuristics:
        - All caps
        - Short (< 100 chars)
        - No ending punctuation

        Args:
            text: Text to analyze

        Returns:
            'heading' or 'paragraph'
        """
        text_clean = text.strip()

        # Check if all caps (and has letters)
        if (
            len(text_clean) < 100
            and text_clean.isupper()
            and any(c.isalpha() for c in text_clean)
        ):
            return "heading"

        # Check if short and no ending punctuation
        if len(text_clean) < 80 and not text_clean.endswith((".", "!", "?")):
            return "heading"

        return "paragraph"
