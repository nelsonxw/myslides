"""
Unit tests for generation models.
"""
import pytest
from myslides.generation.generation_models import (
    SlideType, ChartSubType, TextContent, ChartData, 
    ProcessStep, TimelineEvent, GenerationIntent, GenerationConfig
)


class TestSlideType:
    """Test SlideType enum."""
    
    def test_slide_type_values(self):
        """Test that all expected slide types are defined."""
        assert SlideType.TITLE_SLIDE.value == "title_slide"
        assert SlideType.PROCESS_FLOW.value == "process_flow"
        assert SlideType.DATA_CHART.value == "data_chart"
        assert SlideType.TIMELINE.value == "timeline"


class TestChartSubType:
    """Test ChartSubType enum."""
    
    def test_chart_sub_type_values(self):
        """Test that all expected chart sub-types are defined."""
        assert ChartSubType.BAR_VERTICAL.value == "bar_vertical"
        assert ChartSubType.BAR_HORIZONTAL.value == "bar_horizontal"
        assert ChartSubType.LINE_SINGLE.value == "line_single"
        assert ChartSubType.PIE.value == "pie"


class TestTextContent:
    """Test TextContent dataclass."""
    
    def test_text_content_creation(self):
        """Test creating TextContent with all fields."""
        content = TextContent(
            title="Test Title",
            subtitle="Test Subtitle",
            body_text="Test body text",
            bullet_points=["Point 1", "Point 2"]
        )
        assert content.title == "Test Title"
        assert content.subtitle == "Test Subtitle"
        assert content.body_text == "Test body text"
        assert len(content.bullet_points) == 2
    
    def test_text_content_minimal(self):
        """Test creating TextContent with only required fields."""
        content = TextContent(title="Test Title")
        assert content.title == "Test Title"
        assert content.subtitle is None
        assert content.body_text is None
        assert content.bullet_points is None


class TestChartData:
    """Test ChartData dataclass."""
    
    def test_chart_data_creation(self):
        """Test creating ChartData with all fields."""
        data = ChartData(
            chart_type=ChartSubType.BAR_VERTICAL,
            title="Test Chart",
            categories=["Q1", "Q2", "Q3", "Q4"],
            series_data={"Series 1": [100, 150, 200, 180]},
            has_legend=True,
            show_data_labels=False
        )
        assert data.chart_type == ChartSubType.BAR_VERTICAL
        assert data.title == "Test Chart"
        assert len(data.categories) == 4
        assert "Series 1" in data.series_data
        assert data.has_legend is True
        assert data.show_data_labels is False


class TestProcessStep:
    """Test ProcessStep dataclass."""
    
    def test_process_step_creation(self):
        """Test creating ProcessStep with all fields."""
        step = ProcessStep(
            label="Step 1",
            description="First step",
            number=1
        )
        assert step.label == "Step 1"
        assert step.description == "First step"
        assert step.number == 1
    
    def test_process_step_minimal(self):
        """Test creating ProcessStep with only label."""
        step = ProcessStep(label="Step 1")
        assert step.label == "Step 1"
        assert step.description is None
        assert step.number is None


class TestTimelineEvent:
    """Test TimelineEvent dataclass."""
    
    def test_timeline_event_creation(self):
        """Test creating TimelineEvent with all fields."""
        event = TimelineEvent(
            date="2024-01-01",
            title="Milestone 1",
            description="First milestone"
        )
        assert event.date == "2024-01-01"
        assert event.title == "Milestone 1"
        assert event.description == "First milestone"


class TestGenerationIntent:
    """Test GenerationIntent dataclass and methods."""
    
    def test_intent_creation(self):
        """Test creating GenerationIntent."""
        intent = GenerationIntent(
            slide_type=SlideType.PROCESS_FLOW,
            content={"title": "Test Process"},
            tone="professional"
        )
        assert intent.slide_type == SlideType.PROCESS_FLOW
        assert intent.content["title"] == "Test Process"
        assert intent.tone == "professional"
    
    def test_get_text_content(self):
        """Test extracting text content from intent."""
        intent = GenerationIntent(
            slide_type=SlideType.TITLE_SLIDE,
            content={
                "title": "Test Title",
                "subtitle": "Test Subtitle",
                "bullet_points": ["Point 1", "Point 2"]
            }
        )
        text_content = intent.get_text_content()
        assert text_content is not None
        assert text_content.title == "Test Title"
        assert text_content.subtitle == "Test Subtitle"
        assert len(text_content.bullet_points) == 2
    
    def test_get_text_content_none(self):
        """Test extracting text content when not present."""
        intent = GenerationIntent(
            slide_type=SlideType.PROCESS_FLOW,
            content={"steps": ["Step 1", "Step 2"]}
        )
        text_content = intent.get_text_content()
        assert text_content is None
    
    def test_get_chart_data(self):
        """Test extracting chart data from intent."""
        intent = GenerationIntent(
            slide_type=SlideType.DATA_CHART,
            content={
                "chart_data": {
                    "chart_type": "bar_vertical",
                    "title": "Revenue Chart",
                    "categories": ["Q1", "Q2", "Q3"],
                    "series_data": {"Revenue": [100, 150, 200]}
                }
            }
        )
        chart_data = intent.get_chart_data()
        assert chart_data is not None
        assert chart_data.title == "Revenue Chart"
        assert len(chart_data.categories) == 3
    
    def test_get_chart_data_none(self):
        """Test extracting chart data when not present."""
        intent = GenerationIntent(
            slide_type=SlideType.PROCESS_FLOW,
            content={"steps": ["Step 1"]}
        )
        chart_data = intent.get_chart_data()
        assert chart_data is None
    
    def test_get_process_steps_strings(self):
        """Test extracting process steps from string list."""
        intent = GenerationIntent(
            slide_type=SlideType.PROCESS_FLOW,
            content={"steps": ["Step 1", "Step 2", "Step 3"]}
        )
        steps = intent.get_process_steps()
        assert len(steps) == 3
        assert steps[0].label == "Step 1"
        assert steps[0].number == 1
        assert steps[1].number == 2
    
    def test_get_process_steps_dicts(self):
        """Test extracting process steps from dict list."""
        intent = GenerationIntent(
            slide_type=SlideType.PROCESS_FLOW,
            content={
                "steps": [
                    {"label": "Step 1", "description": "First step"},
                    {"label": "Step 2", "description": "Second step"}
                ]
            }
        )
        steps = intent.get_process_steps()
        assert len(steps) == 2
        assert steps[0].label == "Step 1"
        assert steps[0].description == "First step"
    
    def test_get_process_steps_none(self):
        """Test extracting process steps when not present."""
        intent = GenerationIntent(
            slide_type=SlideType.TITLE_SLIDE,
            content={"title": "Test"}
        )
        steps = intent.get_process_steps()
        assert len(steps) == 0
    
    def test_get_timeline_events(self):
        """Test extracting timeline events from intent."""
        intent = GenerationIntent(
            slide_type=SlideType.TIMELINE,
            content={
                "events": [
                    {"date": "2024-01-01", "title": "Milestone 1"},
                    {"date": "2024-06-01", "title": "Milestone 2"}
                ]
            }
        )
        events = intent.get_timeline_events()
        assert len(events) == 2
        assert events[0].date == "2024-01-01"
        assert events[0].title == "Milestone 1"
    
    def test_get_timeline_events_none(self):
        """Test extracting timeline events when not present."""
        intent = GenerationIntent(
            slide_type=SlideType.PROCESS_FLOW,
            content={"steps": ["Step 1"]}
        )
        events = intent.get_timeline_events()
        assert len(events) == 0


class TestGenerationConfig:
    """Test GenerationConfig dataclass."""
    
    def test_config_defaults(self):
        """Test GenerationConfig with default values."""
        config = GenerationConfig()
        assert config.template_id is None
        assert config.template_element_manifest is None
        assert config.template_color_palette is None
        assert config.output_path == "generated_slide.pptx"
        assert config.adaptive_element_count is True
        assert config.preserve_styling is True
    
    def test_config_custom(self):
        """Test GenerationConfig with custom values."""
        config = GenerationConfig(
            template_id="template_123",
            template_color_palette=["#FF0000", "#00FF00", "#0000FF"],
            output_path="custom_output.pptx",
            adaptive_element_count=False
        )
        assert config.template_id == "template_123"
        assert len(config.template_color_palette) == 3
        assert config.output_path == "custom_output.pptx"
        assert config.adaptive_element_count is False
