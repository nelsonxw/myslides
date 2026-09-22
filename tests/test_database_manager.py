"""
Tests for Database Manager module.
"""
import pytest
import tempfile
from pathlib import Path
from datetime import datetime

from myslides.database.database_manager import DatabaseManager
from myslides.database.models import SlideCollection, SlideTemplate, GenerationRequest, GeneratedDeck


class TestDatabaseManager:
    """Tests for DatabaseManager class."""
    
    @pytest.fixture
    def db_manager(self, tmp_path):
        """Create a DatabaseManager instance with temporary database."""
        # Use a temporary database file
        from myslides.config import settings
        original_db_url = settings.database_url
        settings.database_url = f"sqlite:///{tmp_path / 'test_myslides.db'}"
        
        manager = DatabaseManager()
        
        yield manager
        
        # Cleanup
        settings.database_url = original_db_url
    
    def test_initialization(self, db_manager):
        """Test database manager initialization."""
        assert db_manager.engine is not None
        assert db_manager.SessionLocal is not None
    
    def test_create_collection(self, db_manager):
        """Test creating a slide collection."""
        collection = db_manager.create_collection(
            file_name="test.pptx",
            storage_path="collections/test/test.pptx",
            total_slides=5,
            metadata={"source": "test"}
        )
        
        assert collection.id is not None
        assert collection.file_name == "test.pptx"
        assert collection.storage_path == "collections/test/test.pptx"
        assert collection.total_slides == 5
        assert collection.metadata == {"source": "test"}
    
    def test_get_collection(self, db_manager):
        """Test retrieving a collection by ID."""
        collection = db_manager.create_collection(
            file_name="test.pptx",
            storage_path="collections/test/test.pptx",
            total_slides=3
        )
        
        retrieved = db_manager.get_collection(collection.id)
        
        assert retrieved is not None
        assert retrieved.id == collection.id
        assert retrieved.file_name == "test.pptx"
    
    def test_get_nonexistent_collection(self, db_manager):
        """Test retrieving a non-existent collection."""
        retrieved = db_manager.get_collection(99999)
        assert retrieved is None
    
    def test_list_collections(self, db_manager):
        """Test listing all collections."""
        # Create multiple collections
        db_manager.create_collection("test1.pptx", "collections/test1.pptx", 5)
        db_manager.create_collection("test2.pptx", "collections/test2.pptx", 3)
        db_manager.create_collection("test3.pptx", "collections/test3.pptx", 7)
        
        collections = db_manager.list_collections()
        
        assert len(collections) == 3
        assert all(isinstance(c, SlideCollection) for c in collections)
    
    def test_delete_collection(self, db_manager):
        """Test deleting a collection."""
        collection = db_manager.create_collection(
            file_name="test.pptx",
            storage_path="collections/test/test.pptx",
            total_slides=5
        )
        
        result = db_manager.delete_collection(collection.id)
        
        assert result is True
        
        # Verify deletion
        retrieved = db_manager.get_collection(collection.id)
        assert retrieved is None
    
    def test_delete_nonexistent_collection(self, db_manager):
        """Test deleting a non-existent collection."""
        result = db_manager.delete_collection(99999)
        assert result is False
    
    def test_create_template(self, db_manager):
        """Test creating a slide template."""
        collection = db_manager.create_collection("test.pptx", "collections/test.pptx", 5)
        
        template_data = {
            "collection_id": collection.id,
            "slide_index": 0,
            "classification": "title_slide",
            "tags": ["title", "simple"],
            "thumbnail_path": "thumbnails/test_0.png",
            "original_pptx_reference": "collections/test.pptx",
            "element_manifest": {"shapes": []},
            "placeholder_map": [],
            "color_palette": ["#FF0000"],
            "complexity_score": 5,
            "description": "A title slide",
            "template_hash": "abc123"
        }
        
        template = db_manager.create_template(template_data)
        
        assert template.id is not None
        assert template.collection_id == collection.id
        assert template.classification == "title_slide"
        assert template.complexity_score == 5
    
    def test_get_template(self, db_manager):
        """Test retrieving a template by ID."""
        collection = db_manager.create_collection("test.pptx", "collections/test.pptx", 5)
        
        template_data = {
            "collection_id": collection.id,
            "slide_index": 0,
            "classification": "title_slide",
            "tags": ["title"],
            "thumbnail_path": None,
            "original_pptx_reference": "collections/test.pptx",
            "element_manifest": {},
            "placeholder_map": [],
            "color_palette": [],
            "complexity_score": 5,
            "description": "Test",
            "template_hash": "hash123"
        }
        
        template = db_manager.create_template(template_data)
        retrieved = db_manager.get_template(template.id)
        
        assert retrieved is not None
        assert retrieved.id == template.id
        assert retrieved.classification == "title_slide"
    
    def test_list_templates(self, db_manager):
        """Test listing templates."""
        collection = db_manager.create_collection("test.pptx", "collections/test.pptx", 3)
        
        # Create multiple templates
        for i in range(3):
            template_data = {
                "collection_id": collection.id,
                "slide_index": i,
                "classification": "content_slide",
                "tags": ["content"],
                "thumbnail_path": None,
                "original_pptx_reference": "collections/test.pptx",
                "element_manifest": {},
                "placeholder_map": [],
                "color_palette": [],
                "complexity_score": 5,
                "description": f"Slide {i}",
                "template_hash": f"hash{i}"
            }
            db_manager.create_template(template_data)
        
        templates = db_manager.list_templates(collection_id=collection.id)
        
        assert len(templates) == 3
        assert all(t.collection_id == collection.id for t in templates)
    
    def test_list_templates_by_classification(self, db_manager):
        """Test listing templates filtered by classification."""
        collection = db_manager.create_collection("test.pptx", "collections/test.pptx", 3)
        
        # Create templates with different classifications
        for classification in ["title_slide", "content_slide", "data_chart"]:
            template_data = {
                "collection_id": collection.id,
                "slide_index": 0,
                "classification": classification,
                "tags": [classification],
                "thumbnail_path": None,
                "original_pptx_reference": "collections/test.pptx",
                "element_manifest": {},
                "placeholder_map": [],
                "color_palette": [],
                "complexity_score": 5,
                "description": classification,
                "template_hash": classification
            }
            db_manager.create_template(template_data)
        
        title_templates = db_manager.list_templates(classification="title_slide")
        
        assert len(title_templates) == 1
        assert title_templates[0].classification == "title_slide"
    
    def test_update_template(self, db_manager):
        """Test updating a template."""
        collection = db_manager.create_collection("test.pptx", "collections/test.pptx", 5)
        
        template_data = {
            "collection_id": collection.id,
            "slide_index": 0,
            "classification": "title_slide",
            "tags": ["title"],
            "thumbnail_path": None,
            "original_pptx_reference": "collections/test.pptx",
            "element_manifest": {},
            "placeholder_map": [],
            "color_palette": [],
            "complexity_score": 5,
            "description": "Original description",
            "template_hash": "hash123"
        }
        
        template = db_manager.create_template(template_data)
        
        updated = db_manager.update_template(template.id, {
            "description": "Updated description",
            "complexity_score": 10
        })
        
        assert updated is not None
        assert updated.description == "Updated description"
        assert updated.complexity_score == 10
    
    def test_delete_template(self, db_manager):
        """Test deleting a template."""
        collection = db_manager.create_collection("test.pptx", "collections/test.pptx", 5)
        
        template_data = {
            "collection_id": collection.id,
            "slide_index": 0,
            "classification": "title_slide",
            "tags": ["title"],
            "thumbnail_path": None,
            "original_pptx_reference": "collections/test.pptx",
            "element_manifest": {},
            "placeholder_map": [],
            "color_palette": [],
            "complexity_score": 5,
            "description": "Test",
            "template_hash": "hash123"
        }
        
        template = db_manager.create_template(template_data)
        result = db_manager.delete_template(template.id)
        
        assert result is True
        
        # Verify deletion
        retrieved = db_manager.get_template(template.id)
        assert retrieved is None
    
    def test_search_templates_by_tags(self, db_manager):
        """Test searching templates by tags."""
        collection = db_manager.create_collection("test.pptx", "collections/test.pptx", 5)
        
        # Create templates with different tags
        tags_sets = [["title", "simple"], ["content", "chart"], ["title", "complex"]]
        for tags in tags_sets:
            template_data = {
                "collection_id": collection.id,
                "slide_index": 0,
                "classification": "content_slide",
                "tags": tags,
                "thumbnail_path": None,
                "original_pptx_reference": "collections/test.pptx",
                "element_manifest": {},
                "placeholder_map": [],
                "color_palette": [],
                "complexity_score": 5,
                "description": "Test",
                "template_hash": "hash123"
            }
            db_manager.create_template(template_data)
        
        results = db_manager.search_templates_by_tags(["title"])
        
        assert len(results) == 2
        assert all("title" in t.tags for t in results)
    
    def test_create_generation_request(self, db_manager):
        """Test creating a generation request."""
        request = db_manager.create_generation_request(
            prompt_text="Create a title slide",
            user_id="test_user"
        )
        
        assert request.id is not None
        assert request.prompt_text == "Create a title slide"
        assert request.user_id == "test_user"
        assert request.status == "pending"
    
    def test_update_generation_request(self, db_manager):
        """Test updating a generation request."""
        request = db_manager.create_generation_request("Test prompt")
        
        updated = db_manager.update_generation_request(request.id, {
            "status": "complete",
            "parsed_intent": {"slide_type": "title_slide"},
            "processing_time_seconds": 5.5
        })
        
        assert updated is not None
        assert updated.status == "complete"
        assert updated.parsed_intent == {"slide_type": "title_slide"}
        assert updated.processing_time_seconds == 5.5
    
    def test_list_generation_requests(self, db_manager):
        """Test listing generation requests."""
        db_manager.create_generation_request("Prompt 1")
        db_manager.create_generation_request("Prompt 2")
        db_manager.create_generation_request("Prompt 3")
        
        requests = db_manager.list_generation_requests()
        
        assert len(requests) == 3
        assert all(isinstance(r, GenerationRequest) for r in requests)
    
    def test_create_deck(self, db_manager):
        """Test creating a generated deck."""
        request1 = db_manager.create_generation_request("Prompt 1")
        request2 = db_manager.create_generation_request("Prompt 2")
        
        deck = db_manager.create_deck(
            title="Test Deck",
            slides=[request1.id, request2.id],
            user_id="test_user"
        )
        
        assert deck.id is not None
        assert deck.title == "Test Deck"
        assert deck.slides == [request1.id, request2.id]
        assert deck.export_format == "pptx"
    
    def test_get_statistics(self, db_manager):
        """Test getting database statistics."""
        # Create some test data
        collection = db_manager.create_collection("test.pptx", "collections/test.pptx", 5)
        db_manager.create_template({
            "collection_id": collection.id,
            "slide_index": 0,
            "classification": "title_slide",
            "tags": ["title"],
            "thumbnail_path": None,
            "original_pptx_reference": "collections/test.pptx",
            "element_manifest": {},
            "placeholder_map": [],
            "color_palette": [],
            "complexity_score": 5,
            "description": "Test",
            "template_hash": "hash123"
        })
        db_manager.create_generation_request("Test prompt")
        
        stats = db_manager.get_statistics()
        
        assert stats["total_collections"] >= 1
        assert stats["total_templates"] >= 1
        assert stats["total_requests"] >= 1
        assert "classification_breakdown" in stats
    
    def test_session_context_manager(self, db_manager):
        """Test session context manager for transaction handling."""
        with db_manager.get_session() as session:
            collection = db_manager.create_collection("test.pptx", "collections/test.pptx", 5)
            # Session should be committed automatically
        
        # Verify the collection was saved
        retrieved = db_manager.get_collection(collection.id)
        assert retrieved is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
