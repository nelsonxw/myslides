"""
Integration tests between Module 2 (Prompt Interpretation Engine)
and Module 4 (Slide Generation Engine).

Verifies the end-to-end pipeline:
Natural language prompt -> PromptParser/DeckPlanner -> GenerationIntent -> SlideGenerator -> PPTXExporter
"""
import os
import pytest
from unittest.mock import Mock, patch

from myslides.llm.prompt_parser import PromptParser
from myslides.llm.deck_planner import DeckPlanner, DeckPlan
from myslides.llm.conversation_manager import ConversationManager
from myslides.llm.llm_client import LLMClient
from myslides.generation.slide_generator import SlideGenerator
from myslides.generation.generation_models import SlideType, ChartSubType, GenerationIntent
from myslides.generation.pptx_exporter import PPTXExporter


class TestIntegrationModule2Module4:
    """End-to-end integration tests between LLM interpretation and slide generation."""
    
    def test_prompt_to_process_flow_slide(self):
        """Test pipeline from process flow prompt to generated PPTX slide."""
        mock_llm = Mock(spec=LLMClient)
        mock_llm.generate_json_completion.return_value = {
            "slide_type": "process_flow",
            "content": {
                "title": "Continuous Delivery Pipeline",
                "subtitle": "From commit to production deployment",
                "steps": [
                    {"label": "Build", "description": "Compile and lint code", "number": 1},
                    {"label": "Test", "description": "Run unit & integration tests", "number": 2},
                    {"label": "Stage", "description": "Deploy to staging environment", "number": 3},
                    {"label": "Deploy", "description": "Canary rollout to production", "number": 4}
                ]
            },
            "tone": "professional"
        }
        
        # 1. Module 2: Parse natural language prompt into GenerationIntent
        parser = PromptParser(llm_client=mock_llm)
        intent = parser.parse_prompt("Create a 4-step continuous delivery pipeline slide")
        
        assert intent.slide_type == SlideType.PROCESS_FLOW
        assert len(intent.get_process_steps()) == 4
        
        # 2. Module 4: Generate slide from intent
        generator = SlideGenerator()
        presentation = generator.generate_slide(intent)
        
        assert len(presentation.slides) == 1
        slide = presentation.slides[0]
        # Should contain title, subtitle, 4 step shapes, and 3 connectors
        assert len(slide.shapes) >= 6
        
        # 3. Export & validate presentation
        exporter = PPTXExporter(presentation)
        assert exporter.validate() is True
        
        temp_path = exporter.save_to_temp("test_pipeline_flow.pptx")
        assert os.path.exists(temp_path)
        assert os.path.getsize(temp_path) > 0
        os.remove(temp_path)

    def test_prompt_to_chart_slide(self):
        """Test pipeline from chart prompt to generated PPTX slide."""
        mock_llm = Mock(spec=LLMClient)
        mock_llm.generate_json_completion.return_value = {
            "slide_type": "data_chart",
            "content": {
                "title": "Quarterly Sales Performance",
                "subtitle": "Regional comparison (in Thousands)",
                "chart_data": {
                    "chart_type": "bar_vertical",
                    "title": "Sales by Region",
                    "categories": ["Q1", "Q2", "Q3", "Q4"],
                    "series_data": {
                        "North America": [150.0, 180.0, 210.0, 240.0],
                        "Europe": [120.0, 140.0, 160.0, 190.0]
                    },
                    "has_legend": True,
                    "show_data_labels": True
                }
            },
            "tone": "professional"
        }
        
        # 1. Module 2: Parse prompt
        parser = PromptParser(llm_client=mock_llm)
        intent = parser.parse_prompt("Show quarterly sales for North America and Europe as a vertical bar chart")
        
        assert intent.slide_type == SlideType.DATA_CHART
        chart_data = intent.get_chart_data()
        assert chart_data is not None
        assert chart_data.chart_type == ChartSubType.BAR_VERTICAL
        assert len(chart_data.categories) == 4
        
        # 2. Module 4: Generate slide
        generator = SlideGenerator()
        presentation = generator.generate_slide(intent)
        
        assert len(presentation.slides) == 1
        slide = presentation.slides[0]
        # Verify native chart shape exists
        chart_shapes = [s for s in slide.shapes if s.has_chart]
        assert len(chart_shapes) == 1
        
        # 3. Validate
        exporter = PPTXExporter(presentation)
        assert exporter.validate() is True

    def test_deck_planner_to_multi_slide_deck(self):
        """Test pipeline from deck plan prompt to generated multi-slide PPTX deck."""
        mock_llm = Mock(spec=LLMClient)
        mock_llm.generate_json_completion.return_value = {
            "title": "AI Platform Pitch Deck",
            "description": "Investor presentation for seed funding",
            "slide_intents": [
                {
                    "slide_type": "title_slide",
                    "content": {
                        "title": "NextGen AI Platform",
                        "subtitle": "Transforming Enterprise Presentation Workflows"
                    }
                },
                {
                    "slide_type": "process_flow",
                    "content": {
                        "title": "How It Works",
                        "steps": ["Upload Template", "Catalog Elements", "Prompt LLM", "Export Deck"]
                    }
                },
                {
                    "slide_type": "data_chart",
                    "content": {
                        "title": "Market Growth",
                        "chart_data": {
                            "chart_type": "line_single",
                            "title": "Total Addressable Market ($B)",
                            "categories": ["2022", "2023", "2024", "2025"],
                            "series_data": {"TAM": [5.2, 8.4, 14.1, 22.5]}
                        }
                    }
                },
                {
                    "slide_type": "text_heavy",
                    "content": {
                        "title": "Key Advantages",
                        "bullet_points": [
                            "Proprietary slide layout extraction algorithms",
                            "Seamless python-pptx native shape and chart generation",
                            "End-to-end vector search and retrieval matching"
                        ]
                    }
                }
            ],
            "suggested_flow": ["Introduction", "Workflow Architecture", "Market Size", "Competitive Edge"]
        }
        
        # 1. Module 2: Plan deck
        planner = DeckPlanner(llm_client=mock_llm)
        plan = planner.plan_deck("Create a 4-slide pitch deck for our AI platform")
        
        assert plan.title == "AI Platform Pitch Deck"
        assert plan.estimated_slide_count == 4
        assert len(plan.slide_intents) == 4
        
        # 2. Module 4: Generate multi-slide deck
        generator = SlideGenerator()
        presentation = generator.generate_deck(plan.slide_intents)
        
        assert len(presentation.slides) == 4
        
        # 3. Export & validate multi-slide presentation
        exporter = PPTXExporter(presentation)
        assert exporter.validate() is True
        
        temp_path = exporter.save_to_temp("ai_platform_pitch.pptx")
        assert os.path.exists(temp_path)
        assert os.path.getsize(temp_path) > 0
        os.remove(temp_path)

    def test_conversational_refinement_to_slide_generation(self):
        """Test conversational refinement pipeline: parse initial -> refine -> generate updated slide."""
        mock_llm = Mock(spec=LLMClient)
        # 1st call: initial prompt
        initial_resp = {
            "slide_type": "process_flow",
            "content": {
                "title": "Hiring Pipeline",
                "steps": ["Application", "Phone Screen", "Final Interview"]
            }
        }
        # 2nd call: follow-up refinement
        refined_resp = {
            "slide_type": "process_flow",
            "content": {
                "title": "Hiring Pipeline",
                "steps": ["Application", "Phone Screen", "Technical Assessment", "Final Interview", "Offer"]
            }
        }
        mock_llm.generate_json_completion.side_effect = [initial_resp, refined_resp]
        
        parser = PromptParser(llm_client=mock_llm)
        conv_manager = ConversationManager(llm_client=mock_llm, prompt_parser=parser)
        
        # Step 1: Initial user message
        _, initial_intent = conv_manager.process_message(
            "recruiting_session",
            "Create a hiring pipeline process flow with 3 steps"
        )
        assert len(initial_intent.get_process_steps()) == 3
        
        # Step 2: Refine user message
        refined_intent = conv_manager.refine_intent(
            "recruiting_session",
            "Add technical assessment and offer steps, making it 5 steps total"
        )
        assert len(refined_intent.get_process_steps()) == 5
        
        # Step 3: Generate the updated slide using SlideGenerator
        generator = SlideGenerator()
        presentation = generator.generate_slide(refined_intent)
        
        assert len(presentation.slides) == 1
        exporter = PPTXExporter(presentation)
        assert exporter.validate() is True
