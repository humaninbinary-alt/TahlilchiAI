"""Graph node and edge representations."""

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Optional


@dataclass
class GraphNode:
    """
    Represents a node in the document graph.

    Each node is an atomic unit with metadata.
    """

    node_id: str  # atomic_unit.id
    node_type: str  # section, paragraph, heading, table_row, etc.
    text: str  # actual content
    level: int  # nesting level (0=top, 1=subsection, etc.)
    sequence: int  # order in document

    # Document context
    document_id: str
    page_number: Optional[int] = None
    section_title: Optional[str] = None

    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON storage."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GraphNode":
        """Create from dictionary."""
        return cls(**data)


@dataclass
class GraphEdge:
    """
    Represents an edge (relationship) in the document graph.
    """

    source_id: str  # source node ID
    target_id: str  # target node ID
    edge_type: str  # CONTAINS, NEXT, REFERS_TO, etc.

    # Optional edge metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON storage."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GraphEdge":
        """Create from dictionary."""
        return cls(**data)


class EdgeType:
    """Standard edge types in document graph."""

    CONTAINS = "CONTAINS"  # parent -> child (section contains paragraph)
    NEXT = "NEXT"  # sequential order (paragraph -> next paragraph)
    REFERS_TO = "REFERS_TO"  # cross-reference (clause mentions article)
    PART_OF = "PART_OF"  # inverse of CONTAINS
