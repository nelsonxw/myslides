"""
Tests for Ingestion Pipeline module.
"""
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import tempfile

from myslides.ingestion.ingestion_pipeline import IngestionPipeline
from myslides.ingestion.pptx_parser import SlideInfo, SlideLayoutType, PositionInfo


class TestIngestionPipeline:
    """Tests for IngestionPipeline class."""
    
    @pytest.fixture
    def pipeline(self):
        """Create an IngestionPipeline instance."""
        return IngestionPipeline()
    
    @pytest.fixture
    def sample_pptx_file(self, tmp_path):
        """Create a sample PPTX file for testing."""
        pptx_path = tmp_path / "test.pptx"
        pptx_path.touch()  # Create empty file
        return pptx_path
    
    def test_initialization(self, pipeline):
        """Test pipeline initialization."""
        assert pipeline.storage_service is not None
        assert pipeline.database_manager is not None
        assert pipeline.template_extractor is not None
        assert pipeline.embedding_generator is not None
    
    def test_ingestion_status(self, pipeline):
        """Test getting ingestion pipeline status."""
        status = pipeline.get_ingestion_status()
        
        assert "storage" in status
        assert "database" in status
        assert "data_directories" in status
        assert "bucket_name" in status["storage"]
        assert "total_collections" in status["database"]
    
    @patch('myslides.ingestion.ingestion_pipeline.PPTXParser')
    def test_ingest_pptx_file_success(self, mock_parser_class, pipeline, sample_pptx_file):
        """Test successful PPTX file ingestion."""
        # Mock the parser for individual slide
        mock_parser = Mock()
        mock_parser.parse_slide.return_value = SlideInfo(
            slide_index=0,
            layout_type=SlideLayoutType.TITLE_SLIDE,
            width=9144000,
            height=6858000,
            shapes=[],
            charts=[],
            tables=[],
            images=[],
            text_content="Test Title",
            color_palette=["#FF0000"],
            complexity_score=5
        )
        mock_parser.get_presentation_metadata.return_value = {
            "file_name": sample_pptx_file.name,
            "slide_count": 1,  # Individual slides always have 1 slide
            "width": 9144000,
            "height": 6858000
        }
        mock_parser_class.return_value = mock_parser
        
        # Mock storage service
        with patch.object(pipeline.storage_service, 'upload_pptx') as mock_upload:
            mock_upload.return_value = Mock(
                id="test_storage_id",
                storage_path="collections/test/test.pptx"
            )
            
            # Mock thumbnail generation
            with patch.object(pipeline, '_generate_slide_thumbnail') as mock_thumbnail:
                mock_thumbnail.return_value = None
                
                # Mock storage service for thumbnails
                with patch.object(pipeline.storage_service, 'upload_thumbnail') as mock_upload_thumb:
                    mock_upload_thumb.return_value = Mock(storage_path="thumbnails/test.png")
                    
                    result = pipeline.ingest_pptx_file(
                        sample_pptx_file,
                        "test_collection",
                        generate_thumbnails=False
                    )
        
        assert result["success"] is True
        assert result["slides_processed"] == 1  # Individual slides always have 1 slide
        assert result["templates_created"] == 1
        assert result["collection_id"] is not None
    
    @patch('myslides.ingestion.ingestion_pipeline.PPTXParser')
    def test_ingest_pptx_file_with_error(self, mock_parser_class, pipeline, sample_pptx_file):
        """Test PPTX file ingestion with error."""
        # Mock parser to raise an error
        mock_parser_class.side_effect = Exception("Parser error")
        
        result = pipeline.ingest_pptx_file(
            sample_pptx_file,
            "test_collection"
        )
        
        assert result["success"] is False
        assert len(result["errors"]) > 0
        assert "Parser error" in result["errors"][0]
    
    def test_generate_slide_thumbnail(self, pipeline, tmp_path):
        """Test thumbnail generation for a slide."""
        pptx_path = tmp_path / "test.pptx"
        pptx_path.touch()
        
        thumbnail_path = pipeline._generate_slide_thumbnail(
            pptx_path,
            slide_index=0,
            collection_name="test_collection"
        )
        
        if thumbnail_path:
            assert thumbnail_path.exists()
            assert thumbnail_path.suffix == ".png"
            assert "test_collection" in thumbnail_path.name
            assert "slide_0" in thumbnail_path.name
    
    def test_generate_slide_thumbnail_error_handling(self, pipeline, tmp_path):
        """Test thumbnail generation error handling."""
        pptx_path = tmp_path / "test.pptx"
        pptx_path.touch()
        
        # Mock PIL to raise an error
        with patch('myslides.ingestion.ingestion_pipeline.Image', side_effect=Exception("PIL error")):
            thumbnail_path = pipeline._generate_slide_thumbnail(
                pptx_path,
                slide_index=0,
                collection_name="test_collection"
            )
            
            # Should return None on error
            assert thumbnail_path is None
    
    @patch('myslides.ingestion.ingestion_pipeline.PPTXParser')
    def test_process_batch_files(self, mock_parser_class, pipeline, tmp_path):
        """Test batch processing of multiple PPTX files."""
        # Create multiple test files
        pptx_files = [
            tmp_path / "test1.pptx",
            tmp_path / "test2.pptx",
            tmp_path / "test3.pptx"
        ]
        for pptx_file in pptx_files:
            pptx_file.touch()
        
        # Mock the parser
        mock_parser = Mock()
        sample_slide = SlideInfo(
            slide_index=0,
            layout_type=SlideLayoutType.TITLE_SLIDE,
            width=9144000,
            height=6858000,
            shapes=[],
            charts=[],
            tables=[],
            images=[],
            text_content="Test",
            color_palette=[],
            complexity_score=5
        )
        mock_parser.parse_slide.return_value = sample_slide
        mock_parser.parse_all_slides.return_value = [sample_slide]
        mock_parser.get_presentation_metadata.return_value = {
            "file_name": "test.pptx",
            "slide_count": 1,
            "width": 9144000,
            "height": 6858000
        }
        mock_parser_class.return_value = mock_parser
        
        # Mock storage service
        with patch.object(pipeline.storage_service, 'upload_pptx') as mock_upload:
            mock_upload.return_value = Mock(
                id="test_storage_id",
                storage_path="collections/test/test.pptx"
            )
            
            with patch.object(pipeline, '_generate_slide_thumbnail') as mock_thumbnail:
                mock_thumbnail.return_value = None
                
                with patch.object(pipeline.storage_service, 'upload_thumbnail') as mock_upload_thumb:
                    mock_upload_thumb.return_value = Mock(storage_path="thumbnails/test.png")
                    
                    result = pipeline.process_batch_files(
                        pptx_files,
                        "test_batch",
                        generate_thumbnails=False
                    )
        
        assert result["total_files"] == 3
        assert result["successful_files"] == 3
        assert result["failed_files"] == 0
        assert result["total_slides_processed"] == 3
        assert result["total_templates_created"] == 3
        assert len(result["file_results"]) == 3
    
    @patch('myslides.ingestion.ingestion_pipeline.PPTXParser')
    def test_process_batch_files_with_failure(self, mock_parser_class, pipeline, tmp_path):
        """Test batch processing with some failures."""
        # Create test files
        pptx_files = [
            tmp_path / "test1.pptx",
            tmp_path / "test2.pptx"
        ]
        for pptx_file in pptx_files:
            pptx_file.touch()
        
        # Mock parser to fail on second call
        call_count = [0]
        def side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                mock_parser = Mock()
                sample_slide = SlideInfo(
                    slide_index=0,
                    layout_type=SlideLayoutType.TITLE_SLIDE,
                    width=9144000,
                    height=6858000,
                    shapes=[],
                    charts=[],
                    tables=[],
                    images=[],
                    text_content="Test",
                    color_palette=[],
                    complexity_score=5
                )
                mock_parser.parse_slide.return_value = sample_slide
                mock_parser.parse_all_slides.return_value = [sample_slide]
                mock_parser.get_presentation_metadata.return_value = {
                    "file_name": "test.pptx",
                    "slide_count": 1,
                    "width": 9144000,
                    "height": 6858000
                }
                return mock_parser
            else:
                raise Exception("Parser error")
        
        mock_parser_class.side_effect = side_effect
        
        # Mock storage service
        with patch.object(pipeline.storage_service, 'upload_pptx') as mock_upload:
            mock_upload.return_value = Mock(
                id="test_storage_id",
                storage_path="collections/test/test.pptx"
            )
            
            with patch.object(pipeline, '_generate_slide_thumbnail') as mock_thumbnail:
                mock_thumbnail.return_value = None
                
                with patch.object(pipeline.storage_service, 'upload_thumbnail') as mock_upload_thumb:
                    mock_upload_thumb.return_value = Mock(storage_path="thumbnails/test.png")
                    
                    result = pipeline.process_batch_files(
                        pptx_files,
                        "test_batch",
                        generate_thumbnails=False
                    )
        
        assert result["total_files"] == 2
        assert result["successful_files"] == 1
        assert result["failed_files"] == 1
        assert len(result["errors"]) > 0
    
    def test_process_batch_files_empty_list(self, pipeline):
        """Test batch processing with empty file list."""
        result = pipeline.process_batch_files([], "test_batch")
        
        assert result["total_files"] == 0
        assert result["successful_files"] == 0
        assert result["failed_files"] == 0
        assert result["success"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
