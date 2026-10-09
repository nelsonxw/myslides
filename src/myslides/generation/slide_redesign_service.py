"""
Slide Redesign Service for MySlides.

Analyzes an existing PowerPoint slide, extracts its core content and structure,
and discovers improved visual layouts based on what AI has learned from the
curated slides in the training dataset.
"""
import re
import tempfile
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from myslides.database.database_manager import DatabaseManager
from myslides.generation.generation_models import GenerationIntent, SlideType
from myslides.ingestion.embedding_generator import EmbeddingGenerator
from myslides.ingestion.pptx_parser import PPTXParser, SlideInfo
from myslides.ingestion.slide_classifier import SlideClassifier
from myslides.llm.prompt_parser import PromptParser
from myslides.template_matching.template_matcher import TemplateMatcher

logger = logging.getLogger(__name__)


@dataclass
class SlideAnalysisResult:
    """Container for the analysis and layout improvement recommendations."""
    original_classification: str
    extracted_title: str
    extracted_subtitle: Optional[str]
    extracted_items: List[str]
    suggested_prompt: str
    recommended_slide_types: List[str]
    parsed_intent: Dict[str, Any]
    suggested_templates: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary for API response."""
        return {
            "original_classification": self.original_classification,
            "extracted_title": self.extracted_title,
            "extracted_subtitle": self.extracted_subtitle,
            "extracted_items": self.extracted_items,
            "suggested_prompt": self.suggested_prompt,
            "recommended_slide_types": self.recommended_slide_types,
            "parsed_intent": self.parsed_intent,
            "suggested_templates": self.suggested_templates,
        }


class SlideRedesignService:
    """Service to analyze existing slides and generate layout improvement suggestions based on curated training slides."""

    def __init__(
        self,
        classifier: Optional[SlideClassifier] = None,
        prompt_parser: Optional[PromptParser] = None,
        template_matcher: Optional[TemplateMatcher] = None,
        embedding_generator: Optional[EmbeddingGenerator] = None,
        database_manager: Optional[DatabaseManager] = None,
    ):
        """Initialize SlideRedesignService."""
        self.classifier = classifier or SlideClassifier()
        if prompt_parser is None:
            try:
                from myslides.llm.llm_client import LLMClient
                self.prompt_parser = PromptParser(llm_client=LLMClient())
            except Exception:
                self.prompt_parser = PromptParser(llm_client=None)
        else:
            self.prompt_parser = prompt_parser
        self.template_matcher = template_matcher or TemplateMatcher()
        self.embedding_generator = embedding_generator or EmbeddingGenerator()
        self.database_manager = database_manager or DatabaseManager()

    def analyze_slide_file(
        self,
        pptx_path: Path | str,
        user_improvement_prompt: Optional[str] = None,
        n_suggestions: int = 5,
    ) -> SlideAnalysisResult:
        """
        Analyze a local PPTX slide file and generate improvement recommendations.

        Args:
            pptx_path: Path to the PPTX file
            user_improvement_prompt: Optional custom instructions from user
            n_suggestions: Number of curated template suggestions to retrieve

        Returns:
            SlideAnalysisResult with extracted content and recommended layouts
        """
        parser = PPTXParser(pptx_path)
        slide_info = parser.parse_slide(slide_index=0)

        return self.analyze_slide_info(
            slide_info=slide_info,
            user_improvement_prompt=user_improvement_prompt,
            n_suggestions=n_suggestions,
        )

    def analyze_slide_info(
        self,
        slide_info: SlideInfo,
        user_improvement_prompt: Optional[str] = None,
        n_suggestions: int = 5,
    ) -> SlideAnalysisResult:
        """
        Analyze parsed SlideInfo to extract content and discover improved visual layouts
        learned directly from the curated slides training vector store.
        """
        classification_category = self.classifier.classify(slide_info)
        original_classification = (
            classification_category.value
            if hasattr(classification_category, "value")
            else str(classification_category)
        )

        title, subtitle, items = self._extract_content_elements(slide_info)

        # Check for table data in slide
        table_dict = None
        columns_data = []
        if getattr(slide_info, "tables", None):
            for t in slide_info.tables:
                if t.data:
                    has_banner_row = False
                    if len(t.data) >= 2:
                        non_empty_0 = sum(1 for c in t.data[0] if str(c).strip())
                        non_empty_1 = sum(1 for c in t.data[1] if str(c).strip())
                        if non_empty_0 <= 2 and non_empty_1 >= 2:
                            has_banner_row = True

                    if has_banner_row:
                        actual_headers = t.data[1]
                        data_rows = t.data[2:]
                    else:
                        actual_headers = t.headers or t.data[0]
                        data_rows = t.data[1:] if t.has_header else t.data

                    table_dict = {
                        "headers": actual_headers,
                        "rows": data_rows,
                    }

                    if len(actual_headers) >= 3:
                        data_cols_start = (
                            1
                            if (
                                not actual_headers[0]
                                or any(w in actual_headers[0].lower() for w in ["initiative", "team", "project", "workstream"])
                                or len(actual_headers[0]) < 25
                            )
                            else 0
                        )
                        for c_idx in range(data_cols_start, len(actual_headers)):
                            hdr_name = actual_headers[c_idx].strip()
                            if not hdr_name:
                                continue
                            pts = []
                            for row in data_rows:
                                if c_idx < len(row):
                                    cell_val = str(row[c_idx]).strip()
                                    if cell_val and cell_val.lower() not in ("no update this week", "none", "n/a"):
                                        prefix = ""
                                        if data_cols_start == 1 and len(row) > 0 and str(row[0]).strip():
                                            init_name = str(row[0]).strip().split("\n")[0]
                                            prefix = f"{init_name}: "
                                        clean_text = cell_val.replace("\n", " ")
                                        if len(clean_text) > 180:
                                            clean_text = clean_text[:177] + "..."
                                        pts.append(prefix + clean_text)
                            if pts:
                                columns_data.append({
                                    "title": hdr_name,
                                    "points": pts[:6],
                                })
                    break

        if table_dict and original_classification == "title_slide":
            original_classification = "table_view"

        # Discover templates and formats learned by AI from curated training slides
        suggested_templates, recommended_types = self._discover_learned_layouts(
            slide_info=slide_info,
            n_suggestions=n_suggestions,
        )

        if not recommended_types:
            recommended_types = [original_classification]

        primary_recommendation = recommended_types[0]

        if user_improvement_prompt and user_improvement_prompt.strip():
            suggested_prompt = f"{user_improvement_prompt.strip()}. Title: {title}. Points: {'; '.join(items[:5])}"
        else:
            items_summary = "; ".join(items[:5]) if items else "key points"
            suggested_prompt = (
                f"Redesign this slide into a modern {primary_recommendation.replace('_', ' ')} layout. "
                f"Title: {title}. Content: {items_summary}"
            )

        try:
            intent = self.prompt_parser.parse_prompt(suggested_prompt)
        except Exception:
            intent = GenerationIntent(
                slide_type=SlideType(primary_recommendation),
                content={
                    "title": title,
                    "subtitle": subtitle,
                    "items": items,
                },
                tone="professional",
            )

        if not user_improvement_prompt and recommended_types:
            try:
                intent.slide_type = SlideType(primary_recommendation)
            except ValueError:
                pass

        if not intent.content.get("title") and title:
            intent.content["title"] = title
        if items and not intent.content.get("items") and not intent.content.get("steps"):
            intent.content["items"] = items
        if columns_data:
            intent.content["columns"] = columns_data
        if table_dict:
            intent.content["table_data"] = table_dict

        return SlideAnalysisResult(
            original_classification=original_classification,
            extracted_title=title,
            extracted_subtitle=subtitle,
            extracted_items=items,
            suggested_prompt=suggested_prompt,
            recommended_slide_types=recommended_types,
            parsed_intent={
                "slide_type": intent.slide_type.value,
                "content": intent.content,
                "tone": intent.tone,
                "element_preferences": intent.element_preferences,
                "color_preference": intent.color_preference,
            },
            suggested_templates=suggested_templates,
        )

    def _discover_learned_layouts(
        self,
        slide_info: SlideInfo,
        n_suggestions: int = 5,
    ) -> tuple[List[Dict[str, Any]], List[str]]:
        """
        Query ChromaDB vector store of the 1,528 curated training slides
        to discover the best layout formats based entirely on AI training.
        """
        suggested_templates: List[Dict[str, Any]] = []
        recommended_types: List[str] = []

        try:
            query_embedding = None
            if hasattr(self.embedding_generator, "_extract_semantic_features"):
                features = self.embedding_generator._extract_semantic_features(slide_info)
                query_embedding = self.embedding_generator._features_to_embedding(features)
            elif hasattr(self.embedding_generator, "generate_semantic_embedding"):
                try:
                    query_embedding = self.embedding_generator.generate_semantic_embedding(slide_info, "query_tmp")
                except Exception:
                    pass

            if not query_embedding:
                features = [
                    float(slide_info.slide_index),
                    float(len(slide_info.shapes)),
                    float(len(slide_info.charts)),
                    float(len(slide_info.tables)),
                    float(slide_info.complexity_score or 5),
                    float(len(slide_info.text_content or "")),
                ]
                query_embedding = features + [0.0] * (384 - len(features))

            chroma_results = self.template_matcher.semantic_collection.query(
                query_embeddings=[query_embedding],
                n_results=n_suggestions * 2,
            )

            ids = chroma_results.get("ids", [[]])[0]
            distances = chroma_results.get("distances", [[]])[0] if "distances" in chroma_results else []

            for i, tid in enumerate(ids):
                template = self.database_manager.get_template_by_id(tid)
                if not template:
                    continue

                dist = distances[i] if i < len(distances) else 1.0
                similarity = max(0.01, min(0.99, 1.0 / (1.0 + float(dist) / 10000000.0)))
                cat = template.classification or "mixed"

                if cat not in recommended_types:
                    recommended_types.append(cat)

                suggested_templates.append({
                    "template_id": tid,
                    "template_data": template.to_dict(),
                    "similarity_score": round(similarity, 2),
                    "rank": len(suggested_templates) + 1,
                    "match_reason": f"Learned from curated training slide ({cat.replace('_', ' ')})",
                })

                if len(suggested_templates) >= n_suggestions:
                    break
        except Exception as err:
            logger.warning("AI template query failed (%s)", err)

        return suggested_templates, recommended_types

    def _extract_content_elements(self, slide_info: SlideInfo) -> tuple[str, Optional[str], List[str]]:
        """Extract title, subtitle, and body items from slide shapes."""
        extracted_title = ""
        extracted_subtitle = None
        extracted_items: List[str] = []

        all_paragraphs: List[str] = []
        for shape in slide_info.shapes:
            if shape.text_content and shape.text_content.paragraphs:
                for para in shape.text_content.paragraphs:
                    clean_para = para.strip()
                    if clean_para and clean_para not in all_paragraphs:
                        all_paragraphs.append(clean_para)

        if not all_paragraphs and slide_info.text_content:
            for line in slide_info.text_content.split("\n"):
                clean_line = line.strip()
                if clean_line:
                    all_paragraphs.append(clean_line)

        if all_paragraphs:
            extracted_title = all_paragraphs[0]
            remaining = all_paragraphs[1:]

            if remaining:
                first_rem = remaining[0]
                is_date_or_sub = bool(re.match(r"^(as of|by|date|q[1-4]|\d{1,2}/\d{1,2}/\d{2,4})\b", first_rem, re.IGNORECASE))
                first_is_step = bool(re.match(r"^(step|phase|part|item|\d+)\b", first_rem, re.IGNORECASE))

                if (is_date_or_sub or len(first_rem) < 60) and not first_is_step:
                    extracted_subtitle = first_rem
                    remaining = remaining[1:]

            for p in remaining:
                cleaned = re.sub(r"^[•\-\*\d\.\)\s]+", "", p).strip()
                if cleaned and len(cleaned) > 2 and cleaned not in extracted_items:
                    extracted_items.append(cleaned)

        if getattr(slide_info, "tables", None):
            for t in slide_info.tables:
                if t.data:
                    for row in t.data:
                        row_str = " | ".join(str(c) for c in row if c)
                        if row_str and row_str not in extracted_items and row_str != extracted_title and row_str != extracted_subtitle:
                            extracted_items.append(row_str)

        if not extracted_title:
            extracted_title = "Untitled Slide"

        return extracted_title, extracted_subtitle, extracted_items
