"""
Chart Generator for MySlides.
Handles programmatic creation of charts (FR-4.2).
"""
from typing import Dict, List, Optional
from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION
from pptx.util import Inches, Pt

from myslides.generation.generation_models import ChartData, ChartSubType


class ChartGenerator:
    """Generates PowerPoint charts from structured data."""
    
    def __init__(self, presentation: Presentation):
        """
        Initialize the chart generator.
        
        Args:
            presentation: pptx Presentation object
        """
        self.presentation = presentation
    
    def add_chart_to_slide(self, slide, chart_data: ChartData, 
                          left: float = 1.0, top: float = 1.5, 
                          width: float = 8.0, height: float = 4.5) -> None:
        """
        Add a chart to a slide.
        
        Args:
            slide: pptx slide object
            chart_data: ChartData object with chart configuration
            left: Left position in inches
            top: Top position in inches
            width: Width in inches
            height: Height in inches
        """
        chart_type = self._get_pptx_chart_type(chart_data.chart_type)
        
        # Create chart data
        data = CategoryChartData()
        
        # Add categories
        data.categories = chart_data.categories
        
        # Add series
        for series_name, values in chart_data.series_data.items():
            data.add_series(series_name, values)
        
        # Add chart to slide
        chart = slide.shapes.add_chart(
            chart_type,
            Inches(left),
            Inches(top),
            Inches(width),
            Inches(height),
            data
        ).chart
        
        # Set chart title
        if chart_data.title:
            chart.has_title = True
            chart.chart_title.text_frame.text = chart_data.title
        
        # Configure legend
        if chart_data.has_legend:
            chart.has_legend = True
            chart.legend.position = XL_LEGEND_POSITION.RIGHT
        else:
            chart.has_legend = False
        
        # Configure data labels
        if chart_data.show_data_labels:
            for plot in chart.plots:
                plot.has_data_labels = True
                data_labels = plot.data_labels
                if data_labels:
                    data_labels.show_value = True
    
    def _get_pptx_chart_type(self, chart_sub_type: ChartSubType) -> XL_CHART_TYPE:
        """
        Convert ChartSubType to pptx XL_CHART_TYPE.

        Args:
            chart_sub_type: ChartSubType enum value

        Returns:
            XL_CHART_TYPE enum value
        """
        type_mapping = {
            ChartSubType.BAR_VERTICAL: XL_CHART_TYPE.COLUMN_CLUSTERED,
            ChartSubType.BAR_HORIZONTAL: XL_CHART_TYPE.BAR_CLUSTERED,
            ChartSubType.BAR_STACKED: XL_CHART_TYPE.COLUMN_STACKED,
            ChartSubType.BAR_GROUPED: XL_CHART_TYPE.COLUMN_CLUSTERED,
            ChartSubType.LINE_SINGLE: XL_CHART_TYPE.LINE,
            ChartSubType.LINE_MULTI: XL_CHART_TYPE.LINE,
            ChartSubType.PIE: XL_CHART_TYPE.PIE,
            ChartSubType.DONUT: XL_CHART_TYPE.DOUGHNUT,
            ChartSubType.AREA: XL_CHART_TYPE.AREA,
            ChartSubType.AREA_STACKED: XL_CHART_TYPE.AREA_STACKED,
            ChartSubType.SCATTER: XL_CHART_TYPE.XY_SCATTER,
            ChartSubType.COMBO: XL_CHART_TYPE.COLUMN_CLUSTERED,
            ChartSubType.WATERFALL: XL_CHART_TYPE.COLUMN_STACKED
        }

        return type_mapping.get(chart_sub_type, XL_CHART_TYPE.COLUMN_CLUSTERED)
    
    def create_bar_chart(self, slide, title: str, categories: List[str], 
                        series_data: Dict[str, List[float]], 
                        horizontal: bool = False, stacked: bool = False) -> None:
        """
        Create a bar chart (convenience method).
        
        Args:
            slide: pptx slide object
            title: Chart title
            categories: List of category labels
            series_data: Dictionary mapping series names to value lists
            horizontal: Whether to use horizontal bars
            stacked: Whether to stack bars
        """
        chart_type = ChartSubType.BAR_HORIZONTAL if horizontal else ChartSubType.BAR_VERTICAL
        if stacked:
            chart_type = ChartSubType.BAR_STACKED
        
        chart_data = ChartData(
            chart_type=chart_type,
            title=title,
            categories=categories,
            series_data=series_data,
            has_legend=True
        )
        
        self.add_chart_to_slide(slide, chart_data)
    
    def create_line_chart(self, slide, title: str, categories: List[str], 
                         series_data: Dict[str, List[float]]) -> None:
        """
        Create a line chart (convenience method).
        
        Args:
            slide: pptx slide object
            title: Chart title
            categories: List of category labels (x-axis)
            series_data: Dictionary mapping series names to value lists
        """
        chart_type = ChartSubType.LINE_MULTI if len(series_data) > 1 else ChartSubType.LINE_SINGLE
        
        chart_data = ChartData(
            chart_type=chart_type,
            title=title,
            categories=categories,
            series_data=series_data,
            has_legend=True
        )
        
        self.add_chart_to_slide(slide, chart_data)
    
    def create_pie_chart(self, slide, title: str, categories: List[str], 
                        values: List[float]) -> None:
        """
        Create a pie chart (convenience method).
        
        Args:
            slide: pptx slide object
            title: Chart title
            categories: List of category labels (slice labels)
            values: List of values for each slice
        """
        chart_data = ChartData(
            chart_type=ChartSubType.PIE,
            title=title,
            categories=categories,
            series_data={"Series 1": values},
            has_legend=True
        )

        self.add_chart_to_slide(slide, chart_data)

    def create_combo_chart(self, slide, title: str, categories: List[str],
                          primary_series: Dict[str, List[float]],
                          secondary_series: Dict[str, List[float]]) -> None:
        """
        Create a combo chart (bar + line overlay) (FR-4.2 Phase 2).

        Args:
            slide: pptx slide object
            title: Chart title
            categories: List of category labels
            primary_series: Dictionary for bar series
            secondary_series: Dictionary for line series
        """
        chart_data = ChartData(
            chart_type=ChartSubType.COMBO,
            title=title,
            categories=categories,
            series_data={**primary_series, **secondary_series},
            has_legend=True
        )

        self.add_chart_to_slide(slide, chart_data)

    def create_waterfall_chart(self, slide, title: str, categories: List[str],
                             values: List[float]) -> None:
        """
        Create a waterfall chart (variance analysis) (FR-4.2 Phase 2).

        Args:
            slide: pptx slide object
            title: Chart title
            categories: List of category labels
            values: List of values (positive/negative for up/down)
        """
        chart_data = ChartData(
            chart_type=ChartSubType.WATERFALL,
            title=title,
            categories=categories,
            series_data={"Values": values},
            has_legend=False
        )

        self.add_chart_to_slide(slide, chart_data)

    def create_stacked_area_chart(self, slide, title: str, categories: List[str],
                                  series_data: Dict[str, List[float]]) -> None:
        """
        Create a stacked area chart (FR-4.2 Phase 2).

        Args:
            slide: pptx slide object
            title: Chart title
            categories: List of category labels
            series_data: Dictionary mapping series names to value lists
        """
        chart_data = ChartData(
            chart_type=ChartSubType.AREA_STACKED,
            title=title,
            categories=categories,
            series_data=series_data,
            has_legend=True
        )

        self.add_chart_to_slide(slide, chart_data)
