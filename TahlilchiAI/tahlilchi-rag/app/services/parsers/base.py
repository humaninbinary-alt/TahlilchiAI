"""Abstract base class for document parsers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class ParsedUnit:
    """
    Intermediate representation of a parsed atomic unit.

    This is the data structure returned by parsers before saving to database.
    It contains all the information needed to create an AtomicUnit model instance.
    """

    unit_type: str
    text: str
    sequence: int
    level: int
    page_number: Optional[int] = None
    section_title: Optional[str] = None
    parent_sequence: Optional[int] = None
    metadata: Optional[dict] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate parsed unit data."""
        if not self.text.strip():
            raise ValueError("ParsedUnit text cannot be empty")
        if self.sequence < 0:
            raise ValueError("ParsedUnit sequence must be non-negative")
        if self.level < 0:
            raise ValueError("ParsedUnit level must be non-negative")


class BaseDocumentParser(ABC):
    """
    Abstract base class for document parsers.

    All format-specific parsers (PDF, DOCX, TXT, etc.) must inherit from this
    class and implement the parse() and validate_file() methods.

    This ensures a consistent interface for all parsers and makes it easy to
    add new document formats in the future.
    """

    @abstractmethod
    def parse(self, file_path: Path) -> list[ParsedUnit]:
        """
        Parse a document and return list of atomic units.

        Args:
            file_path: Path to the document file

        Returns:
            List of ParsedUnit objects representing the document structure

        Raises:
            ParsingError: If parsing fails
            FileCorruptedError: If file is corrupted or unreadable
        """
        pass

    @abstractmethod
    def validate_file(self, file_path: Path) -> bool:
        """
        Validate that file is readable and not corrupted.

        Args:
            file_path: Path to the document file

        Returns:
            True if file is valid and readable

        Raises:
            FileCorruptedError: If file validation fails
        """
        pass
