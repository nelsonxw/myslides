"""
Slide Classifier for MySlides.
Classifies slides into categories using heuristics and LLM semantic analysis.
"""
from enum import Enum
from typing import Optional

from myslides.ingestion.pptx_parser import SlideInfo, ChartType, SlideLayoutType
from myslides.llm.llm_client import LLMClient, LLMProvider


class SlideCategory(Enum):
    """Enumeration of slide categories for template matching."""
    TITLE_SLIDE = "title_slide"
    AGENDA = "agenda"
    SECTION_HEADER = "section_header"
    TEXT_HEAVY = "text_heavy"
    COMPARISON = "comparison"
    PROCESS_FLOW = "process_flow"
    TIMELINE = "timeline"
    ORG_CHART = "org_chart"
    DATA_CHART = "data_chart"
    MATRIX = "matrix"
    FUNNEL = "funnel"
    PYRAMID = "pyramid"
    DASHBOARD = "dashboard"
    IMAGE_SHOWCASE = "image_showcase"
    TABLE_VIEW = "table_view"
    MIXED = "mixed"


class SlideClassifier:
    """Classifier for categorizing slides based on their content and structure using Gemini Flash LLM."""

    def __init__(self):
        """Initialize the slide classifier with LLM client."""
        self._llm_client: Optional[LLMClient] = None

    def _get_llm_client(self) -> LLMClient:
        """Get LLM client, raising error if unavailable."""
        if self._llm_client is None:
            try:
                client = LLMClient()
                if client.provider != LLMProvider.GEMINI:
                    raise RuntimeError("Gemini API key not configured. Please set GEMINI_API_KEY in .env")
                self._llm_client = client
            except Exception as e:
                raise RuntimeError(f"Failed to initialize Gemini LLM client: {e}")
        return self._llm_client

    def classify(self, slide_info: SlideInfo) -> SlideCategory:
        """
        Classify a slide into a category using Gemini Flash LLM.

        Args:
            slide_info: SlideInfo object with parsed slide data

        Returns:
            SlideCategory enum value

        Raises:
            RuntimeError: If LLM is unavailable or classification fails
        """
        client = self._get_llm_client()
        category = self._classify_with_llm(slide_info, client)
        if category:
            return category
        raise RuntimeError("LLM classification failed to return a valid category")

    def _classify_with_llm(self, slide_info: SlideInfo, client: LLMClient) -> Optional[SlideCategory]:
        """
        Classify slide using Gemini Flash LLM for semantic understanding.

        Args:
            slide_info: SlideInfo object with parsed slide data
            client: LLMClient instance

        Returns:
            SlideCategory if classification succeeds, None otherwise
        """
        description = self._build_slide_description(slide_info)

        system_prompt = (
            "You are a slide layout classification expert. "
            "Classify the slide into one of these categories: "
            "title_slide, agenda, section_header, text_heavy, comparison, process_flow, "
            "timeline, org_chart, data_chart, matrix, funnel, pyramid, dashboard, "
            "image_showcase, table_view, mixed. "
            "Classification guidelines:\n"
            "- A slide with 3 or more charts is 'dashboard'.\n"
            "- A slide with 3 or more images and minimal text is 'image_showcase'.\n"
            "- A slide with extensive reading paragraphs or text length > 300 characters is 'text_heavy'.\n"
            "- A title_slide typically has a short presentation title and title layout.\n"
            "Respond with ONLY the category name, no explanation."
        )

        response = client.generate_completion(
            description,
            system_prompt=system_prompt,
            temperature=0.1,
            max_tokens=30
        )
        category_name = response.strip().lower()
        for category in SlideCategory:
            if category.value == category_name:
                return category
        return None

    def _build_slide_description(self, slide_info: SlideInfo) -> str:
        """Build a textual description of the slide for LLM classification."""
        parts = []
        if len(slide_info.text_content) > 300:
            parts.append(f"Content: {slide_info.text_content[:400]} (text length: {len(slide_info.text_content)} characters)")
        elif slide_info.text_content:
            parts.append(f"Content: {slide_info.text_content[:200]}")

        if slide_info.charts:
            parts.append(f"Charts: {len(slide_info.charts)}")
            for chart in slide_info.charts[:3]:
                parts.append(f"  - {chart.chart_type.value}")

        if slide_info.tables:
            parts.append(f"Tables: {len(slide_info.tables)}")

        if slide_info.images:
            parts.append(f"Images: {len(slide_info.images)}")

        parts.append(f"Shapes: {len(slide_info.shapes)}")
        parts.append(f"Layout: {slide_info.layout_type.value}")
        parts.append(f"Complexity: {slide_info.complexity_score}")

        return "\n".join(parts)

    def _is_process_flow_layout(self, slide_info: SlideInfo) -> bool:
        """
        Determine if the slide has a process flow layout based on shape arrangement.

        Args:
            slide_info: SlideInfo object

        Returns:
            True if appears to be a process flow layout
        """
        if len(slide_info.shapes) < 3:
            return False

        similar_shapes = []
        for shape in slide_info.shapes:
            if shape.shape_type not in ["group", "picture"]:
                similar_shapes.append(shape)

        if len(similar_shapes) < 3:
            return False

        y_positions = []
        for shape in similar_shapes:
            if hasattr(shape, 'position') and hasattr(shape.position, 'y') and isinstance(shape.position.y, (int, float)):
                y_positions.append(shape.position.y)

        if len(y_positions) < 3:
            return False

        y_variance = max(y_positions) - min(y_positions)

        # If y positions are similar (within 10% of slide height), likely horizontal arrangement
        if y_variance < slide_info.height * 0.1:
            return True

        return False

    def get_tags(self, slide_info: SlideInfo) -> list[str]:
        """
        Generate tags for a slide based on its content.

        Args:
            slide_info: SlideInfo object

        Returns:
            List of tag strings
        """
        tags = []
        category = self.classify(slide_info)
        tags.append(category.value)

        # Add chart type tags
        for chart in slide_info.charts:
            if chart.chart_type != ChartType.UNKNOWN:
                tags.append(f"chart_{chart.chart_type.value}")

        # Add layout tags
        tags.append(f"layout_{slide_info.layout_type.value}")

        # Add complexity tags
        if slide_info.complexity_score < 5:
            tags.append("simple")
        elif slide_info.complexity_score < 15:
            tags.append("moderate")
        else:
            tags.append("complex")

        # Add element count tags
        if len(slide_info.charts) > 0:
            tags.append("has_chart")
        if len(slide_info.tables) > 0:
            tags.append("has_table")
        if len(slide_info.images) > 0:
            tags.append("has_image")

        return tags
