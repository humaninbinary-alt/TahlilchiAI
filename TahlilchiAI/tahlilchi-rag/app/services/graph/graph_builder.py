"""Graph builder for constructing document knowledge structure."""

import logging
import re
from typing import Dict, List, Tuple

from app.models.atomic_unit import AtomicUnit
from app.services.graph.node import EdgeType, GraphEdge, GraphNode

logger = logging.getLogger(__name__)


class GraphBuilder:
    """
    Builds document structure graph from atomic units.

    Creates:
    1. Nodes from atomic units
    2. CONTAINS edges (parent-child based on level)
    3. NEXT edges (sequential order)
    4. REFERS_TO edges (cross-references detected in text)
    """

    def __init__(self):
        """Initialize graph builder."""
        self.logger = logger

    def build_graph(
        self, atomic_units: List[AtomicUnit]
    ) -> Tuple[Dict[str, GraphNode], List[GraphEdge]]:
        """
        Build graph structure from atomic units.

        Args:
            atomic_units: List of AtomicUnit objects (sorted by sequence)

        Returns:
            Tuple of (nodes_dict, edges_list)
            - nodes_dict: {node_id: GraphNode}
            - edges_list: [GraphEdge, ...]
        """
        if not atomic_units:
            return {}, []

        self.logger.info(f"Building graph from {len(atomic_units)} atomic units")

        # 1. Create nodes
        nodes = self._create_nodes(atomic_units)

        # 2. Create edges
        edges = []
        edges.extend(self._create_hierarchy_edges(atomic_units))
        edges.extend(self._create_sequence_edges(atomic_units))
        edges.extend(self._create_reference_edges(atomic_units, nodes))

        self.logger.info(f"Graph built: {len(nodes)} nodes, {len(edges)} edges")

        return nodes, edges

    def _create_nodes(self, atomic_units: List[AtomicUnit]) -> Dict[str, GraphNode]:
        """
        Convert atomic units to graph nodes.

        Args:
            atomic_units: List of atomic units

        Returns:
            Dictionary mapping node_id to GraphNode
        """
        nodes = {}

        for unit in atomic_units:
            node = GraphNode(
                node_id=str(unit.id),
                node_type=unit.unit_type,
                text=unit.text,
                level=unit.level,
                sequence=unit.sequence,
                document_id=str(unit.document_id),
                page_number=unit.page_number,
                section_title=unit.section_title,
                metadata=unit.metadata_json or {},
            )
            nodes[node.node_id] = node

        return nodes

    def _create_hierarchy_edges(
        self, atomic_units: List[AtomicUnit]
    ) -> List[GraphEdge]:
        """
        Create CONTAINS edges based on hierarchy levels.

        Strategy:
        - Lower level units are contained by nearest higher level unit before them
        - Example: level 0 (section) CONTAINS level 1 (paragraph)

        Args:
            atomic_units: List of atomic units

        Returns:
            List of CONTAINS edges
        """
        edges = []
        parent_stack = []  # Stack of (level, unit_id)

        for unit in atomic_units:
            # Pop parents that are at same or lower level
            while parent_stack and parent_stack[-1][0] >= unit.level:
                parent_stack.pop()

            # If there's a parent, create CONTAINS edge
            if parent_stack:
                parent_id = parent_stack[-1][1]
                edges.append(
                    GraphEdge(
                        source_id=str(parent_id),
                        target_id=str(unit.id),
                        edge_type=EdgeType.CONTAINS,
                        metadata={"hierarchy": True},
                    )
                )

            # Add current unit to stack (potential parent for next units)
            parent_stack.append((unit.level, unit.id))

        self.logger.info(f"Created {len(edges)} CONTAINS edges")
        return edges

    def _create_sequence_edges(self, atomic_units: List[AtomicUnit]) -> List[GraphEdge]:
        """
        Create NEXT edges for sequential order.

        Connect each unit to the next one in sequence.

        Args:
            atomic_units: List of atomic units

        Returns:
            List of NEXT edges
        """
        edges = []

        for i in range(len(atomic_units) - 1):
            edges.append(
                GraphEdge(
                    source_id=str(atomic_units[i].id),
                    target_id=str(atomic_units[i + 1].id),
                    edge_type=EdgeType.NEXT,
                    metadata={"sequence_gap": 1},
                )
            )

        self.logger.info(f"Created {len(edges)} NEXT edges")
        return edges

    def _create_reference_edges(
        self, atomic_units: List[AtomicUnit], nodes: Dict[str, GraphNode]
    ) -> List[GraphEdge]:
        """
        Create REFERS_TO edges by detecting cross-references in text.

        Detects patterns like:
        - "Article 27"
        - "Section 3.2"
        - "Clause 15"
        - "modda 27" (Uzbek)
        - "статья 27" (Russian)

        Args:
            atomic_units: List of atomic units
            nodes: Dictionary of graph nodes

        Returns:
            List of REFERS_TO edges
        """
        edges = []

        # Build a lookup of section titles/headings
        heading_lookup = {}
        for node in nodes.values():
            if node.node_type in ["heading", "section"]:
                # Extract numbers from text
                numbers = re.findall(r"\d+", node.text)
                if numbers:
                    heading_lookup[numbers[0]] = node.node_id

        # Patterns to detect references
        patterns = [
            r"[Aa]rticle\s+(\d+)",  # English
            r"[Ss]ection\s+(\d+)",
            r"[Cc]lause\s+(\d+)",
            r"[Mm]odda\s+(\d+)",  # Uzbek
            r"[Бб]о[лъ]им\s+(\d+)",
            r"[Сс]татья\s+(\d+)",  # Russian
        ]

        combined_pattern = "|".join(f"({p})" for p in patterns)

        for unit in atomic_units:
            # Find all reference mentions in this unit's text
            matches = re.finditer(combined_pattern, unit.text)

            for match in matches:
                # Extract the number
                number = None
                for group in match.groups():
                    if group and re.search(r"\d+", group):
                        number_match = re.search(r"\d+", group)
                        if number_match:
                            number = number_match.group(0)
                            break

                if number and number in heading_lookup:
                    target_id = heading_lookup[number]
                    # Don't create self-references
                    if str(unit.id) != target_id:
                        edges.append(
                            GraphEdge(
                                source_id=str(unit.id),
                                target_id=target_id,
                                edge_type=EdgeType.REFERS_TO,
                                metadata={
                                    "reference_text": match.group(0),
                                    "reference_number": number,
                                },
                            )
                        )

        self.logger.info(f"Created {len(edges)} REFERS_TO edges")
        return edges
