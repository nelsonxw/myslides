"""
PPTX Parser for MySlides.
Extracts comprehensive information from PowerPoint slides including shapes, charts, images, text, and styling.
"""
import json
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
from typing import Any, Optional, List

from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE
from pptx.util import Inches, Pt, Emu


class SlideLayoutType(Enum):
    """Enumeration of common slide layout types."""
    TITLE_SLIDE = "title_slide"
    CONTENT_SLIDE = "content_slide"
    SECTION_HEADER = "section_header"
    BLANK = "blank"
    TWO_CONTENT = "two_content"
    COMPARISON = "comparison"
    TITLE_ONLY = "title_only"


class ChartType(Enum):
    """Enumeration of PowerPoint chart types."""
    BAR = "bar"
    LINE = "line"
    PIE = "pie"
    AREA = "area"
    SCATTER = "scatter"
    COMBO = "combo"
    WATERFALL = "waterfall"
    FUNNEL = "funnel"
    DOUGHNUT = "doughnut"
    RADAR = "radar"
    UNKNOWN = "unknown"


@dataclass
class ColorInfo:
    """Information about a color."""
    hex_value: str
    rgb: tuple[int, int, int]
    brightness: float
    
    @classmethod
    def from_color_format(cls, color_format) -> Optional["ColorInfo"]:
        """Create ColorInfo from pptx color format."""
        if color_format is None or color_format.type == 0:  # No color
            return None
        
        try:
            rgb = color_format.rgb
            if rgb:
                hex_value = f"#{rgb:06x}"
                r = (rgb >> 16) & 0xFF
                g = (rgb >> 8) & 0xFF
                b = rgb & 0xFF
                brightness = (0.299 * r + 0.587 * g + 0.114 * b) / 255
                return cls(hex_value=hex_value, rgb=(r, g, b), brightness=brightness)
        except Exception:
            pass
        
        return None


@dataclass
class FontInfo:
    """Information about font styling."""
    name: str
    size: float
    bold: bool
    italic: bool
    underline: bool
    color: Optional[ColorInfo]
    
    @classmethod
    def from_font(cls, font) -> "FontInfo":
        """Create FontInfo from pptx font object."""
        return cls(
            name=font.name or "Calibri",
            size=font.size.pt if font.size else 11.0,
            bold=font.bold,
            italic=font.italic,
            underline=font.underline,
            color=ColorInfo.from_color_format(font.color)
        )


@dataclass
class PositionInfo:
    """Position and size information in EMUs."""
    x: int
    y: int
    width: int
    height: int
    
    @classmethod
    def from_shape(cls, shape) -> "PositionInfo":
        """Create PositionInfo from pptx shape."""
        return cls(
            x=shape.left,
            y=shape.top,
            width=shape.width,
            height=shape.height
        )


@dataclass
class TextContent:
    """Text content with styling information."""
    text: str
    font: FontInfo
    paragraphs: List[str]
    
    @classmethod
    def from_text_frame(cls, text_frame) -> "TextContent":
        """Create TextContent from pptx text frame."""
        paragraphs = []
        full_text = ""
        
        for paragraph in text_frame.paragraphs:
            para_text = paragraph.text.strip()
            if para_text:
                paragraphs.append(para_text)
                full_text += para_text + "\n"
        
        # Get font info from first run with font properties
        font_info = FontInfo(name="Calibri", size=11.0, bold=False, italic=False, underline=False, color=None)
        if text_frame.paragraphs:
            for paragraph in text_frame.paragraphs:
                if paragraph.runs:
                    first_run = paragraph.runs[0]
                    if first_run.font.name or first_run.font.size:
                        font_info = FontInfo.from_font(first_run.font)
                        break
        
        return cls(
            text=full_text.strip(),
            font=font_info,
            paragraphs=paragraphs
        )


@dataclass
class ShapeInfo:
    """Information about a shape on a slide."""
    shape_id: int
    shape_type: str
    name: str
    position: PositionInfo
    fill_color: Optional[ColorInfo]
    line_color: Optional[ColorInfo]
    text_content: Optional[TextContent]
    is_grouped: bool
    group_id: Optional[int]
    
    @classmethod
    def from_shape(cls, shape) -> "ShapeInfo":
        """Create ShapeInfo from pptx shape."""
        shape_type_str = str(shape.shape_type)
        
        # Determine shape type
        if hasattr(shape, 'chart'):
            shape_type_str = "chart"
        elif hasattr(shape, 'table'):
            shape_type_str = "table"
        elif hasattr(shape, 'picture'):
            shape_type_str = "picture"
        elif shape.shape_type == MSO_SHAPE_TYPE.GROUP:
            shape_type_str = "group"
        
        # Extract text content if present
        text_content = None
        if hasattr(shape, 'text_frame') and shape.text_frame:
            try:
                text_content = TextContent.from_text_frame(shape.text_frame)
            except Exception:
                text_content = None
        
        # Extract fill color with error handling
        fill_color = None
        try:
            if hasattr(shape, 'fill') and hasattr(shape.fill, 'foreground_color'):
                fill_color = ColorInfo.from_color_format(shape.fill.foreground_color)
        except Exception:
            fill_color = None
        
        # Extract line color with error handling
        line_color = None
        try:
            if hasattr(shape, 'line') and hasattr(shape.line, 'color'):
                line_color = ColorInfo.from_color_format(shape.line.color)
        except Exception:
            line_color = None
        
        return cls(
            shape_id=shape.shape_id,
            shape_type=shape_type_str,
            name=shape.name or f"Shape_{shape.shape_id}",
            position=PositionInfo.from_shape(shape),
            fill_color=fill_color,
            line_color=line_color,
            text_content=text_content,
            is_grouped=shape.shape_type == MSO_SHAPE_TYPE.GROUP,
            group_id=None  # Would need parent tracking
        )


@dataclass
class ChartInfo:
    """Information about a chart on a slide."""
    chart_type: ChartType
    title: str
    has_legend: bool
    data_series_count: int
    category_count: int
    position: PositionInfo
    
    @classmethod
    def from_chart(cls, chart) -> "ChartInfo":
        """Create ChartInfo from pptx chart."""
        # Determine chart type
        chart_type = ChartType.UNKNOWN
        try:
            if hasattr(chart, 'chart_type'):
                chart_type_str = str(chart.chart_type).lower()
                if 'bar' in chart_type_str:
                    chart_type = ChartType.BAR
                elif 'line' in chart_type_str:
                    chart_type = ChartType.LINE
                elif 'pie' in chart_type_str:
                    chart_type = ChartType.PIE
                elif 'area' in chart_type_str:
                    chart_type = ChartType.AREA
                elif 'scatter' in chart_type_str:
                    chart_type = ChartType.SCATTER
                elif 'doughnut' in chart_type_str:
                    chart_type = ChartType.DOUGHNUT
                elif 'radar' in chart_type_str:
                    chart_type = ChartType.RADAR
        except Exception:
            pass
        
        # Get chart title
        title = ""
        try:
            if hasattr(chart, 'chart_title') and chart.chart_title:
                if hasattr(chart.chart_title, 'text_frame') and chart.chart_title.text_frame:
                    title = chart.chart_title.text_frame.text
        except Exception:
            pass
        
        # Count series and categories
        series_count = 0
        category_count = 0
        try:
            if hasattr(chart, 'series'):
                series_count = len(list(chart.series))
            if hasattr(chart, 'categories'):
                category_count = len(list(chart.categories))
        except Exception:
            pass
        
        # Get has_legend with error handling
        has_legend = False
        try:
            if hasattr(chart, 'has_legend'):
                has_legend = chart.has_legend
        except Exception:
            pass
        
        return cls(
            chart_type=chart_type,
            title=title,
            has_legend=has_legend,
            data_series_count=series_count,
            category_count=category_count,
            position=PositionInfo.from_shape(chart)
        )


@dataclass
class TableInfo:
    """Information about a table on a slide."""
    rows: int
    columns: int
    has_header: bool
    cell_count: int
    position: PositionInfo
    
    @classmethod
    def from_table(cls, table) -> "TableInfo":
        """Create TableInfo from pptx table."""
        rows = len(table.rows)
        columns = len(table.columns)
        
        # Check if first row looks like a header
        has_header = False
        if rows > 0:
            first_row = table.rows[0]
            has_header = any(cell.text.strip() for cell in first_row.cells)
        
        return cls(
            rows=rows,
            columns=columns,
            has_header=has_header,
            cell_count=rows * columns,
            position=PositionInfo.from_shape(table)
        )


@dataclass
class ImageInfo:
    """Information about an image on a slide."""
    filename: str
    content_type: str
    width: int
    height: int
    position: PositionInfo
    
    @classmethod
    def from_picture(cls, picture) -> "ImageInfo":
        """Create ImageInfo from pptx picture."""
        filename = "unknown"
        content_type = "unknown"
        
        try:
            if hasattr(picture, 'image'):
                image_data = picture.image
                if hasattr(image_data, 'filename'):
                    filename = image_data.filename
                if hasattr(image_data, 'content_type'):
                    content_type = image_data.content_type
        except Exception:
            pass
        
        return cls(
            filename=filename,
            content_type=content_type,
            width=picture.width,
            height=picture.height,
            position=PositionInfo.from_shape(picture)
        )


@dataclass
class SlideInfo:
    """Comprehensive information about a single slide."""
    slide_index: int
    layout_type: SlideLayoutType
    width: int
    height: int
    shapes: List[ShapeInfo]
    charts: List[ChartInfo]
    tables: List[TableInfo]
    images: List[ImageInfo]
    text_content: str
    color_palette: List[str]
    complexity_score: int
    
    def to_dict(self) -> dict[str, Any]:
        """Convert SlideInfo to dictionary for JSON serialization."""
        return {
            "slide_index": self.slide_index,
            "layout_type": self.layout_type.value,
            "width": self.width,
            "height": self.height,
            "shapes": [asdict(shape) for shape in self.shapes],
            "charts": [asdict(chart) for chart in self.charts],
            "tables": [asdict(table) for table in self.tables],
            "images": [asdict(image) for image in self.images],
            "text_content": self.text_content,
            "color_palette": self.color_palette,
            "complexity_score": self.complexity_score
        }


class PPTXParser:
    """Parser for extracting comprehensive information from individual PPTX slide files."""
    
    def __init__(self, pptx_path: Path | str):
        """
        Initialize PPTX parser for individual slide file.
        
        Args:
            pptx_path: Path to the individual PPTX slide file
        """
        self.pptx_path = Path(pptx_path)
        if not self.pptx_path.exists():
            raise FileNotFoundError(f"PPTX file not found: {pptx_path}")
        
        self.presentation = Presentation(str(self.pptx_path))
    
    def parse_slide(self, slide_index: int = 0) -> SlideInfo:
        """
        Parse the single slide in the PPTX file.
        
        Args:
            slide_index: Index for the slide (default 0 for individual slides)
        
        Returns:
            SlideInfo object with comprehensive slide information
        """
        # Get the first (and only) slide from the presentation
        if len(self.presentation.slides) == 0:
            raise ValueError("No slides found in the PPTX file")
        
        slide = self.presentation.slides[0]
        
        # Get slide dimensions
        width = self.presentation.slide_width
        height = self.presentation.slide_height
        
        # Determine layout type
        layout_type = self._determine_layout_type(slide)
        
        # Extract shapes
        shapes = []
        charts = []
        tables = []
        images = []
        all_text = []
        color_palette = set()
        
        for shape in slide.shapes:
            try:
                # Extract basic shape info
                shape_info = ShapeInfo.from_shape(shape)
                shapes.append(shape_info)
                
                # Extract color information
                if shape_info.fill_color:
                    color_palette.add(shape_info.fill_color.hex_value)
                if shape_info.line_color:
                    color_palette.add(shape_info.line_color.hex_value)
                
                # Extract text content
                if shape_info.text_content:
                    all_text.append(shape_info.text_content.text)
                
                # Extract specific types
                if hasattr(shape, 'chart') and shape.chart:
                    try:
                        chart_info = ChartInfo.from_chart(shape.chart)
                        charts.append(chart_info)
                    except Exception:
                        pass
                
                if hasattr(shape, 'table') and shape.table:
                    try:
                        table_info = TableInfo.from_table(shape.table)
                        tables.append(table_info)
                    except Exception:
                        pass
                
                if hasattr(shape, 'image'):
                    try:
                        image_info = ImageInfo.from_picture(shape)
                        images.append(image_info)
                    except Exception:
                        pass
            except Exception as e:
                print(f"Error processing shape {shape.shape_id}: {e}")
                continue
        
        # Calculate complexity score
        complexity_score = self._calculate_complexity(shapes, charts, tables, images)
        
        return SlideInfo(
            slide_index=slide_index,
            layout_type=layout_type,
            width=width,
            height=height,
            shapes=shapes,
            charts=charts,
            tables=tables,
            images=images,
            text_content="\n".join(all_text),
            color_palette=list(color_palette),
            complexity_score=complexity_score
        )
    
    def _determine_layout_type(self, slide) -> SlideLayoutType:
        """
        Determine the layout type of a slide based on its content.
        
        Args:
            slide: pptx slide object
        
        Returns:
            SlideLayoutType enum value
        """
        shape_count = len(slide.shapes)
        text_shapes = 0
        has_title = False
        
        for shape in slide.shapes:
            if hasattr(shape, 'text_frame') and shape.text_frame:
                if shape.text_frame.text.strip():
                    text_shapes += 1
                    # Check if this looks like a title (large font, centered)
                    if shape.text_frame.paragraphs:
                        first_para = shape.text_frame.paragraphs[0]
                        if first_para.runs:
                            first_run = first_para.runs[0]
                            if first_run.font.size and first_run.font.size.pt > 20:
                                has_title = True
        
        # Heuristic layout determination
        if shape_count <= 2 and has_title:
            return SlideLayoutType.TITLE_SLIDE
        elif shape_count == 1 and not has_title:
            return SlideLayoutType.BLANK
        elif has_title and text_shapes == 1:
            return SlideLayoutType.TITLE_ONLY
        elif has_title and text_shapes == 2:
            return SlideLayoutType.TWO_CONTENT
        elif has_title and text_shapes > 2:
            return SlideLayoutType.CONTENT_SLIDE
        elif not has_title and text_shapes > 0:
            return SlideLayoutType.SECTION_HEADER
        else:
            return SlideLayoutType.CONTENT_SLIDE
    
    def _calculate_complexity(self, shapes: List[ShapeInfo], charts: List[ChartInfo], 
                            tables: List[TableInfo], images: List[ImageInfo]) -> int:
        """
        Calculate a complexity score for the slide.
        
        Args:
            shapes: List of shapes on the slide
            charts: List of charts on the slide
            tables: List of tables on the slide
            images: List of images on the slide
        
        Returns:
            Complexity score (higher = more complex)
        """
        score = 0
        
        # Base score for number of elements
        score += len(shapes) * 1
        score += len(charts) * 5
        score += len(tables) * 3
        score += len(images) * 2
        
        # Additional complexity for grouped shapes
        grouped_shapes = [s for s in shapes if s.is_grouped]
        score += len(grouped_shapes) * 2
        
        # Additional complexity for text content
        total_text_length = sum(len(s.text_content.text) if s.text_content else 0 for s in shapes)
        score += min(total_text_length // 100, 10)
        
        return score
    
    def get_presentation_metadata(self) -> dict[str, Any]:
        """
        Get metadata about the individual slide file.
        
        Returns:
            Dictionary with slide file metadata
        """
        return {
            "file_path": str(self.pptx_path),
            "file_name": self.pptx_path.name,
            "slide_count": 1,  # Individual slides always have 1 slide
            "width": self.presentation.slide_width,
            "height": self.presentation.slide_height,
        }
