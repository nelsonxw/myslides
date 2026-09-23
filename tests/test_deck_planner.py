"""
Unit tests for Deck Planner.
"""
import pytest
from unittest.mock import Mock, patch
from myslides.llm.deck_planner import DeckPlanner, DeckPlan
from myslides.llm.llm_client import LLMClient
from myslides.generation.generation_models import GenerationIntent, SlideType


class TestDeckPlan:
    """Test cases for DeckPlan dataclass."""
    
    def test_deck_plan_creation(self):
        """Test creating a deck plan."""
        plan = DeckPlan(
            title="Test Deck",
            description="A test deck",
            estimated_slide_count=3
        )
        assert plan.title == "Test Deck"
        assert plan.description == "A test deck"
        assert plan.estimated_slide_count == 3
        assert len(plan.slide_intents) == 0
    
    def test_deck_plan_to_dict(self):
        """Test converting deck plan to dictionary."""
        intent = GenerationIntent(
            slide_type=SlideType.TITLE_SLIDE,
            content={"title": "Test"}
        )
        plan = DeckPlan(
            title="Test Deck",
            description="A test deck",
            slide_intents=[intent],
            estimated_slide_count=1,
            suggested_flow=["Introduction"]
        )
        
        plan_dict = plan.to_dict()
        assert plan_dict["title"] == "Test Deck"
        assert len(plan_dict["slide_intents"]) == 1
        assert plan_dict["slide_intents"][0]["slide_type"] == "title_slide"


class TestDeckPlanner:
    """Test cases for DeckPlanner."""
    
    @patch("myslides.llm.deck_planner.LLMClient")
    def test_initialization(self, mock_llm_client_class):
        """Test planner initialization."""
        planner = DeckPlanner()
        assert planner.llm_client is not None
        assert planner.system_prompt is not None
    
    @patch("myslides.llm.deck_planner.LLMClient")
    def test_initialization_custom_client(self, mock_llm_client_class):
        """Test planner initialization with custom LLM client."""
        custom_client = Mock(spec=LLMClient)
        planner = DeckPlanner(llm_client=custom_client)
        assert planner.llm_client == custom_client
    
    @patch("myslides.llm.deck_planner.LLMClient")
    def test_plan_deck_pitch_deck(self, mock_llm_client_class):
        """Test planning a pitch deck."""
        mock_client = Mock()
        mock_client.generate_json_completion.return_value = {
            "title": "Fintech Startup Pitch Deck",
            "description": "A 10-slide pitch deck for a fintech startup",
            "slide_intents": [
                {
                    "slide_type": "title_slide",
                    "content": {"title": "Fintech Startup", "subtitle": "Revolutionizing Finance"},
                    "tone": "professional"
                },
                {
                    "slide_type": "content_slide",
                    "content": {
                        "title": "Problem",
                        "bullet_points": ["Problem 1", "Problem 2"]
                    },
                    "tone": "professional"
                },
                {
                    "slide_type": "content_slide",
                    "content": {
                        "title": "Solution",
                        "bullet_points": ["Solution 1", "Solution 2"]
                    },
                    "tone": "professional"
                }
            ],
            "suggested_flow": [
                "Title slide introducing the company",
                "Problem statement",
                "Solution overview"
            ]
        }
        mock_llm_client_class.return_value = mock_client
        
        planner = DeckPlanner(llm_client=mock_client)
        plan = planner.plan_deck("Create a 10-slide pitch deck for a fintech startup")
        
        assert plan.title == "Fintech Startup Pitch Deck"
        assert plan.estimated_slide_count == 3
        assert len(plan.slide_intents) == 3
        assert plan.slide_intents[0].slide_type == SlideType.TITLE_SLIDE
        assert plan.slide_intents[1].slide_type == SlideType.CONTENT_SLIDE
    
    @patch("myslides.llm.deck_planner.LLMClient")
    def test_plan_deck_product_demo(self, mock_llm_client_class):
        """Test planning a product demo deck."""
        mock_client = Mock()
        mock_client.generate_json_completion.return_value = {
            "title": "Product Demo",
            "description": "Product demonstration deck",
            "slide_intents": [
                {
                    "slide_type": "title_slide",
                    "content": {"title": "Product Demo"},
                    "tone": "professional"
                },
                {
                    "slide_type": "content_slide",
                    "content": {
                        "title": "Features",
                        "bullet_points": ["Feature 1", "Feature 2"]
                    },
                    "tone": "professional"
                }
            ],
            "suggested_flow": ["Introduction", "Features"]
        }
        mock_llm_client_class.return_value = mock_client
        
        planner = DeckPlanner(llm_client=mock_client)
        plan = planner.plan_deck("Create a product demo presentation")
        
        assert plan.title == "Product Demo"
        assert plan.estimated_slide_count == 2
    
    @patch("myslides.llm.deck_planner.LLMClient")
    def test_plan_deck_invalid_slide_type(self, mock_llm_client_class):
        """Test planning deck with invalid slide type defaults to content_slide."""
        mock_client = Mock()
        mock_client.generate_json_completion.return_value = {
            "title": "Test Deck",
            "description": "Test",
            "slide_intents": [
                {
                    "slide_type": "invalid_type",
                    "content": {"title": "Test"}
                }
            ],
            "suggested_flow": []
        }
        mock_llm_client_class.return_value = mock_client
        
        planner = DeckPlanner(llm_client=mock_client)
        plan = planner.plan_deck("Create a deck")
        
        assert plan.slide_intents[0].slide_type == SlideType.CONTENT_SLIDE
    
    @patch("myslides.llm.deck_planner.LLMClient")
    def test_refine_deck_plan(self, mock_llm_client_class):
        """Test refining an existing deck plan."""
        mock_client = Mock()
        # Initial plan
        initial_response = {
            "title": "Initial Deck",
            "description": "Initial",
            "slide_intents": [
                {
                    "slide_type": "title_slide",
                    "content": {"title": "Title"}
                }
            ],
            "suggested_flow": ["Title"]
        }
        # Refined plan
        refined_response = {
            "title": "Refined Deck",
            "description": "Refined",
            "slide_intents": [
                {
                    "slide_type": "title_slide",
                    "content": {"title": "Title"}
                },
                {
                    "slide_type": "content_slide",
                    "content": {
                        "title": "Competition",
                        "bullet_points": ["Competitor 1", "Competitor 2"]
                    }
                }
            ],
            "suggested_flow": ["Title", "Competition"]
        }
        mock_client.generate_json_completion.side_effect = [initial_response, refined_response]
        mock_llm_client_class.return_value = mock_client
        
        planner = DeckPlanner(llm_client=mock_client)
        initial_plan = planner.plan_deck("Create a pitch deck")
        refined_plan = planner.refine_deck_plan(initial_plan, "Add a slide about competitors")
        
        assert refined_plan.estimated_slide_count == 2
        assert refined_plan.slide_intents[1].slide_type == SlideType.CONTENT_SLIDE
        assert refined_plan.slide_intents[1].content["title"] == "Competition"
    
    @patch("myslides.llm.deck_planner.LLMClient")
    def test_plan_deck_with_various_slide_types(self, mock_llm_client_class):
        """Test planning deck with multiple slide types."""
        mock_client = Mock()
        mock_client.generate_json_completion.return_value = {
            "title": "Comprehensive Deck",
            "description": "Deck with various slide types",
            "slide_intents": [
                {
                    "slide_type": "title_slide",
                    "content": {"title": "Title"}
                },
                {
                    "slide_type": "process_flow",
                    "content": {
                        "title": "Process",
                        "steps": ["Step 1", "Step 2"]
                    }
                },
                {
                    "slide_type": "data_chart",
                    "content": {
                        "title": "Chart",
                        "chart_data": {
                            "chart_type": "bar_vertical",
                            "categories": ["A", "B"],
                            "series_data": {"Series": [1, 2]}
                        }
                    }
                },
                {
                    "slide_type": "timeline",
                    "content": {
                        "title": "Timeline",
                        "events": [{"date": "2020", "title": "Event"}]
                    }
                }
            ],
            "suggested_flow": ["Title", "Process", "Chart", "Timeline"]
        }
        mock_llm_client_class.return_value = mock_client
        
        planner = DeckPlanner(llm_client=mock_client)
        plan = planner.plan_deck("Create a comprehensive presentation")
        
        assert plan.estimated_slide_count == 4
        assert plan.slide_intents[0].slide_type == SlideType.TITLE_SLIDE
        assert plan.slide_intents[1].slide_type == SlideType.PROCESS_FLOW
        assert plan.slide_intents[2].slide_type == SlideType.DATA_CHART
        assert plan.slide_intents[3].slide_type == SlideType.TIMELINE
    
    @patch("myslides.llm.deck_planner.LLMClient")
    def test_format_current_slides(self, mock_llm_client_class):
        """Test formatting current slides for display."""
        mock_client = Mock()
        mock_llm_client_class.return_value = mock_client
        
        planner = DeckPlanner(llm_client=mock_client)
        plan = DeckPlan(
            title="Test",
            description="Test",
            slide_intents=[
                GenerationIntent(slide_type=SlideType.TITLE_SLIDE, content={"title": "Slide 1"}),
                GenerationIntent(slide_type=SlideType.CONTENT_SLIDE, content={"title": "Slide 2"})
            ],
            estimated_slide_count=2
        )
        
        formatted = planner._format_current_slides(plan)
        lines = formatted.split("\n")
        assert "1. title_slide: Slide 1" in lines
        assert "2. content_slide: Slide 2" in lines
