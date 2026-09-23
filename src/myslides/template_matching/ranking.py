"""
Template Ranking for Template Matching.

Ranks templates by similarity scores and applies filtering
and adaptive element count matching.
"""
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum

from myslides.generation.generation_models import SlideType
from myslides.template_matching.similarity_calculator import SimilarityScore


class RankingStrategy(Enum):
    """Strategies for ranking templates."""
    SIMILARITY = "similarity"  # Rank by combined similarity score
    SEMANTIC = "semantic"  # Rank by semantic similarity
    VISUAL = "visual"  # Rank by visual similarity
    STRUCTURAL = "structural"  # Rank by structural similarity


@dataclass
class RankedTemplate:
    """Container for a ranked template."""
    template_id: str
    template_data: Dict[str, Any]
    similarity_score: SimilarityScore
    rank: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "template_id": self.template_id,
            "template_data": self.template_data,
            "similarity_score": self.similarity_score.to_dict(),
            "rank": self.rank
        }


class TemplateRanker:
    """Ranks templates based on similarity scores and filters."""

    def __init__(self, strategy: RankingStrategy = RankingStrategy.SIMILARITY):
        """
        Initialize template ranker.

        Args:
            strategy: Ranking strategy to use
        """
        self.strategy = strategy

    def rank_templates(
        self,
        scored_templates: List[Dict[str, Any]],
        max_results: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[RankedTemplate]:
        """
        Rank templates by similarity score with optional filtering.

        Args:
            scored_templates: List of templates with similarity scores
            max_results: Maximum number of results to return
            filters: Optional filters (slide_type, complexity, tags, etc.)

        Returns:
            List of ranked templates
        """
        # Apply filters
        filtered = self._apply_filters(scored_templates, filters)

        # Sort by ranking strategy
        sorted_templates = self._sort_by_strategy(filtered)

        # Assign ranks
        ranked = []
        for i, template in enumerate(sorted_templates[:max_results]):
            ranked.append(RankedTemplate(
                template_id=template.get("template_id", ""),
                template_data=template.get("template_data", {}),
                similarity_score=template.get("similarity_score"),
                rank=i + 1
            ))

        return ranked

    def rank_by_adaptive_element_count(
        self,
        scored_templates: List[Dict[str, Any]],
        desired_element_count: int,
        max_results: int = 10
    ) -> List[RankedTemplate]:
        """
        Rank templates with adaptive element count matching.

        Prioritizes templates with matching or close element counts.
        Creates copies to avoid mutating input objects.

        Args:
            scored_templates: List of templates with similarity scores
            desired_element_count: Desired number of elements
            max_results: Maximum number of results to return

        Returns:
            List of ranked templates with element count adaptation
        """
        adjusted_templates = []
        for template in scored_templates:
            template_copy = dict(template)
            template_data = template_copy.get("template_data", {})
            element_count = template_data.get("element_count", 0)

            if element_count == 0:
                penalty = 0.5  # Unknown element count
            elif element_count == desired_element_count:
                penalty = 0.0  # Perfect match
            elif abs(element_count - desired_element_count) <= 1:
                penalty = 0.1  # Close match
            elif abs(element_count - desired_element_count) <= 2:
                penalty = 0.2  # Reasonable match
            else:
                # Linear penalty for larger differences
                penalty = min(0.5, 0.2 + (abs(element_count - desired_element_count) - 2) * 0.05)

            similarity = template_copy.get("similarity_score")
            if similarity:
                adjusted_score = similarity.combined_score * (1.0 - penalty)
                # Avoid mutating caller's object
                new_sim = SimilarityScore(
                    semantic_score=similarity.semantic_score,
                    visual_score=similarity.visual_score,
                    structural_score=similarity.structural_score,
                    combined_score=adjusted_score
                )
                template_copy["similarity_score"] = new_sim

            adjusted_templates.append(template_copy)

        # Re-rank with adjusted scores
        return self.rank_templates(adjusted_templates, max_results=max_results)

    def _apply_filters(
        self,
        templates: List[Dict[str, Any]],
        filters: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Apply filters to template list.

        Args:
            templates: List of templates
            filters: Filter criteria

        Returns:
            Filtered list of templates
        """
        if not filters:
            return templates

        filtered = []
        for template in templates:
            template_data = template.get("template_data", {})

            # Slide type filter
            if "slide_type" in filters:
                if template_data.get("slide_type") != filters["slide_type"]:
                    continue

            # Complexity filter
            if "min_complexity" in filters:
                if template_data.get("complexity_score", 0) < filters["min_complexity"]:
                    continue
            if "max_complexity" in filters:
                if template_data.get("complexity_score", 0) > filters["max_complexity"]:
                    continue

            # Tag filter
            if "required_tags" in filters:
                template_tags = set(template_data.get("tags", []))
                required_tags = set(filters["required_tags"])
                if not required_tags.issubset(template_tags):
                    continue

            # Element count filter
            if "min_element_count" in filters:
                if template_data.get("element_count", 0) < filters["min_element_count"]:
                    continue
            if "max_element_count" in filters:
                if template_data.get("element_count", 0) > filters["max_element_count"]:
                    continue

            filtered.append(template)

        return filtered

    def _sort_by_strategy(self, templates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Sort templates by ranking strategy.

        Args:
            templates: List of templates with similarity scores

        Returns:
            Sorted list of templates
        """
        def get_sort_key(template: Dict[str, Any]) -> float:
            similarity = template.get("similarity_score")
            if not similarity:
                return 0.0

            if self.strategy == RankingStrategy.SIMILARITY:
                return similarity.combined_score
            elif self.strategy == RankingStrategy.SEMANTIC:
                return similarity.semantic_score
            elif self.strategy == RankingStrategy.VISUAL:
                return similarity.visual_score
            elif self.strategy == RankingStrategy.STRUCTURAL:
                return similarity.structural_score
            else:
                return similarity.combined_score

        return sorted(templates, key=get_sort_key, reverse=True)
