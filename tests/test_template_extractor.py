"""
Tests for Template Extractor module.
"""
import pytest
from unittest.mock import Mock
from datetime import datetime

from myslides.ingestion.template_extractor import (
    TemplateExtractor, 
    SlideTemplate,
    PlaceholderMap
)
from myslides.ingestion.pptx_parser import (
    SlideInfo, 
    SlideLayoutType, 
    ChartType,
    ShapeInfo,
    ChartInfo,
    TableInfo,
    ImageInfo,
    PositionInfo,
    TextContent,
    FontInfo,
    ColorInfo
)
from myslides.ingestion.slide_classifier import SlideCategory


class TestTemplateExtractor:
    """Tests for TemplateExtractor class."""
    
    @pytest.fixture
    def extractor(self):
        """Create a TemplateExtractor instance."""
        return TemplateExtractor()
    
    @pytest.fixture
    def sample_slide_info(self):
        """Create a sample SlideInfo for testing."""
        # Create sample font and color info
        font_info = FontInfo(
            name="Arial",
            size=14.0,
            bold=True,
            italic=False,
            underline=False,
            color=ColorInfo(hex_value="#FF0000", rgb=(255, 0, 0), brightness=0.3)
        )
        
        text_content = TextContent(
            text="Sample Title",
            font=font_info,
            paragraphs=["Sample Title"]
        )
        
        # Create sample shape
        shape_info = ShapeInfo(
            shape_id=1,
            shape_type="rectangle",
            name="Rectangle 1",
            position=PositionInfo(100, 100, 300, 200),
            fill_color=ColorInfo(hex_value="#00FF00", rgb=(0, 255, 0), brightness=0.7),
            line_color=ColorInfo(hex_value="#000000", rgb=(0, 0, 0), brightness=0.0),
            text_content=text_content,
            is_grouped=False,
            group_id=None
        )
        
        return SlideInfo(
            slide_index=0,
            layout_type=SlideLayoutType.TITLE_SLIDE,
            width=9144000,
            height=6858000,
            shapes=[shape_info],
            charts=[],
            tables=[],
            images=[],
            text_content="Sample Title",
            color_palette=["#FF0000", "#00FF00", "#000000"],
            complexity_score=5
        )
    
    def test_extract_template_basic(self, extractor, sample_slide_info):
        """Test basic template extraction."""
        template = extractor.extract_template(
            slide_info=sample_slide_info,
            collection_id="test_collection",
            original_filename="test.pptx",
            thumbnail_path=None
        )
        
        assert isinstance(template, SlideTemplate)
        assert template.collection_id == "test_collection"
        assert template.slide_index == 0
        assert template.classification in [cat.value for cat in SlideCategory]
        assert template.complexity_score == 5
        assert template.color_palette == ["#FF0000", "#00FF00", "#000000"]
    
    def test_extract_template_with_thumbnail(self, extractor, sample_slide_info):
        """Test template extraction with thumbnail."""
        thumbnail_path = "thumbnails/test_slide_0.png"
        
        template = extractor.extract_template(
            slide_info=sample_slide_info,
            collection_id="test_collection",
            original_filename="test.pptx",
            thumbnail_path=thumbnail_path
        )
        
        assert template.thumbnail_path == thumbnail_path
    
    def test_extract_template_id_generation(self, extractor, sample_slide_info):
        """Test template ID generation."""
        template = extractor.extract_template(
            slide_info=sample_slide_info,
            collection_id="test_collection",
            original_filename="test.pptx"
        )
        
        assert template.template_id == "test_collection_slide_0"
    
    def test_extract_element_manifest(self, extractor, sample_slide_info):
        """Test element manifest extraction."""
        manifest = extractor._extract_element_manifest(sample_slide_info)
        
        assert "slide_dimensions" in manifest
        assert manifest["slide_dimensions"]["width"] == 9144000
        assert manifest["slide_dimensions"]["height"] == 6858000
        assert "shapes" in manifest
        assert len(manifest["shapes"]) == 1
        assert manifest["shapes"][0]["shape_id"] == 1
        assert manifest["shapes"][0]["shape_type"] == "rectangle"
    
    def test_extract_element_manifest_with_chart(self, extractor):
        """Test element manifest extraction with chart."""
        chart_info = ChartInfo(
            chart_type=ChartType.BAR,
            title="Sales Chart",
            has_legend=True,
            data_series_count=2,
            category_count=4,
            position=PositionInfo(100, 100, 500, 300)
        )
        
        slide_info = SlideInfo(
            slide_index=0,
            layout_type=SlideLayoutType.CONTENT_SLIDE,
            width=9144000,
            height=6858000,
            shapes=[],
            charts=[chart_info],
            tables=[],
            images=[],
            text_content="",
            color_palette=[],
            complexity_score=10
        )
        
        manifest = extractor._extract_element_manifest(slide_info)
        
        assert "charts" in manifest
        assert len(manifest["charts"]) == 1
        assert manifest["charts"][0]["chart_type"] == "bar"
        assert manifest["charts"][0]["title"] == "Sales Chart"
    
    def test_extract_element_manifest_with_table(self, extractor):
        """Test element manifest extraction with table."""
        table_info = TableInfo(
            rows=5,
            columns=3,
            has_header=True,
            cell_count=15,
            position=PositionInfo(100, 100, 800, 600)
        )
        
        slide_info = SlideInfo(
            slide_index=0,
            layout_type=SlideLayoutType.CONTENT_SLIDE,
            width=9144000,
            height=6858000,
            shapes=[],
            charts=[],
            tables=[table_info],
            images=[],
            text_content="",
            color_palette=[],
            complexity_score=8
        )
        
        manifest = extractor._extract_element_manifest(slide_info)
        
        assert "tables" in manifest
        assert len(manifest["tables"]) == 1
        assert manifest["tables"][0]["rows"] == 5
        assert manifest["tables"][0]["columns"] == 3
        assert manifest["tables"][0]["has_header"] is True
    
    def test_extract_element_manifest_with_image(self, extractor):
        """Test element manifest extraction with image."""
        image_info = ImageInfo(
            filename="chart.png",
            content_type="image/png",
            width=400,
            height=300,
            position=PositionInfo(100, 100, 400, 300)
        )
        
        slide_info = SlideInfo(
            slide_index=0,
            layout_type=SlideLayoutType.CONTENT_SLIDE,
            width=9144000,
            height=6858000,
            shapes=[],
            charts=[],
            tables=[],
            images=[image_info],
            text_content="",
            color_palette=[],
            complexity_score=7
        )
        
        manifest = extractor._extract_element_manifest(slide_info)
        
        assert "images" in manifest
        assert len(manifest["images"]) == 1
        assert manifest["images"][0]["filename"] == "chart.png"
        assert manifest["images"][0]["content_type"] == "image/png"
    
    def test_extract_placeholder_map_with_text(self, extractor, sample_slide_info):
        """Test placeholder map extraction with text content."""
        placeholder_map = extractor._extract_placeholder_map(sample_slide_info)
        
        assert len(placeholder_map) > 0
        assert placeholder_map[0]["field_type"] in ["title", "subtitle", "text", "number", "date"]
        assert "position_info" in placeholder_map[0]
        assert "is_required" in placeholder_map[0]
    
    def test_extract_placeholder_map_with_chart(self, extractor):
        """Test placeholder map extraction with chart."""
        chart_info = ChartInfo(
            chart_type=ChartType.BAR,
            title="Sales Chart",
            has_legend=True,
            data_series_count=2,
            category_count=4,
            position=PositionInfo(100, 100, 500, 300)
        )
        
        slide_info = SlideInfo(
            slide_index=0,
            layout_type=SlideLayoutType.CONTENT_SLIDE,
            width=9144000,
            height=6858000,
            shapes=[],
            charts=[chart_info],
            tables=[],
            images=[],
            text_content="",
            color_palette=[],
            complexity_score=10
        )
        
        placeholder_map = extractor._extract_placeholder_map(slide_info)
        
        chart_placeholders = [p for p in placeholder_map if p["field_type"] == "chart_data"]
        assert len(chart_placeholders) == 1
        assert chart_placeholders[0]["is_required"] is True
        assert "chart_metadata" in chart_placeholders[0]
    
    def test_extract_placeholder_map_with_table(self, extractor):
        """Test placeholder map extraction with table."""
        table_info = TableInfo(
            rows=5,
            columns=3,
            has_header=True,
            cell_count=15,
            position=PositionInfo(100, 100, 800, 600)
        )
        
        slide_info = SlideInfo(
            slide_index=0,
            layout_type=SlideLayoutType.CONTENT_SLIDE,
            width=9144000,
            height=6858000,
            shapes=[],
            charts=[],
            tables=[table_info],
            images=[],
            text_content="",
            color_palette=[],
            complexity_score=8
        )
        
        placeholder_map = extractor._extract_placeholder_map(slide_info)
        
        table_placeholders = [p for p in placeholder_map if p["field_type"] == "table_data"]
        assert len(table_placeholders) == 1
        assert table_placeholders[0]["is_required"] is True
        assert "table_metadata" in table_placeholders[0]
    
    def test_determine_text_placeholder_type_title(self, extractor):
        """Test text placeholder type determination for title."""
        placeholder_type = extractor._determine_text_placeholder_type("Main Title")
        
        assert placeholder_type == "title"
    
    def test_determine_text_placeholder_type_subtitle(self, extractor):
        """Test text placeholder type determination for subtitle."""
        placeholder_type = extractor._determine_text_placeholder_type("Subtitle Text")
        
        assert placeholder_type == "subtitle"
    
    def test_determine_text_placeholder_type_number(self, extractor):
        """Test text placeholder type determination for number."""
        placeholder_type = extractor._determine_text_placeholder_type("123.45")
        
        assert placeholder_type == "number"
    
    def test_determine_text_placeholder_type_date(self, extractor):
        """Test text placeholder type determination for date."""
        placeholder_type = extractor._determine_text_placeholder_type("Date: 2024-01-01")
        
        assert placeholder_type == "date"
    
    def test_determine_text_placeholder_type_text(self, extractor):
        """Test text placeholder type determination for regular text."""
        placeholder_type = extractor._determine_text_placeholder_type("Regular body text content")
        
        assert placeholder_type == "text"
    
    def test_generate_description(self, extractor, sample_slide_info):
        """Test description generation."""
        description = extractor._generate_description(sample_slide_info, SlideCategory.TITLE_SLIDE)
        
        assert isinstance(description, str)
        assert len(description) > 0
        assert "title slide" in description.lower()
    
    def test_generate_description_with_chart(self, extractor):
        """Test description generation for slide with chart."""
        chart_info = ChartInfo(
            chart_type=ChartType.BAR,
            title="Sales Chart",
            has_legend=True,
            data_series_count=2,
            category_count=4,
            position=PositionInfo(100, 100, 500, 300)
        )
        
        slide_info = SlideInfo(
            slide_index=0,
            layout_type=SlideLayoutType.CONTENT_SLIDE,
            width=9144000,
            height=6858000,
            shapes=[],
            charts=[chart_info],
            tables=[],
            images=[],
            text_content="",
            color_palette=["#FF0000", "#00FF00"],
            complexity_score=10
        )
        
        description = extractor._generate_description(slide_info, SlideCategory.DATA_CHART)
        
        assert "data chart" in description.lower()
        assert "1 chart" in description.lower()
    
    def test_calculate_template_hash(self, extractor, sample_slide_info):
        """Test template hash calculation."""
        hash_value = extractor.calculate_template_hash(sample_slide_info)
        
        assert isinstance(hash_value, str)
        assert len(hash_value) == 32  # MD5 hash length
    
    def test_calculate_template_hash_consistency(self, extractor, sample_slide_info):
        """Test that template hash is consistent for same structure."""
        hash1 = extractor.calculate_template_hash(sample_slide_info)
        hash2 = extractor.calculate_template_hash(sample_slide_info)
        
        assert hash1 == hash2
    
    def test_calculate_template_hash_different_structure(self, extractor):
        """Test that template hash differs for different structures."""
        slide_info1 = SlideInfo(
            slide_index=0,
            layout_type=SlideLayoutType.TITLE_SLIDE,
            width=9144000,
            height=6858000,
            shapes=[Mock()],
            charts=[],
            tables=[],
            images=[],
            text_content="",
            color_palette=[],
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
            text_content="",
            color_palette=[],
            complexity_score=8
        )
        
        hash1 = extractor.calculate_template_hash(slide_info1)
        hash2 = extractor.calculate_template_hash(slide_info2)
        
        assert hash1 != hash2
    
    def test_template_to_dict(self, extractor, sample_slide_info):
        """Test SlideTemplate to dictionary conversion."""
        template = extractor.extract_template(
            slide_info=sample_slide_info,
            collection_id="test_collection",
            original_filename="test.pptx"
        )
        
        template_dict = template.to_dict()
        
        assert isinstance(template_dict, dict)
        assert template_dict["template_id"] == template.template_id
        assert template_dict["collection_id"] == template.collection_id
        assert template_dict["classification"] == template.classification
        assert template_dict["tags"] == template.tags


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
