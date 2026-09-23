"""
Data models for slide generation.
Defines the structured intent format and generation configuration.
"""
from dataclasses import dataclass, field
from typing import Any, Optional, List, Dict
from enum import Enum


class SlideType(Enum):
    """Enumeration of slide types for generation."""
    TITLE_SLIDE = "title_slide"
    CONTENT_SLIDE = "content_slide"
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


class ChartSubType(Enum):
    """Enumeration of chart sub-types."""
    BAR_VERTICAL = "bar_vertical"
    BAR_HORIZONTAL = "bar_horizontal"
    BAR_STACKED = "bar_stacked"
    BAR_GROUPED = "bar_grouped"
    LINE_SINGLE = "line_single"
    LINE_MULTI = "line_multi"
    PIE = "pie"
    DONUT = "donut"
    AREA = "area"
    AREA_STACKED = "area_stacked"
    SCATTER = "scatter"
    COMBO = "combo"
    WATERFALL = "waterfall"


@dataclass
class TextContent:
    """Text content for a slide."""
    title: str
    subtitle: Optional[str] = None
    body_text: Optional[str] = None
    bullet_points: Optional[List[str]] = None


@dataclass
class ChartData:
    """Data for chart generation."""
    chart_type: ChartSubType
    title: str
    categories: List[str]
    series_data: Dict[str, List[float]]  # Series name -> values
    has_legend: bool = True
    show_data_labels: bool = False


@dataclass
class ProcessStep:
    """A single step in a process flow."""
    label: str
    description: Optional[str] = None
    number: Optional[int] = None


@dataclass
class TimelineEvent:
    """A single event in a timeline."""
    date: str
    title: str
    description: Optional[str] = None


@dataclass
class GenerationIntent:
    """Structured intent extracted from user prompt."""
    slide_type: SlideType
    content: Dict[str, Any] = field(default_factory=dict)
    data_type: Optional[str] = None
    element_preferences: List[str] = field(default_factory=list)
    color_preference: Optional[str] = None
    tone: str = "professional"
    
    def get_text_content(self) -> Optional[TextContent]:
        """Extract text content if present."""
        if "title" in self.content:
            return TextContent(
                title=self.content.get("title", ""),
                subtitle=self.content.get("subtitle"),
                body_text=self.content.get("body_text"),
                bullet_points=self.content.get("bullet_points")
            )
        return None
    
    def get_chart_data(self) -> Optional[ChartData]:
        """Extract chart data if present."""
        if "chart_data" in self.content:
            chart_dict = self.content["chart_data"]
            return ChartData(
                chart_type=ChartSubType(chart_dict.get("chart_type", "bar_vertical")),
                title=chart_dict.get("title", ""),
                categories=chart_dict.get("categories", []),
                series_data=chart_dict.get("series_data", {}),
                has_legend=chart_dict.get("has_legend", True),
                show_data_labels=chart_dict.get("show_data_labels", False)
            )
        return None
    
    def get_process_steps(self) -> List[ProcessStep]:
        """Extract process steps if present."""
        if "steps" in self.content:
            steps = []
            for i, step in enumerate(self.content["steps"], 1):
                if isinstance(step, str):
                    steps.append(ProcessStep(label=step, number=i))
                elif isinstance(step, dict):
                    steps.append(ProcessStep(
                        label=step.get("label", ""),
                        description=step.get("description"),
                        number=step.get("number", i)
                    ))
            return steps
        return []
    
    def get_timeline_events(self) -> List[TimelineEvent]:
        """Extract timeline events if present."""
        if "events" in self.content:
            events = []
            for event in self.content["events"]:
                if isinstance(event, dict):
                    events.append(TimelineEvent(
                        date=event.get("date", ""),
                        title=event.get("title", ""),
                        description=event.get("description")
                    ))
            return events
        return []


@dataclass
class GenerationConfig:
    """Configuration for slide generation."""
    template_id: Optional[str] = None
    template_element_manifest: Optional[Dict[str, Any]] = None
    template_color_palette: Optional[List[str]] = None
    output_path: str = "generated_slide.pptx"
    adaptive_element_count: bool = True
    preserve_styling: bool = True
