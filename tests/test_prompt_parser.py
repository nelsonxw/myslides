"""
Unit tests for Prompt Parser.
"""
import pytest
from unittest.mock import Mock, patch
from myslides.llm.prompt_parser import PromptParser
from myslides.llm.llm_client import LLMClient
from myslides.generation.generation_models import GenerationIntent, SlideType, ChartSubType


class TestPromptParser:
    """Test cases for PromptParser."""
    
    @patch("myslides.llm.prompt_parser.LLMClient")
    def test_initialization(self, mock_llm_client):
        """Test parser initialization."""
        parser = PromptParser()
        assert parser.llm_client is not None
        assert parser.system_prompt is not None
    
    @patch("myslides.llm.prompt_parser.LLMClient")
    def test_initialization_custom_client(self, mock_llm_client):
        """Test parser initialization with custom LLM client."""
        custom_client = Mock(spec=LLMClient)
        parser = PromptParser(llm_client=custom_client)
        assert parser.llm_client == custom_client
    
    @patch("myslides.llm.prompt_parser.LLMClient")
    def test_parse_prompt_process_flow(self, mock_llm_client_class):
        """Test parsing a process flow prompt."""
        mock_client = Mock()
        mock_client.generate_json_completion.return_value = {
            "slide_type": "process_flow",
            "content": {
                "title": "5-Step Onboarding Process",
                "steps": ["Application", "Screening", "Interview", "Offer", "Orientation"]
            },
            "tone": "professional"
        }
        mock_llm_client_class.return_value = mock_client
        
        parser = PromptParser(llm_client=mock_client)
        intent = parser.parse_prompt("Create a slide showing our 5-step onboarding process")
        
        assert intent.slide_type == SlideType.PROCESS_FLOW
        assert intent.content["title"] == "5-Step Onboarding Process"
        assert len(intent.content["steps"]) == 5
        assert intent.tone == "professional"
    
    @patch("myslides.llm.prompt_parser.LLMClient")
    def test_parse_prompt_comparison(self, mock_llm_client_class):
        """Test parsing a comparison slide prompt."""
        mock_client = Mock()
        mock_client.generate_json_completion.return_value = {
            "slide_type": "comparison",
            "content": {
                "title": "Plan A vs Plan B Pricing",
                "subtitle": "Feature comparison"
            },
            "tone": "professional"
        }
        mock_llm_client_class.return_value = mock_client
        
        parser = PromptParser(llm_client=mock_client)
        intent = parser.parse_prompt("Build a comparison slide for Plan A vs Plan B pricing")
        
        assert intent.slide_type == SlideType.COMPARISON
        assert intent.content["title"] == "Plan A vs Plan B Pricing"
    
    @patch("myslides.llm.prompt_parser.LLMClient")
    def test_parse_prompt_chart(self, mock_llm_client_class):
        """Test parsing a chart slide prompt."""
        mock_client = Mock()
        mock_client.generate_json_completion.return_value = {
            "slide_type": "data_chart",
            "content": {
                "title": "Quarterly Revenue",
                "chart_data": {
                    "chart_type": "bar_vertical",
                    "title": "Revenue in Millions",
                    "categories": ["Q1", "Q2", "Q3", "Q4"],
                    "series_data": {"Revenue": [100, 150, 200, 180]},
                    "has_legend": True,
                    "show_data_labels": False
                }
            },
            "tone": "professional"
        }
        mock_llm_client_class.return_value = mock_client
        
        parser = PromptParser(llm_client=mock_client)
        intent = parser.parse_prompt("Show quarterly revenue as a bar chart")
        
        assert intent.slide_type == SlideType.DATA_CHART
        assert intent.content["chart_data"]["chart_type"] == ChartSubType.BAR_VERTICAL
    
    @patch("myslides.llm.prompt_parser.LLMClient")
    def test_parse_prompt_timeline(self, mock_llm_client_class):
        """Test parsing a timeline prompt."""
        mock_client = Mock()
        mock_client.generate_json_completion.return_value = {
            "slide_type": "timeline",
            "content": {
                "title": "Product Milestones",
                "events": [
                    {"date": "2020", "title": "Launch", "description": "Initial release"},
                    {"date": "2022", "title": "Expansion", "description": "New markets"}
                ]
            },
            "tone": "professional"
        }
        mock_llm_client_class.return_value = mock_client
        
        parser = PromptParser(llm_client=mock_client)
        intent = parser.parse_prompt("Make a timeline of our product milestones from 2020 to 2025")
        
        assert intent.slide_type == SlideType.TIMELINE
        assert len(intent.content["events"]) == 2
    
    @patch("myslides.llm.prompt_parser.LLMClient")
    def test_parse_prompt_invalid_slide_type(self, mock_llm_client_class):
        """Test parsing with invalid slide type defaults to content_slide."""
        mock_client = Mock()
        mock_client.generate_json_completion.return_value = {
            "slide_type": "invalid_type",
            "content": {"title": "Test"}
        }
        mock_llm_client_class.return_value = mock_client
        
        parser = PromptParser(llm_client=mock_client)
        intent = parser.parse_prompt("Create a slide")
        
        assert intent.slide_type == SlideType.CONTENT_SLIDE
    
    @patch("myslides.llm.prompt_parser.LLMClient")
    def test_parse_prompt_invalid_chart_type(self, mock_llm_client_class):
        """Test parsing with invalid chart type defaults to bar_vertical."""
        mock_client = Mock()
        mock_client.generate_json_completion.return_value = {
            "slide_type": "data_chart",
            "content": {
                "title": "Test",
                "chart_data": {
                    "chart_type": "invalid_chart",
                    "categories": ["A", "B"],
                    "series_data": {"Series": [1, 2]}
                }
            }
        }
        mock_llm_client_class.return_value = mock_client
        
        parser = PromptParser(llm_client=mock_client)
        intent = parser.parse_prompt("Create a chart")
        
        assert intent.content["chart_data"]["chart_type"] == ChartSubType.BAR_VERTICAL
    
    @patch("myslides.llm.prompt_parser.LLMClient")
    def test_parse_with_context_previous_intent(self, mock_llm_client_class):
        """Test parsing with previous intent context."""
        mock_client = Mock()
        mock_client.generate_json_completion.return_value = {
            "slide_type": "data_chart",
            "content": {
                "title": "Quarterly Revenue",
                "chart_data": {
                    "chart_type": "pie",
                    "categories": ["Q1", "Q2", "Q3", "Q4"],
                    "series_data": {"Revenue": [100, 150, 200, 180]}
                }
            },
            "tone": "professional"
        }
        mock_llm_client_class.return_value = mock_client
        
        parser = PromptParser(llm_client=mock_client)
        previous_intent = GenerationIntent(
            slide_type=SlideType.DATA_CHART,
            content={"title": "Revenue Chart"}
        )
        
        intent = parser.parse_with_context(
            "Change the chart to a pie chart instead",
            previous_intent=previous_intent
        )
        
        assert intent.slide_type == SlideType.DATA_CHART
        assert intent.content["chart_data"]["chart_type"] == ChartSubType.PIE
    
    @patch("myslides.llm.prompt_parser.LLMClient")
    def test_parse_with_context_conversation_history(self, mock_llm_client_class):
        """Test parsing with conversation history context."""
        mock_client = Mock()
        mock_client.generate_json_completion.return_value = {
            "slide_type": "process_flow",
            "content": {
                "title": "Onboarding Process",
                "steps": ["Step 1", "Step 2", "Step 3"]
            }
        }
        mock_llm_client_class.return_value = mock_client
        
        parser = PromptParser(llm_client=mock_client)
        history = [
            {"user": "Create a process flow", "assistant": "I'll create a process flow"}
        ]
        
        intent = parser.parse_with_context(
            "Add a third step",
            conversation_history=history
        )
        
        assert intent.slide_type == SlideType.PROCESS_FLOW
        assert len(intent.content["steps"]) == 3
    
    @patch("myslides.llm.prompt_parser.LLMClient")
    def test_parse_with_context_no_context(self, mock_llm_client_class):
        """Test parsing with no context falls back to standard parsing."""
        mock_client = Mock()
        mock_client.generate_json_completion.return_value = {
            "slide_type": "title_slide",
            "content": {"title": "Test"}
        }
        mock_llm_client_class.return_value = mock_client
        
        parser = PromptParser(llm_client=mock_client)
        intent = parser.parse_with_context("Create a title slide")
        
        assert intent.slide_type == SlideType.TITLE_SLIDE
        assert mock_client.generate_json_completion.call_count == 1
    
    @patch("myslides.llm.prompt_parser.LLMClient")
    def test_get_text_content(self, mock_llm_client_class):
        """Test extracting text content from intent."""
        mock_client = Mock()
        mock_client.generate_json_completion.return_value = {
            "slide_type": "content_slide",
            "content": {
                "title": "Test Title",
                "subtitle": "Test Subtitle",
                "bullet_points": ["Point 1", "Point 2"]
            }
        }
        mock_llm_client_class.return_value = mock_client
        
        parser = PromptParser(llm_client=mock_client)
        intent = parser.parse_prompt("Create a content slide")
        
        text_content = intent.get_text_content()
        assert text_content is not None
        assert text_content.title == "Test Title"
        assert text_content.subtitle == "Test Subtitle"
        assert len(text_content.bullet_points) == 2
    
    @patch("myslides.llm.prompt_parser.LLMClient")
    def test_get_chart_data(self, mock_llm_client_class):
        """Test extracting chart data from intent."""
        mock_client = Mock()
        mock_client.generate_json_completion.return_value = {
            "slide_type": "data_chart",
            "content": {
                "title": "Revenue",
                "chart_data": {
                    "chart_type": "line_multi",
                    "categories": ["Q1", "Q2"],
                    "series_data": {"Series A": [100, 150]}
                }
            }
        }
        mock_llm_client_class.return_value = mock_client
        
        parser = PromptParser(llm_client=mock_client)
        intent = parser.parse_prompt("Create a line chart")
        
        chart_data = intent.get_chart_data()
        assert chart_data is not None
        assert chart_data.chart_type == ChartSubType.LINE_MULTI
    
    @patch("myslides.llm.prompt_parser.LLMClient")
    def test_get_process_steps(self, mock_llm_client_class):
        """Test extracting process steps from intent."""
        mock_client = Mock()
        mock_client.generate_json_completion.return_value = {
            "slide_type": "process_flow",
            "content": {
                "title": "Process",
                "steps": ["Step 1", "Step 2", "Step 3"]
            }
        }
        mock_llm_client_class.return_value = mock_client
        
        parser = PromptParser(llm_client=mock_client)
        intent = parser.parse_prompt("Create a process flow")
        
        steps = intent.get_process_steps()
        assert len(steps) == 3
        assert steps[0].label == "Step 1"
        assert steps[0].number == 1
    
    @patch("myslides.llm.prompt_parser.LLMClient")
    def test_get_process_steps_dict_format(self, mock_llm_client_class):
        """Test extracting process steps in dict format."""
        mock_client = Mock()
        mock_client.generate_json_completion.return_value = {
            "slide_type": "process_flow",
            "content": {
                "title": "Process",
                "steps": [
                    {"label": "Step 1", "description": "First step", "number": 1},
                    {"label": "Step 2", "description": "Second step", "number": 2}
                ]
            }
        }
        mock_llm_client_class.return_value = mock_client
        
        parser = PromptParser(llm_client=mock_client)
        intent = parser.parse_prompt("Create a process flow")
        
        steps = intent.get_process_steps()
        assert len(steps) == 2
        assert steps[0].label == "Step 1"
        assert steps[0].description == "First step"
        assert steps[0].number == 1
    
    @patch("myslides.llm.prompt_parser.LLMClient")
    def test_get_timeline_events(self, mock_llm_client_class):
        """Test extracting timeline events from intent."""
        mock_client = Mock()
        mock_client.generate_json_completion.return_value = {
            "slide_type": "timeline",
            "content": {
                "title": "Timeline",
                "events": [
                    {"date": "2020", "title": "Event 1"},
                    {"date": "2021", "title": "Event 2"}
                ]
            }
        }
        mock_llm_client_class.return_value = mock_client
        
        parser = PromptParser(llm_client=mock_client)
        intent = parser.parse_prompt("Create a timeline")
        
        events = intent.get_timeline_events()
        assert len(events) == 2
        assert events[0].date == "2020"
        assert events[0].title == "Event 1"

    def test_normalize_slide_type_aliases(self):
        """Test slide type normalization with various aliases."""
        assert PromptParser.normalize_slide_type("process") == SlideType.PROCESS_FLOW
        assert PromptParser.normalize_slide_type("chart") == SlideType.DATA_CHART
        assert PromptParser.normalize_slide_type("title") == SlideType.TITLE_SLIDE
        assert PromptParser.normalize_slide_type("milestones") == SlideType.TIMELINE
        assert PromptParser.normalize_slide_type("compare") == SlideType.COMPARISON
        assert PromptParser.normalize_slide_type("unknown_type") == SlideType.CONTENT_SLIDE
        assert PromptParser.normalize_slide_type("") == SlideType.CONTENT_SLIDE

    def test_normalize_chart_subtype_aliases(self):
        """Test chart subtype normalization with various aliases."""
        assert PromptParser.normalize_chart_subtype("bar") == ChartSubType.BAR_VERTICAL
        assert PromptParser.normalize_chart_subtype("line") == ChartSubType.LINE_SINGLE
        assert PromptParser.normalize_chart_subtype("pie_chart") == ChartSubType.PIE
        assert PromptParser.normalize_chart_subtype("donut_chart") == ChartSubType.DONUT
        assert PromptParser.normalize_chart_subtype("unknown") == ChartSubType.BAR_VERTICAL
        assert PromptParser.normalize_chart_subtype("") == ChartSubType.BAR_VERTICAL
