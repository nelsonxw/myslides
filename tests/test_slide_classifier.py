"""
Tests for Slide Classifier module.
"""
import pytest
from unittest.mock import Mock

from myslides.ingestion.slide_classifier import (
    SlideClassifier, 
    SlideCategory
)
from myslides.ingestion.pptx_parser import (
    SlideInfo, 
    SlideLayoutType, 
    ChartType,
    ShapeInfo,
    ChartInfo,
    TableInfo,
    ImageInfo,
    PositionInfo
)


class TestSlideClassifier:
    """Tests for SlideClassifier class."""
    
    @pytest.fixture
    def classifier(self):
        """Create a SlideClassifier instance."""
        return SlideClassifier()
    
    @pytest.fixture
    def basic_slide_info(self):
        """Create a basic SlideInfo for testing."""
        return SlideInfo(
            slide_index=0,
            layout_type=SlideLayoutType.CONTENT_SLIDE,
            width=9144000,
            height=6858000,
            shapes=[],
            charts=[],
            tables=[],
            images=[],
            text_content="Test content",
            color_palette=["#FF0000"],
            complexity_score=5
        )
    
    def test_classify_title_slide(self, classifier, basic_slide_info):
        """Test classification of title slide."""
        basic_slide_info.layout_type = SlideLayoutType.TITLE_SLIDE
        basic_slide_info.text_content = "Main Title"
        
        category = classifier.classify(basic_slide_info)
        
        assert category == SlideCategory.TITLE_SLIDE
    
    def test_classify_agenda_slide(self, classifier, basic_slide_info):
        """Test classification of agenda slide."""
        basic_slide_info.text_content = "Agenda: Overview, Topics, Schedule"
        
        category = classifier.classify(basic_slide_info)
        
        assert category == SlideCategory.AGENDA
    
    def test_classify_data_chart_slide(self, classifier, basic_slide_info):
        """Test classification of data chart slide."""
        chart_info = ChartInfo(
            chart_type=ChartType.BAR,
            title="Sales Data",
            has_legend=True,
            data_series_count=2,
            category_count=4,
            position=PositionInfo(100, 100, 500, 300)
        )
        basic_slide_info.charts = [chart_info]
        
        category = classifier.classify(basic_slide_info)
        
        assert category == SlideCategory.DATA_CHART
    
    def test_classify_dashboard_slide(self, classifier, basic_slide_info):
        """Test classification of dashboard slide with multiple charts."""
        chart_info1 = ChartInfo(
            chart_type=ChartType.BAR,
            title="Sales Data",
            has_legend=True,
            data_series_count=2,
            category_count=4,
            position=PositionInfo(100, 100, 500, 300)
        )
        chart_info2 = ChartInfo(
            chart_type=ChartType.LINE,
            title="Trend Data",
            has_legend=True,
            data_series_count=1,
            category_count=12,
            position=PositionInfo(100, 400, 500, 300)
        )
        chart_info3 = ChartInfo(
            chart_type=ChartType.PIE,
            title="Distribution",
            has_legend=True,
            data_series_count=1,
            category_count=5,
            position=PositionInfo(600, 100, 300, 300)
        )
        basic_slide_info.charts = [chart_info1, chart_info2, chart_info3]
        
        category = classifier.classify(basic_slide_info)
        
        assert category == SlideCategory.DASHBOARD
    
    def test_classify_table_view_slide(self, classifier, basic_slide_info):
        """Test classification of table view slide."""
        table_info = TableInfo(
            rows=10,
            columns=5,
            has_header=True,
            cell_count=50,
            position=PositionInfo(100, 100, 800, 600)
        )
        basic_slide_info.tables = [table_info]
        
        category = classifier.classify(basic_slide_info)
        
        assert category == SlideCategory.TABLE_VIEW
    
    def test_classify_image_showcase_slide(self, classifier, basic_slide_info):
        """Test classification of image showcase slide."""
        image_info1 = ImageInfo(
            filename="image1.png",
            content_type="image/png",
            width=400,
            height=300,
            position=PositionInfo(100, 100, 400, 300)
        )
        image_info2 = ImageInfo(
            filename="image2.png",
            content_type="image/png",
            width=400,
            height=300,
            position=PositionInfo(500, 100, 400, 300)
        )
        image_info3 = ImageInfo(
            filename="image3.png",
            content_type="image/png",
            width=400,
            height=300,
            position=PositionInfo(100, 400, 400, 300)
        )
        basic_slide_info.images = [image_info1, image_info2, image_info3]
        
        category = classifier.classify(basic_slide_info)
        
        assert category == SlideCategory.IMAGE_SHOWCASE
    
    def test_classify_process_flow_slide(self, classifier, basic_slide_info):
        """Test classification of process flow slide."""
        basic_slide_info.text_content = "Step 1: Application, Step 2: Review, Step 3: Approval"
        
        category = classifier.classify(basic_slide_info)
        
        assert category == SlideCategory.PROCESS_FLOW
    
    def test_classify_timeline_slide(self, classifier, basic_slide_info):
        """Test classification of timeline slide."""
        basic_slide_info.text_content = "Timeline: Q1 2024, Q2 2024, Q3 2024, Q4 2024"
        
        category = classifier.classify(basic_slide_info)
        
        assert category == SlideCategory.TIMELINE
    
    def test_classify_comparison_slide(self, classifier, basic_slide_info):
        """Test classification of comparison slide."""
        basic_slide_info.text_content = "Plan A vs Plan B comparison"
        
        category = classifier.classify(basic_slide_info)
        
        assert category == SlideCategory.COMPARISON
    
    def test_classify_text_heavy_slide(self, classifier, basic_slide_info):
        """Test classification of text-heavy slide."""
        long_text = "Lorem ipsum " * 50  # Create long text
        basic_slide_info.text_content = long_text
        
        category = classifier.classify(basic_slide_info)
        
        assert category == SlideCategory.TEXT_HEAVY
    
    def test_classify_mixed_slide(self, classifier, basic_slide_info):
        """Test classification of mixed content slide."""
        basic_slide_info.text_content = "Some content with various elements"
        basic_slide_info.shapes = [Mock() for _ in range(3)]
        
        category = classifier.classify(basic_slide_info)
        
        assert category == SlideCategory.MIXED
    
    def test_get_tags(self, classifier, basic_slide_info):
        """Test tag generation for slide."""
        basic_slide_info.text_content = "Agenda: Topics and Schedule"
        basic_slide_info.complexity_score = 3
        
        tags = classifier.get_tags(basic_slide_info)
        
        assert "agenda" in tags
        assert "layout_content_slide" in tags
        assert "simple" in tags
    
    def test_get_tags_with_chart(self, classifier, basic_slide_info):
        """Test tag generation for slide with chart."""
        chart_info = ChartInfo(
            chart_type=ChartType.BAR,
            title="Sales Data",
            has_legend=True,
            data_series_count=2,
            category_count=4,
            position=PositionInfo(100, 100, 500, 300)
        )
        basic_slide_info.charts = [chart_info]
        
        tags = classifier.get_tags(basic_slide_info)
        
        assert "has_chart" in tags
        assert "chart_bar" in tags
    
    def test_get_tags_with_table(self, classifier, basic_slide_info):
        """Test tag generation for slide with table."""
        table_info = TableInfo(
            rows=5,
            columns=3,
            has_header=True,
            cell_count=15,
            position=PositionInfo(100, 100, 800, 600)
        )
        basic_slide_info.tables = [table_info]
        
        tags = classifier.get_tags(basic_slide_info)
        
        assert "has_table" in tags
    
    def test_get_tags_with_image(self, classifier, basic_slide_info):
        """Test tag generation for slide with image."""
        image_info = ImageInfo(
            filename="image.png",
            content_type="image/png",
            width=400,
            height=300,
            position=PositionInfo(100, 100, 400, 300)
        )
        basic_slide_info.images = [image_info]
        
        tags = classifier.get_tags(basic_slide_info)
        
        assert "has_image" in tags
    
    def test_is_process_flow_layout_horizontal(self, classifier):
        """Test process flow layout detection for horizontal arrangement."""
        slide_info = SlideInfo(
            slide_index=0,
            layout_type=SlideLayoutType.CONTENT_SLIDE,
            width=9144000,
            height=6858000,
            shapes=[],
            charts=[],
            tables=[],
            images=[],
            text_content="",
            color_palette=[],
            complexity_score=5
        )
        
        # Create shapes arranged horizontally
        for i in range(4):
            shape = Mock()
            shape.shape_type = "rectangle"
            shape.position = PositionInfo(100 + i * 200, 100, 150, 100)  # Similar Y positions
            shape.is_grouped = False
            slide_info.shapes.append(shape)
        
        is_process_flow = classifier._is_process_flow_layout(slide_info)
        
        assert is_process_flow is True
    
    def test_is_process_flow_layout_vertical(self, classifier):
        """Test process flow layout detection for vertical arrangement."""
        slide_info = SlideInfo(
            slide_index=0,
            layout_type=SlideLayoutType.CONTENT_SLIDE,
            width=9144000,
            height=6858000,
            shapes=[],
            charts=[],
            tables=[],
            images=[],
            text_content="",
            color_palette=[],
            complexity_score=5
        )
        
        # Create shapes arranged vertically
        for i in range(4):
            shape = Mock()
            shape.shape_type = "rectangle"
            shape.position = PositionInfo(100, 100 + i * 200, 150, 100)  # Different Y positions
            shape.is_grouped = False
            slide_info.shapes.append(shape)
        
        is_process_flow = classifier._is_process_flow_layout(slide_info)
        
        assert is_process_flow is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
