"""
Slide Classifier for MySlides.
Classifies slides into categories using heuristics and pattern matching.
"""
from enum import Enum
from typing import Optional

from myslides.ingestion.pptx_parser import SlideInfo, ChartType, SlideLayoutType


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
    """Classifier for categorizing slides based on their content and structure."""
    
    def classify(self, slide_info: SlideInfo) -> SlideCategory:
        """
        Classify a slide into a category using heuristics.
        
        Args:
            slide_info: SlideInfo object with parsed slide data
        
        Returns:
            SlideCategory enum value
        """
        # Priority-based classification
        category = self._classify_by_charts(slide_info)
        if category != SlideCategory.MIXED:
            return category
        
        category = self._classify_by_tables(slide_info)
        if category != SlideCategory.MIXED:
            return category
        
        category = self._classify_by_images(slide_info)
        if category != SlideCategory.MIXED:
            return category
        
        category = self._classify_by_text_content(slide_info)
        if category != SlideCategory.MIXED:
            return category
        
        category = self._classify_by_layout(slide_info)
        if category != SlideCategory.MIXED:
            return category
        
        return SlideCategory.MIXED
    
    def _classify_by_charts(self, slide_info: SlideInfo) -> SlideCategory:
        """Classify based on chart presence and type."""
        if not slide_info.charts:
            return SlideCategory.MIXED
        
        chart_count = len(slide_info.charts)
        
        if chart_count >= 3:
            return SlideCategory.DASHBOARD
        
        if chart_count == 1:
            chart = slide_info.charts[0]
            if chart.chart_type == ChartType.PIE:
                return SlideCategory.DATA_CHART
            elif chart.chart_type == ChartType.FUNNEL:
                return SlideCategory.FUNNEL
            else:
                return SlideCategory.DATA_CHART
        
        return SlideCategory.MIXED
    
    def _classify_by_tables(self, slide_info: SlideInfo) -> SlideCategory:
        """Classify based on table presence."""
        if not slide_info.tables:
            return SlideCategory.MIXED
        
        table_count = len(slide_info.tables)
        
        if table_count == 1 and slide_info.tables[0].rows * slide_info.tables[0].columns > 6:
            return SlideCategory.TABLE_VIEW
        
        if table_count >= 2:
            return SlideCategory.COMPARISON
        
        return SlideCategory.MIXED
    
    def _classify_by_images(self, slide_info: SlideInfo) -> SlideCategory:
        """Classify based on image presence."""
        if not slide_info.images:
            return SlideCategory.MIXED
        
        image_count = len(slide_info.images)
        
        if image_count >= 3:
            return SlideCategory.IMAGE_SHOWCASE
        
        if image_count == 1 and len(slide_info.shapes) <= 2:
            return SlideCategory.IMAGE_SHOWCASE
        
        return SlideCategory.MIXED
    
    def _classify_by_text_content(self, slide_info: SlideInfo) -> SlideCategory:
        """Classify based on text content patterns."""
        text = slide_info.text_content.lower()
        
        # Check for agenda patterns
        agenda_keywords = ["agenda", "schedule", "overview", "table of contents", "topics"]
        if any(keyword in text for keyword in agenda_keywords):
            return SlideCategory.AGENDA
        
        # Check for process flow patterns
        process_keywords = ["step", "phase", "stage", "process", "workflow", "flow"]
        if any(keyword in text for keyword in process_keywords):
            return SlideCategory.PROCESS_FLOW
        
        # Check for timeline patterns
        timeline_keywords = ["timeline", "roadmap", "milestone", "q1", "q2", "q3", "q4", "2020", "2021", "2022", "2023", "2024", "2025"]
        if any(keyword in text for keyword in timeline_keywords):
            return SlideCategory.TIMELINE
        
        # Check for comparison patterns
        comparison_keywords = ["vs", "versus", "compare", "comparison", "difference", "pros and cons"]
        if any(keyword in text for keyword in comparison_keywords):
            return SlideCategory.COMPARISON
        
        # Check for org chart patterns
        org_keywords = ["organization", "hierarchy", "reporting", "structure", "team", "department"]
        if any(keyword in text for keyword in org_keywords):
            return SlideCategory.ORG_CHART
        
        # Check for matrix patterns
        matrix_keywords = ["matrix", "quadrant", "grid", "2x2", "four quadrant"]
        if any(keyword in text for keyword in matrix_keywords):
            return SlideCategory.MATRIX
        
        # Check for pyramid patterns
        pyramid_keywords = ["pyramid", "hierarchy of needs", "levels", "tiers"]
        if any(keyword in text for keyword in pyramid_keywords):
            return SlideCategory.PYRAMID
        
        # Check for text-heavy slides
        text_length = len(text)
        if text_length > 500:
            return SlideCategory.TEXT_HEAVY
        
        return SlideCategory.MIXED
    
    def _classify_by_layout(self, slide_info: SlideInfo) -> SlideCategory:
        """Classify based on layout type and shape structure."""
        layout = slide_info.layout_type
        
        if layout == SlideLayoutType.TITLE_SLIDE:
            return SlideCategory.TITLE_SLIDE
        
        if layout == SlideLayoutType.SECTION_HEADER:
            return SlideCategory.SECTION_HEADER
        
        if layout == SlideLayoutType.TITLE_ONLY:
            return SlideCategory.TITLE_SLIDE
        
        if layout == SlideLayoutType.BLANK:
            return SlideCategory.MIXED
        
        # Check for comparison layout (two content areas)
        if layout == SlideLayoutType.TWO_CONTENT:
            return SlideCategory.COMPARISON
        
        # Check for process flow based on shape arrangement
        if self._is_process_flow_layout(slide_info):
            return SlideCategory.PROCESS_FLOW
        
        return SlideCategory.MIXED
    
    def _is_process_flow_layout(self, slide_info: SlideInfo) -> bool:
        """
        Determine if the slide has a process flow layout based on shape arrangement.
        
        Args:
            slide_info: SlideInfo object
        
        Returns:
            True if appears to be a process flow layout
        """
        # Simple heuristic: check for multiple similar shapes arranged horizontally
        if len(slide_info.shapes) < 3:
            return False
        
        # Look for shapes with similar heights and widths arranged horizontally
        similar_shapes = []
        for shape in slide_info.shapes:
            if shape.shape_type not in ["group", "picture"]:
                similar_shapes.append(shape)
        
        if len(similar_shapes) < 3:
            return False
        
        # Check if shapes are arranged in a horizontal line
        y_positions = [shape.position.y for shape in similar_shapes]
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
