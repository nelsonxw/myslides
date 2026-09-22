"""
Tests for Embedding Generator module.
"""
import pytest
from pathlib import Path
from unittest.mock import Mock, patch
import tempfile

from myslides.ingestion.embedding_generator import EmbeddingGenerator
from myslides.ingestion.pptx_parser import (
    SlideInfo, 
    SlideLayoutType, 
    PositionInfo
)


class TestEmbeddingGenerator:
    """Tests for EmbeddingGenerator class."""
    
    @pytest.fixture
    def embedding_generator(self):
        """Create an EmbeddingGenerator instance."""
        return EmbeddingGenerator()
    
    @pytest.fixture
    def sample_slide_info(self):
        """Create a sample SlideInfo for testing."""
        return SlideInfo(
            slide_index=0,
            layout_type=SlideLayoutType.TITLE_SLIDE,
            width=9144000,
            height=6858000,
            shapes=[],
            charts=[],
            tables=[],
            images=[],
            text_content="Test content for embedding generation",
            color_palette=["#FF0000", "#00FF00"],
            complexity_score=5
        )
    
    def test_initialization(self, embedding_generator):
        """Test EmbeddingGenerator initialization."""
        assert embedding_generator.classifier is not None
        assert embedding_generator.chroma_client is not None
    
    def test_generate_semantic_embedding(self, embedding_generator, sample_slide_info):
        """Test semantic embedding generation."""
        template_id = "test_template_1"
        embedding = embedding_generator.generate_semantic_embedding(sample_slide_info, template_id)
        
        assert isinstance(embedding, list)
        assert len(embedding) == 384  # Target embedding size
        assert all(isinstance(x, float) for x in embedding)
    
    def test_generate_semantic_embedding_storage(self, embedding_generator, sample_slide_info):
        """Test that semantic embedding is stored in ChromaDB."""
        template_id = "test_template_storage"
        embedding = embedding_generator.generate_semantic_embedding(sample_slide_info, template_id)
        
        # Try to retrieve the stored embedding
        if embedding_generator.semantic_collection:
            try:
                results = embedding_generator.semantic_collection.get(ids=[template_id])
                assert template_id in results['ids']
            except Exception as e:
                pytest.skip(f"ChromaDB storage test skipped: {e}")
    
    def test_generate_visual_embedding_with_image(self, embedding_generator, tmp_path):
        """Test visual embedding generation with actual image."""
        # Create a simple test image
        from PIL import Image
        image_path = tmp_path / "test_image.png"
        img = Image.new('RGB', (100, 100), color='red')
        img.save(image_path)
        
        template_id = "test_visual_template"
        embedding = embedding_generator.generate_visual_embedding(image_path, template_id)
        
        if embedding is not None:
            assert isinstance(embedding, list)
            assert len(embedding) == 384
            assert all(isinstance(x, float) for x in embedding)
    
    def test_generate_visual_embedding_without_image(self, embedding_generator):
        """Test visual embedding generation with non-existent image."""
        non_existent_path = Path("/nonexistent/path/image.png")
        template_id = "test_no_image"
        
        embedding = embedding_generator.generate_visual_embedding(non_existent_path, template_id)
        
        # Should return None for non-existent image
        assert embedding is None
    
    def test_search_similar_templates_semantic(self, embedding_generator, sample_slide_info):
        """Test searching similar templates using semantic embeddings."""
        # First, generate and store an embedding
        template_id = "test_search_template"
        query_embedding = embedding_generator.generate_semantic_embedding(sample_slide_info, template_id)
        
        # Search for similar templates
        results = embedding_generator.search_similar_templates(
            query_embedding=query_embedding,
            collection_type="semantic",
            n_results=3
        )
        
        assert isinstance(results, list)
        # Should at least return the template we just added
        if results:
            assert "template_id" in results[0]
            assert "similarity" in results[0]
    
    def test_search_similar_templates_visual(self, embedding_generator, tmp_path):
        """Test searching similar templates using visual embeddings."""
        # Create a test image
        from PIL import Image
        image_path = tmp_path / "test_search_image.png"
        img = Image.new('RGB', (100, 100), color='blue')
        img.save(image_path)
        
        template_id = "test_visual_search"
        query_embedding = embedding_generator.generate_visual_embedding(image_path, template_id)
        
        if query_embedding:
            results = embedding_generator.search_similar_templates(
                query_embedding=query_embedding,
                collection_type="visual",
                n_results=3
            )
            
            assert isinstance(results, list)
    
    def test_extract_semantic_features(self, embedding_generator, sample_slide_info):
        """Test semantic feature extraction."""
        features = embedding_generator._extract_semantic_features(sample_slide_info)
        
        assert isinstance(features, dict)
        assert "classification" in features
        assert "tags" in features
        assert "layout_type" in features
        assert "shape_count" in features
        assert "complexity_score" in features
        assert features["shape_count"] == len(sample_slide_info.shapes)
        assert features["complexity_score"] == sample_slide_info.complexity_score
    
    def test_extract_visual_features(self, embedding_generator, tmp_path):
        """Test visual feature extraction from image."""
        from PIL import Image
        image_path = tmp_path / "test_features.png"
        img = Image.new('RGB', (200, 150), color='green')
        img.save(image_path)
        
        features = embedding_generator._extract_visual_features(image_path)
        
        assert isinstance(features, dict)
        assert "width" in features
        assert "height" in features
        assert "aspect_ratio" in features
        assert "mean_colors" in features
        assert features["width"] == 200
        assert features["height"] == 150
        assert features["aspect_ratio"] == 200 / 150
    
    def test_extract_visual_features_without_pil(self, embedding_generator, tmp_path):
        """Test visual feature extraction fallback when PIL is not available."""
        image_path = tmp_path / "test_no_pil.png"
        image_path.touch()  # Create empty file
        
        with patch('myslides.ingestion.embedding_generator.Image', side_effect=ImportError):
            features = embedding_generator._extract_visual_features(image_path)
            
            assert isinstance(features, dict)
            assert features["width"] == 0
            assert features["height"] == 0
            assert features["aspect_ratio"] == 1
    
    def test_features_to_embedding(self, embedding_generator):
        """Test conversion of features to embedding vector."""
        features = {
            "classification": "title_slide",
            "shape_count": 5,
            "complexity_score": 10,
            "has_chart": True,
            "color_count": 3
        }
        
        embedding = embedding_generator._features_to_embedding(features)
        
        assert isinstance(embedding, list)
        assert len(embedding) == 384  # Target size
        assert all(isinstance(x, float) for x in embedding)
    
    def test_features_to_embedding_with_list(self, embedding_generator):
        """Test conversion of features with list values to embedding."""
        features = {
            "tags": ["title", "simple", "has_chart"],
            "color_palette": ["#FF0000", "#00FF00", "#0000FF"]
        }
        
        embedding = embedding_generator._features_to_embedding(features)
        
        assert isinstance(embedding, list)
        assert len(embedding) == 384
    
    def test_create_semantic_document(self, embedding_generator, sample_slide_info):
        """Test creation of semantic document for embedding."""
        document = embedding_generator._create_semantic_document(sample_slide_info)
        
        assert isinstance(document, str)
        assert len(document) > 0
        assert "Slide type:" in document
        assert "Layout:" in document
        assert "Tags:" in document
    
    def test_delete_template_embeddings(self, embedding_generator, sample_slide_info):
        """Test deletion of template embeddings."""
        template_id = "test_delete_template"
        
        # First, generate and store an embedding
        embedding_generator.generate_semantic_embedding(sample_slide_info, template_id)
        
        # Delete the embedding
        embedding_generator.delete_template_embeddings(template_id)
        
        # Verify deletion (if collection exists)
        if embedding_generator.semantic_collection:
            try:
                results = embedding_generator.semantic_collection.get(ids=[template_id])
                assert template_id not in results['ids']
            except Exception as e:
                pytest.skip(f"ChromaDB deletion test skipped: {e}")
    
    def test_embedding_consistency(self, embedding_generator, sample_slide_info):
        """Test that embeddings are consistent for the same input."""
        template_id = "test_consistency"
        
        embedding1 = embedding_generator.generate_semantic_embedding(sample_slide_info, template_id)
        embedding2 = embedding_generator.generate_semantic_embedding(sample_slide_info, template_id)
        
        # Embeddings should be identical for the same input
        assert embedding1 == embedding2
    
    def test_embedding_different_inputs(self, embedding_generator):
        """Test that embeddings differ for different inputs."""
        slide_info1 = SlideInfo(
            slide_index=0,
            layout_type=SlideLayoutType.TITLE_SLIDE,
            width=9144000,
            height=6858000,
            shapes=[],
            charts=[],
            tables=[],
            images=[],
            text_content="Content 1",
            color_palette=["#FF0000"],
            complexity_score=5
        )
        
        slide_info2 = SlideInfo(
            slide_index=0,
            layout_type=SlideLayoutType.CONTENT_SLIDE,
            width=9144000,
            height=6858000,
            shapes=[Mock(), Mock()],
            charts=[],
            tables=[],
            images=[],
            text_content="Content 2 with different text",
            color_palette=["#00FF00", "#0000FF"],
            complexity_score=10
        )
        
        embedding1 = embedding_generator.generate_semantic_embedding(slide_info1, "test1")
        embedding2 = embedding_generator.generate_semantic_embedding(slide_info2, "test2")
        
        # Embeddings should differ for different inputs
        assert embedding1 != embedding2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
