"""
Similarity Calculator for Template Matching.

Calculates similarity scores between templates and queries using
semantic, visual, and structural features.
"""
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
import numpy as np

from myslides.generation.generation_models import SlideType


@dataclass
class SimilarityScore:
    """Container for similarity calculation results."""
    semantic_score: float  # 0.0 to 1.0
    visual_score: float  # 0.0 to 1.0
    structural_score: float  # 0.0 to 1.0
    combined_score: float  # 0.0 to 1.0

    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary."""
        return {
            "semantic_score": self.semantic_score,
            "visual_score": self.visual_score,
            "structural_score": self.structural_score,
            "combined_score": self.combined_score
        }


class SimilarityCalculator:
    """Calculates similarity scores between templates and queries."""

    def __init__(self, semantic_weight: float = 0.5, visual_weight: float = 0.3, structural_weight: float = 0.2):
        """
        Initialize similarity calculator with weights.

        Args:
            semantic_weight: Weight for semantic similarity (default 0.5)
            visual_weight: Weight for visual similarity (default 0.3)
            structural_weight: Weight for structural similarity (default 0.2)
        """
        self.semantic_weight = semantic_weight
        self.visual_weight = visual_weight
        self.structural_weight = structural_weight

    def calculate_similarity(
        self,
        query_embedding: Optional[List[float]],
        template_embedding: Optional[List[float]],
        query_slide_type: Optional[SlideType] = None,
        template_slide_type: Optional[SlideType] = None,
        query_element_count: Optional[int] = None,
        template_element_count: Optional[int] = None,
        template_metadata: Optional[Dict[str, Any]] = None
    ) -> SimilarityScore:
        """
        Calculate combined similarity score.

        Args:
            query_embedding: Query embedding vector (semantic)
            template_embedding: Template embedding vector (semantic)
            query_slide_type: Desired slide type
            template_slide_type: Template's slide type
            query_element_count: Desired number of elements (e.g., steps)
            template_element_count: Template's element count
            template_metadata: Additional template metadata

        Returns:
            SimilarityScore with individual and combined scores
        """
        semantic_score = self._calculate_semantic_similarity(query_embedding, template_embedding)
        visual_score = self._calculate_visual_similarity(template_metadata)
        structural_score = self._calculate_structural_similarity(
            query_slide_type, template_slide_type,
            query_element_count, template_element_count
        )

        combined_score = (
            self.semantic_weight * semantic_score +
            self.visual_weight * visual_score +
            self.structural_weight * structural_score
        )

        return SimilarityScore(
            semantic_score=semantic_score,
            visual_score=visual_score,
            structural_score=structural_score,
            combined_score=combined_score
        )

    def _calculate_semantic_similarity(
        self,
        query_embedding: Optional[List[float]],
        template_embedding: Optional[List[float]]
    ) -> float:
        """
        Calculate semantic similarity using cosine similarity.

        Args:
            query_embedding: Query embedding vector
            template_embedding: Template embedding vector

        Returns:
            Similarity score between 0.0 and 1.0
        """
        if not query_embedding or not template_embedding:
            return 0.0

        try:
            query_vec = np.array(query_embedding)
            template_vec = np.array(template_embedding)

            # Handle different lengths by truncating to minimum
            min_len = min(len(query_vec), len(template_vec))
            if min_len == 0:
                return 0.0

            query_vec = query_vec[:min_len]
            template_vec = template_vec[:min_len]

            # Cosine similarity
            dot_product = np.dot(query_vec, template_vec)
            norm_query = np.linalg.norm(query_vec)
            norm_template = np.linalg.norm(template_vec)

            if norm_query == 0 or norm_template == 0:
                return 0.0

            similarity = dot_product / (norm_query * norm_template)
            return float(max(0.0, min(1.0, similarity)))
        except Exception:
            return 0.0

    def _calculate_visual_similarity(self, template_metadata: Optional[Dict[str, Any]]) -> float:
        """
        Calculate visual similarity based on template metadata.

        Args:
            template_metadata: Template metadata including visual features

        Returns:
            Similarity score between 0.0 and 1.0
        """
        if not template_metadata:
            return 0.0  # No score if no metadata

        # For MVP, return a neutral score
        # In production, this would compare visual embeddings
        return 0.5

    def _calculate_structural_similarity(
        self,
        query_slide_type: Optional[SlideType],
        template_slide_type: Optional[SlideType],
        query_element_count: Optional[int],
        template_element_count: Optional[int]
    ) -> float:
        """
        Calculate structural similarity based on slide type and element count.

        Args:
            query_slide_type: Desired slide type
            template_slide_type: Template's slide type
            query_element_count: Desired element count
            template_element_count: Template's element count

        Returns:
            Similarity score between 0.0 and 1.0
        """
        score = 0.0

        # Slide type match (high weight)
        if query_slide_type and template_slide_type:
            if query_slide_type == template_slide_type:
                score += 0.7
            elif self._is_compatible_slide_type(query_slide_type, template_slide_type):
                score += 0.3

        # Element count match (medium weight)
        if query_element_count is not None and template_element_count is not None:
            if query_element_count == template_element_count:
                score += 0.3
            elif abs(query_element_count - template_element_count) <= 1:
                score += 0.15  # Close match
            else:
                # Penalize large differences
                diff_penalty = max(0, 1.0 - (abs(query_element_count - template_element_count) / 10.0))
                score += 0.15 * diff_penalty

        return min(1.0, score)

    def _is_compatible_slide_type(self, query_type: SlideType, template_type: SlideType) -> bool:
        """
        Check if two slide types are compatible for substitution.

        Args:
            query_type: Desired slide type
            template_type: Template's slide type

        Returns:
            True if types are compatible
        """
        # Define compatibility rules
        compatible_pairs = {
            SlideType.TEXT_HEAVY: [SlideType.TITLE_SLIDE],
            SlideType.COMPARISON: [SlideType.TEXT_HEAVY],
            SlideType.PROCESS_FLOW: [SlideType.TIMELINE],
            SlideType.TIMELINE: [SlideType.PROCESS_FLOW],
        }

        return template_type in compatible_pairs.get(query_type, [])
