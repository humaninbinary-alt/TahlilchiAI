"""Result fusion logic for combining multiple ranked lists."""

import logging
from collections import defaultdict
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ReciprocalRankFusion:
    """
    Reciprocal Rank Fusion (RRF) for combining ranked lists.

    RRF formula: score = sum(1 / (k + rank_i))
    where k is a constant (typically 60) and rank_i is the rank in list i.

    This gives higher weight to items ranked highly across multiple lists.
    """

    def __init__(self, k: int = 60):
        """
        Initialize RRF with constant k.

        Args:
            k: Constant for RRF formula (default: 60)
        """
        self.k = k
        self.logger = logger

    def fuse(
        self,
        ranked_lists: List[List[Dict[str, Any]]],
        weights: Optional[List[float]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fuse multiple ranked lists using RRF.

        Args:
            ranked_lists: List of ranked result lists
            weights: Optional weights for each list (default: equal weights)

        Returns:
            Single fused ranked list
        """
        if not ranked_lists:
            return []

        # Default to equal weights
        if weights is None:
            weights = [1.0] * len(ranked_lists)

        # Normalize weights
        weight_sum = sum(weights)
        weights = [w / weight_sum for w in weights]

        # Calculate RRF scores
        rrf_scores: Dict[str, float] = defaultdict(float)
        item_data: Dict[str, Dict[str, Any]] = {}

        for list_idx, ranked_list in enumerate(ranked_lists):
            weight = weights[list_idx]

            for rank, item in enumerate(ranked_list, start=1):
                item_id = item["atomic_unit_id"]

                # RRF score contribution from this list
                rrf_score = weight / (self.k + rank)
                rrf_scores[item_id] += rrf_score

                # Store item data (first occurrence)
                if item_id not in item_data:
                    item_data[item_id] = item

        # Sort by fused score
        fused_results = []
        for item_id, score in sorted(
            rrf_scores.items(), key=lambda x: x[1], reverse=True
        ):
            result = item_data[item_id].copy()
            result["score"] = float(score)
            result["source"] = "fusion"
            fused_results.append(result)

        self.logger.info(
            f"Fused {len(ranked_lists)} lists into {len(fused_results)} results"
        )
        return fused_results
