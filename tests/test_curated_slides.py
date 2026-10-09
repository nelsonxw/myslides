"""
Tests for CuratedSlidesReader and training-slides endpoints.
"""
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from myslides.api.main import app
from myslides.ingestion.curated_slides_reader import CuratedSlidesReader, CuratedSlideItem


@pytest.fixture
def client():
    """Create test client for FastAPI app."""
    return TestClient(app)


class TestCuratedSlidesReader:
    """Unit tests for CuratedSlidesReader service."""

    def test_list_training_slides(self):
        """Test listing training slides merging storage and database information."""
        mock_storage = MagicMock()
        mock_storage.list_curated_slides.return_value = [
            {
                "name": "slide_1.pptx",
                "storage_path": "curated slides/slide_1.pptx",
                "size": 1024,
                "updated": "2026-10-01T00:00:00Z",
                "download_url": "/download/slide_1.pptx",
                "public_url": "https://storage.googleapis.com/bucket/slide_1.pptx",
            }
        ]

        mock_db = MagicMock()
        reader = CuratedSlidesReader(storage_service=mock_storage, database_manager=mock_db)

        with patch.object(reader, "_get_indexed_templates_map", return_value={
            "slide_1.pptx": {"template_id": 42, "classification": "process_flow", "tags": ["process"]}
        }):
            items = reader.list_training_slides()
            assert len(items) == 1
            assert items[0].name == "slide_1.pptx"
            assert items[0].is_indexed is True
            assert items[0].template_id == 42
            assert items[0].classification == "process_flow"

    def test_get_catalog_status(self):
        """Test getting catalog status summary."""
        mock_storage = MagicMock()
        mock_storage.is_connected = True
        mock_storage.bucket_name = "test-bucket"

        mock_db = MagicMock()
        mock_db.get_statistics.return_value = {
            "total_templates": 10,
            "total_collections": 5,
        }

        reader = CuratedSlidesReader(storage_service=mock_storage, database_manager=mock_db)
        with patch.object(reader, "list_training_slides", return_value=[
            CuratedSlideItem("s1.pptx", "curated slides/s1.pptx", 100, None, "", "", template_id=1, is_indexed=True),
            CuratedSlideItem("s2.pptx", "curated slides/s2.pptx", 100, None, "", "", is_indexed=False),
        ]):
            status = reader.get_catalog_status()
            assert status["firebase_connected"] is True
            assert status["total_curated_in_storage"] == 2
            assert status["total_curated_indexed"] == 1
            assert status["total_templates_in_db"] == 10


class TestCuratedSlidesEndpoints:
    """Tests for curated slides API endpoints."""

    def test_get_training_slides_status(self, client):
        """Test GET /api/training-slides/status."""
        response = client.get("/api/training-slides/status")
        assert response.status_code == 200
        data = response.json()
        assert "firebase_connected" in data
        assert "storage_bucket" in data
        assert "curated_slides_folder" in data
        assert "total_curated_in_storage" in data

    def test_list_training_slides_endpoint(self, client):
        """Test GET /api/training-slides."""
        response = client.get("/api/training-slides?limit=5")
        assert response.status_code == 200
        data = response.json()
        assert "slides" in data
        assert "total" in data
        assert "indexed_count" in data

    def test_reindex_endpoints(self, client):
        """Test GET /api/training-slides/sync-and-reindex/status."""
        # Test the status endpoint
        status_resp = client.get("/api/training-slides/sync-and-reindex/status")
        assert status_resp.status_code == 200
        status_data = status_resp.json()
        assert "status" in status_data
        assert "reindex_progress_percent" in status_data
