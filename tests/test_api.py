"""
Tests for FastAPI endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock

from myslides.api.main import app
from myslides.generation.pptx_exporter import PPTXExporter


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


class TestHealthCheck:
    """Test health check endpoint."""

    def test_health_check(self, client):
        """Test health check returns healthy status."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data


class TestCollectionsEndpoints:
    """Test collection-related endpoints."""

    @patch("myslides.api.main.ingestion_pipeline")
    def test_upload_collection(self, mock_pipeline, client):
        """Test uploading a PPTX file."""
        mock_pipeline.ingest_pptx_file.return_value = {
            "success": True,
            "collection_id": 1,
            "templates_created": 5
        }

        # Create a mock file
        file_content = b"mock pptx content"
        files = {"file": ("test.pptx", file_content, "application/vnd.openxmlformats-officedocument.presentationml.presentation")}

        response = client.post("/api/collections/upload", files=files)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "complete"
        assert data["templates_created"] == 5

    @patch("myslides.api.main.db_manager")
    def test_list_collections(self, mock_db, client):
        """Test listing collections."""
        mock_collection = Mock()
        mock_collection.id = 1
        mock_collection.file_name = "test.pptx"
        mock_collection.storage_path = "collections/test.pptx"
        mock_collection.total_slides = 5
        mock_collection.upload_date = "2024-01-01T00:00:00"
        mock_collection.metadata = None

        mock_db.list_collections.return_value = [mock_collection]

        response = client.get("/api/collections")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["collections"]) == 1
        assert data["collections"][0]["file_name"] == "test.pptx"


class TestTemplatesEndpoints:
    """Test template-related endpoints."""

    @patch("myslides.api.main.db_manager")
    def test_list_templates(self, mock_db, client):
        """Test listing templates."""
        mock_template = Mock()
        mock_template.id = 1
        mock_template.collection_id = 1
        mock_template.slide_index = 0
        mock_template.classification = "title_slide"
        mock_template.tags = ["title", "simple"]
        mock_template.thumbnail_path = "thumbnails/test_0.png"
        mock_template.element_manifest = {"shapes": []}
        mock_template.placeholder_map = []
        mock_template.color_palette = ["#FF0000"]
        mock_template.complexity_score = 5
        mock_template.description = "A title slide"
        mock_template.template_hash = "abc123"

        mock_db.list_templates.return_value = [mock_template]

        response = client.get("/api/templates")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["templates"]) == 1
        assert data["templates"][0]["classification"] == "title_slide"

    @patch("myslides.api.main.db_manager")
    def test_list_templates_by_classification(self, mock_db, client):
        """Test listing templates filtered by classification."""
        mock_template = Mock()
        mock_template.id = 1
        mock_template.collection_id = 1
        mock_template.slide_index = 0
        mock_template.classification = "process_flow"
        mock_template.tags = ["process"]
        mock_template.thumbnail_path = None
        mock_template.element_manifest = {}
        mock_template.placeholder_map = []
        mock_template.color_palette = []
        mock_template.complexity_score = 5
        mock_template.description = "Process flow"
        mock_template.template_hash = "hash123"

        mock_db.list_templates_by_classification.return_value = [mock_template]

        response = client.get("/api/templates?classification=process_flow")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["templates"][0]["classification"] == "process_flow"

    @patch("myslides.api.main.db_manager")
    def test_update_template(self, mock_db, client):
        """Test updating template classification and tags."""
        mock_template = Mock()
        mock_template.id = 1
        mock_template.collection_id = 1
        mock_template.slide_index = 0
        mock_template.classification = "title_slide"
        mock_template.tags = ["title"]
        mock_template.thumbnail_path = None
        mock_template.element_manifest = {}
        mock_template.placeholder_map = []
        mock_template.color_palette = []
        mock_template.complexity_score = 5
        mock_template.description = "Test"
        mock_template.template_hash = "hash123"

        mock_db.get_template.return_value = mock_template
        mock_db.update_template.return_value = mock_template

        update_data = {"classification": "agenda", "tags": ["agenda", "list"]}
        response = client.patch("/api/templates/1", json=update_data)
        assert response.status_code == 200
        data = response.json()
        assert data["classification"] == "title_slide"  # Mock returns original

    @patch("myslides.api.main.db_manager")
    def test_update_template_not_found(self, mock_db, client):
        """Test updating non-existent template."""
        mock_db.get_template.return_value = None

        update_data = {"classification": "agenda"}
        response = client.patch("/api/templates/999", json=update_data)
        assert response.status_code == 404


class TestGenerationEndpoints:
    """Test generation-related endpoints."""

    @patch("myslides.api.main.prompt_parser")
    def test_parse_prompt(self, mock_parser, client):
        """Test parsing a natural language prompt."""
        from myslides.generation.generation_models import GenerationIntent, SlideType

        mock_intent = GenerationIntent(
            slide_type=SlideType.PROCESS_FLOW,
            content={"steps": ["Step 1", "Step 2", "Step 3"]},
            tone="professional"
        )
        mock_parser.parse_prompt.return_value = mock_intent

        request_data = {"prompt_text": "Create a 3-step process flow"}
        response = client.post("/api/generate/parse-prompt", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert data["slide_type"] == "process_flow"
        assert "content" in data

    @patch("myslides.api.main.template_matcher")
    def test_suggest_templates(self, mock_matcher, client):
        """Test getting template suggestions."""
        from myslides.template_matching.template_matcher import TemplateMatch
        from myslides.template_matching.similarity_calculator import SimilarityScore

        mock_match = TemplateMatch(
            template_id="template_1",
            template_data={"classification": "process_flow"},
            similarity_score=SimilarityScore(0.8, 0.7, 0.6, 0.75),
            rank=1,
            match_reason="Good match"
        )
        mock_matcher.find_similar_templates.return_value = [mock_match]

        request_data = {
            "slide_type": "process_flow",
            "content": {"steps": ["Step 1", "Step 2"]},
            "n_results": 5
        }
        response = client.post("/api/generate/suggest-templates", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["template_id"] == "template_1"

    @patch("myslides.api.main.PPTXExporter")
    @patch("myslides.api.main.slide_generator")
    @patch("myslides.api.main.db_manager")
    def test_create_slide(self, mock_db, mock_generator, mock_exporter_class, client):
        """Test generating a slide."""
        from pptx import Presentation

        mock_presentation = MagicMock(spec=Presentation)
        mock_generator.generate_slide.return_value = mock_presentation

        mock_exporter_instance = Mock()
        mock_exporter_class.return_value = mock_exporter_instance
        mock_exporter_instance.save.return_value = "/tmp/test.pptx"

        mock_gen_request = Mock()
        mock_gen_request.id = 1
        mock_db.create_generation_request.return_value = mock_gen_request

        request_data = {
            "slide_type": "title_slide",
            "content": {"title": "Test Slide"}
        }
        response = client.post("/api/generate/create-slide", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "complete"
        assert "request_id" in data

    @patch("myslides.api.main.PPTXExporter")
    @patch("myslides.api.main.deck_planner")
    @patch("myslides.api.main.slide_generator")
    @patch("myslides.api.main.db_manager")
    def test_create_deck(self, mock_db, mock_generator, mock_planner, mock_exporter_class, client):
        """Test generating a deck."""
        from myslides.llm.deck_planner import DeckPlan
        from myslides.generation.generation_models import GenerationIntent, SlideType
        from pptx import Presentation

        mock_intent = GenerationIntent(
            slide_type=SlideType.TITLE_SLIDE,
            content={"title": "Test"}
        )
        mock_plan = DeckPlan(title="Test Deck", description="Test", slide_intents=[mock_intent])
        mock_planner.plan_deck.return_value = mock_plan

        mock_presentation = MagicMock(spec=Presentation)
        mock_generator.generate_deck.return_value = mock_presentation

        mock_exporter_instance = Mock()
        mock_exporter_class.return_value = mock_exporter_instance
        mock_exporter_instance.save.return_value = "/tmp/test.pptx"

        mock_deck = Mock()
        mock_deck.id = 1
        mock_db.create_deck.return_value = mock_deck

        request_data = {
            "prompts": ["Create a title slide"],
            "title": "Test Deck"
        }
        response = client.post("/api/generate/create-deck", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "complete"
        assert data["slide_count"] == 1


class TestPalettesEndpoints:
    """Test palette-related endpoints."""

    @patch("myslides.api.main.db_manager")
    def test_list_palettes(self, mock_db, client):
        """Test listing color palettes."""
        mock_template = Mock()
        mock_template.id = 1
        mock_template.collection_id = 1
        mock_template.color_palette = ["#FF0000", "#00FF00", "#0000FF"]

        mock_db.list_templates.return_value = [mock_template]

        response = client.get("/api/palettes")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["palettes"]) == 1
        assert data["palettes"][0]["colors"] == ["#FF0000", "#00FF00", "#0000FF"]


class TestPhase2Endpoints:
    """Test Phase 2 API endpoints."""

    @patch("myslides.api.main.db_manager")
    def test_get_deck(self, mock_db, client):
        """Test getting a deck."""
        mock_deck = Mock()
        mock_deck.id = 1
        mock_deck.title = "Pitch Deck"
        mock_deck.slides = [1, 2, 3]
        mock_deck.created_at = None
        mock_db.get_deck.return_value = mock_deck

        response = client.get("/api/decks/1")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 1
        assert data["title"] == "Pitch Deck"
        assert data["slides"] == [1, 2, 3]

    @patch("myslides.api.main.db_manager")
    def test_update_deck(self, mock_db, client):
        """Test updating a deck."""
        mock_deck = Mock()
        mock_deck.id = 1
        mock_db.update_deck.return_value = mock_deck

        response = client.patch("/api/decks/1", json={"slides": [3, 2, 1]})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    def test_parse_csv_endpoint(self, client):
        """Test CSV parsing endpoint."""
        csv_content = b"Metric,2023,2024\nRevenue,100,150"
        files = {"file": ("data.csv", csv_content, "text/csv")}
        response = client.post("/api/data/parse-csv", files=files)
        assert response.status_code == 200
        data = response.json()
        assert data["categories"] == ["2023", "2024"]
        assert data["series_data"]["Revenue"] == [100.0, 150.0]
