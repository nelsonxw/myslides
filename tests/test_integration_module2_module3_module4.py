"""
End-to-End Integration Tests for Module 2, Module 3, and Module 4.

Verifies the full pipeline:
Natural Language Prompt -> PromptParser (Module 2) -> TemplateMatcher (Module 3) -> SlideGenerator (Module 4)
"""
import pytest
from unittest.mock import Mock, patch, MagicMock

from myslides.generation.generation_models import GenerationIntent, SlideType
from myslides.llm.prompt_parser import PromptParser
from myslides.template_matching.template_matcher import TemplateMatcher
from myslides.template_matching.ranking import RankingStrategy
from myslides.generation.slide_generator import SlideGenerator
from myslides.generation.pptx_exporter import PPTXExporter


class TestIntegrationModule2Module3Module4:
    """End-to-end integration test suite."""

    @patch("myslides.template_matching.template_matcher.chromadb.PersistentClient")
    @patch("myslides.template_matching.template_matcher.DatabaseManager")
    def test_pipeline_prompt_to_matching_to_slide(self, mock_db_manager, mock_chroma):
        """Test complete pipeline from prompt parsing to template matching to slide generation."""
        # 1. Setup mock ChromaDB and Database with templates
        mock_collection = MagicMock()
        mock_collection.query.return_value = {
            'ids': [['template_process_3', 'template_chart_1']],
            'distances': [[0.15, 0.65]],
            'metadatas': [[{'classification': 'process_flow'}, {'classification': 'data_chart'}]]
        }
        mock_chroma.return_value.get_or_create_collection.return_value = mock_collection

        # Ingested mock template
        mock_template = Mock()
        mock_template.id = 101
        mock_template.classification = "process_flow"
        mock_template.semantic_embedding = [0.1] * 384
        mock_template.element_manifest = {
            "shapes": [
                {"name": "step_1", "text": {"content": "Step 1"}},
                {"name": "step_2", "text": {"content": "Step 2"}},
                {"name": "step_3", "text": {"content": "Step 3"}},
            ]
        }
        mock_template.complexity_score = 4
        mock_template.tags = ["process", "flow", "workflow"]
        mock_template.to_dict.return_value = {
            "id": 101,
            "classification": "process_flow",
            "complexity_score": 4,
            "tags": ["process", "flow", "workflow"]
        }
        mock_db_manager.return_value.get_template_by_id.return_value = mock_template

        # 2. Module 2: Prompt interpretation
        mock_llm = Mock()
        mock_llm.generate_json_completion.return_value = {
            "slide_type": "process_flow",
            "content": {
                "title": "Data Processing Pipeline",
                "subtitle": "Ingestion to reporting",
                "steps": ["Collect", "Normalize", "Aggregate"]
            },
            "tone": "professional"
        }
        parser = PromptParser(llm_client=mock_llm)
        intent = parser.parse_prompt("Create a 3-step process flow for data processing")

        assert intent.slide_type == SlideType.PROCESS_FLOW
        assert len(intent.content["steps"]) == 3

        # 3. Module 3: Template Matching & Suggestion
        matcher = TemplateMatcher(ranking_strategy=RankingStrategy.SIMILARITY)
        matches = matcher.find_similar_templates(intent, n_results=5, use_adaptive_element_count=True)

        assert len(matches) > 0
        top_match = matches[0]
        assert top_match.template_id == "template_process_3"
        assert top_match.similarity_score.combined_score > 0.0

        # 4. Module 4: Slide Generation from Intent
        generator = SlideGenerator()
        presentation = generator.generate_slide(intent)
        assert presentation is not None
        assert len(presentation.slides) == 1

        # Verify shapes on slide
        slide = presentation.slides[0]
        assert len(slide.shapes) >= 3

        # Export and validate presentation
        exporter = PPTXExporter(presentation)
        assert exporter.validate() is True
