"""
Template Matcher for MySlides.

Main service for finding and ranking similar templates based on
user prompts and generation intents.
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import hashlib

import chromadb
from chromadb.config import Settings

from myslides.config import settings
from myslides.generation.generation_models import GenerationIntent, SlideType
from myslides.template_matching.similarity_calculator import SimilarityCalculator, SimilarityScore
from myslides.template_matching.ranking import TemplateRanker, RankingStrategy, RankedTemplate
from myslides.database.database_manager import DatabaseManager


@dataclass
class TemplateMatch:
    """Container for a template match result."""
    template_id: str
    template_data: Dict[str, Any]
    similarity_score: SimilarityScore
    rank: int
    match_reason: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "template_id": self.template_id,
            "template_data": self.template_data,
            "similarity_score": self.similarity_score.to_dict(),
            "rank": self.rank,
            "match_reason": self.match_reason
        }


class TemplateMatcher:
    """Main service for template matching and suggestion."""

    def __init__(
        self,
        semantic_weight: float = 0.5,
        visual_weight: float = 0.3,
        structural_weight: float = 0.2,
        ranking_strategy: RankingStrategy = RankingStrategy.SIMILARITY
    ):
        """
        Initialize template matcher.

        Args:
            semantic_weight: Weight for semantic similarity
            visual_weight: Weight for visual similarity
            structural_weight: Weight for structural similarity
            ranking_strategy: Strategy for ranking results
        """
        self.similarity_calculator = SimilarityCalculator(
            semantic_weight=semantic_weight,
            visual_weight=visual_weight,
            structural_weight=structural_weight
        )
        self.ranker = TemplateRanker(strategy=ranking_strategy)
        self.db_manager = DatabaseManager()

        # Initialize ChromaDB for vector search
        self.chroma_client = chromadb.PersistentClient(
            path=str(settings.chroma_persist_directory),
            settings=Settings(anonymized_telemetry=False)
        )
        self.semantic_collection = None
        self.visual_collection = None
        self._initialize_collections()

    def _initialize_collections(self) -> None:
        """Initialize ChromaDB collections."""
        try:
            self.semantic_collection = self.chroma_client.get_or_create_collection(
                name="slide_semantic_embeddings"
            )
            self.visual_collection = self.chroma_client.get_or_create_collection(
                name="slide_visual_embeddings"
            )
        except Exception as e:
            print(f"Error initializing ChromaDB collections: {e}")

    def find_similar_templates(
        self,
        intent: GenerationIntent,
        n_results: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        use_adaptive_element_count: bool = True
    ) -> List[TemplateMatch]:
        """
        Find similar templates based on generation intent.

        Args:
            intent: Generation intent from LLM
            n_results: Number of results to return
            filters: Optional filters (slide_type, complexity, tags, etc.)
            use_adaptive_element_count: Whether to use adaptive element count matching

        Returns:
            List of template matches
        """
        # Generate query embedding from intent
        query_embedding = self._intent_to_embedding(intent)

        # Search ChromaDB for similar templates
        similar_from_chroma = self._search_chromadb(query_embedding, n_results * 2)

        # Get full template data from database
        scored_templates = []
        for chroma_result in similar_from_chroma:
            template_id = chroma_result.get("template_id")
            if not template_id:
                continue

            template = self.db_manager.get_template_by_id(template_id)
            if not template:
                continue

            # Calculate similarity score
            template_embedding = template.semantic_embedding
            element_count = self._extract_element_count(template, intent.slide_type)

            similarity = self.similarity_calculator.calculate_similarity(
                query_embedding=query_embedding,
                template_embedding=template_embedding,
                query_slide_type=intent.slide_type,
                template_slide_type=SlideType(template.classification) if template.classification else None,
                query_element_count=self._extract_desired_element_count(intent),
                template_element_count=element_count,
                template_metadata={
                    "element_count": element_count,
                    "complexity_score": template.complexity_score,
                    "tags": template.tags or []
                }
            )

            scored_templates.append({
                "template_id": template_id,
                "template_data": template.to_dict(),
                "similarity_score": similarity
            })

        # Rank templates
        if use_adaptive_element_count:
            desired_count = self._extract_desired_element_count(intent)
            if desired_count is not None:
                ranked = self.ranker.rank_by_adaptive_element_count(
                    scored_templates, desired_count, max_results=n_results
                )
            else:
                ranked = self.ranker.rank_templates(
                    scored_templates, max_results=n_results, filters=filters
                )
        else:
            ranked = self.ranker.rank_templates(
                scored_templates, max_results=n_results, filters=filters
            )

        # Convert to TemplateMatch objects
        matches = []
        for ranked_template in ranked:
            match_reason = self._generate_match_reason(
                ranked_template.similarity_score,
                intent.slide_type
            )
            matches.append(TemplateMatch(
                template_id=ranked_template.template_id,
                template_data=ranked_template.template_data,
                similarity_score=ranked_template.similarity_score,
                rank=ranked_template.rank,
                match_reason=match_reason
            ))

        return matches

    def _deterministic_str_hash(self, text: str) -> float:
        """Deterministic string hash to float [0.0, 1.0)."""
        digest = hashlib.md5(str(text).encode('utf-8')).digest()
        val = int.from_bytes(digest[:4], byteorder='big')
        return float(val % 1000) / 1000.0

    def _intent_to_embedding(self, intent: GenerationIntent) -> List[float]:
        """
        Convert generation intent to query embedding.

        Args:
            intent: Generation intent

        Returns:
            Query embedding vector
        """
        # Feature-based embedding from intent, matching EmbeddingGenerator approach
        features = {
            "slide_type": intent.slide_type.value,
            "tone": intent.tone or "professional",
            "element_count": self._extract_desired_element_count(intent) or 0,
            "has_chart": intent.content.get("chart_data") is not None,
            "has_table": intent.content.get("table_data") is not None,
            "content_length": len(str(intent.content))
        }

        # Convert to embedding (deterministic across process restarts)
        embedding = []
        for key, value in features.items():
            if isinstance(value, (int, float)):
                embedding.append(float(value))
            elif isinstance(value, str):
                embedding.append(self._deterministic_str_hash(value))
            elif isinstance(value, bool):
                embedding.append(1.0 if value else 0.0)

        # Pad to 384 dimensions
        target_size = 384
        if len(embedding) < target_size:
            embedding.extend([0.0] * (target_size - len(embedding)))
        else:
            embedding = embedding[:target_size]

        return embedding

    def _search_chromadb(self, query_embedding: List[float], n_results: int) -> List[Dict[str, Any]]:
        """
        Search ChromaDB for similar templates.

        Args:
            query_embedding: Query embedding vector
            n_results: Number of results

        Returns:
            List of similar template information
        """
        if not self.semantic_collection:
            return []

        try:
            results = self.semantic_collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results
            )

            similar = []
            if results['ids'] and results['ids'][0]:
                for i, template_id in enumerate(results['ids'][0]):
                    similar.append({
                        "template_id": template_id,
                        "similarity": 1 - results['distances'][0][i] if results['distances'] else 0,
                        "metadata": results['metadatas'][0][i] if results['metadatas'] else {}
                    })

            return similar
        except Exception as e:
            print(f"Error searching ChromaDB: {e}")
            return []

    def _extract_element_count(self, template, slide_type: SlideType) -> int:
        """
        Extract element count from template based on slide type.
        Supports both structured element manifests and dictionary manifests.

        Args:
            template: Template database model
            slide_type: Slide type

        Returns:
            Element count
        """
        manifest = template.element_manifest or {}

        # 1. Handle mock / legacy dict format where keys are element names
        if slide_type == SlideType.PROCESS_FLOW:
            step_keys = [k for k in manifest.keys() if 'step' in k.lower()]
            if step_keys:
                return len(step_keys)
        elif slide_type == SlideType.TIMELINE:
            event_keys = [k for k in manifest.keys() if 'event' in k.lower()]
            if event_keys:
                return len(event_keys)

        # 2. Handle standard ingested manifest with "shapes", "charts", "tables", etc.
        shapes = manifest.get("shapes", []) if isinstance(manifest.get("shapes"), list) else []
        charts = manifest.get("charts", []) if isinstance(manifest.get("charts"), list) else []

        if slide_type == SlideType.PROCESS_FLOW:
            # Count shapes indicating process steps
            step_shapes = [
                s for s in shapes
                if any(kw in str(s.get("name", "")).lower() or kw in str(s.get("text", {}).get("content", "")).lower()
                       for kw in ["step", "process", "phase", "chevron", "arrow"])
            ]
            if step_shapes:
                return len(step_shapes)
            return len(shapes) if shapes else 1

        elif slide_type == SlideType.TIMELINE:
            event_shapes = [
                s for s in shapes
                if any(kw in str(s.get("name", "")).lower() or kw in str(s.get("text", {}).get("content", "")).lower()
                       for kw in ["event", "milestone", "date", "year"])
            ]
            if event_shapes:
                return len(event_shapes)
            return len(shapes) if shapes else 1

        elif slide_type == SlideType.DATA_CHART:
            if charts:
                return len(charts)
            chart_keys = [v for k, v in manifest.items() if 'chart' in k.lower()]
            return len(chart_keys) if chart_keys else 1

        return len(shapes) if shapes else len(manifest)

    def _extract_desired_element_count(self, intent: GenerationIntent) -> Optional[int]:
        """
        Extract desired element count from intent.

        Args:
            intent: Generation intent

        Returns:
            Desired element count or None
        """
        if intent.slide_type == SlideType.PROCESS_FLOW:
            steps = intent.content.get("steps", [])
            if isinstance(steps, list):
                return len(steps)
            elif isinstance(steps, dict):
                return len(steps.get("steps", []))
        elif intent.slide_type == SlideType.TIMELINE:
            events = intent.content.get("events", [])
            if isinstance(events, list):
                return len(events)
            elif isinstance(events, dict):
                return len(events.get("events", []))
        elif intent.slide_type == SlideType.DATA_CHART:
            chart_data = intent.content.get("chart_data", {})
            if isinstance(chart_data, dict):
                series_data = chart_data.get("series_data", {})
                return len(series_data) if isinstance(series_data, dict) else 1

        return None

    def _generate_match_reason(self, similarity: SimilarityScore, slide_type: SlideType) -> str:
        """
        Generate human-readable match reason.

        Args:
            similarity: Similarity score
            slide_type: Slide type

        Returns:
            Match reason string
        """
        reasons = []

        if similarity.semantic_score > 0.7:
            reasons.append("strong semantic match")
        elif similarity.semantic_score > 0.5:
            reasons.append("good semantic match")

        if similarity.structural_score > 0.7:
            reasons.append("perfect structure match")
        elif similarity.structural_score > 0.5:
            reasons.append("compatible structure")

        if similarity.visual_score > 0.7:
            reasons.append("similar visual style")

        if not reasons:
            reasons.append("moderate similarity")

        return f"{slide_type.value} with {', '.join(reasons)}"
