"""
Template Extractor for MySlides.
Extracts and stores slide templates with comprehensive metadata.
"""
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Optional
from datetime import datetime

from myslides.ingestion.pptx_parser import SlideInfo, ShapeInfo, ChartInfo, TableInfo, ImageInfo
from myslides.ingestion.slide_classifier import SlideClassifier, SlideCategory


@dataclass
class PlaceholderMap:
    """Maps placeholder fields in a template to their types and positions."""
    field_name: str
    field_type: str  # "text", "number", "date", "image", "chart_data"
    position_info: dict[str, Any]
    is_required: bool


@dataclass
class SlideTemplate:
    """Comprehensive template record for a cataloged slide."""
    template_id: str
    collection_id: str
    slide_index: int
    classification: str
    tags: list[str]
    thumbnail_path: Optional[str]
    element_manifest: dict[str, Any]
    placeholder_map: list[dict[str, Any]]
    color_palette: list[str]
    complexity_score: int
    description: str
    created_at: str
    
    def to_dict(self) -> dict[str, Any]:
        """Convert SlideTemplate to dictionary for JSON serialization."""
        return asdict(self)


class TemplateExtractor:
    """Extracts and formats slide templates from parsed slide information."""
    
    def __init__(self):
        self.classifier = SlideClassifier()
    
    def extract_template(
        self,
        slide_info: SlideInfo,
        collection_id: str,
        original_filename: str,
        thumbnail_path: Optional[str] = None
    ) -> SlideTemplate:
        """
        Extract a template from parsed slide information.
        
        Args:
            slide_info: Parsed slide information
            collection_id: ID of the slide collection
            original_filename: Original PPTX filename
            thumbnail_path: Path to thumbnail image (optional)
        
        Returns:
            SlideTemplate object
        """
        # Classify the slide
        classification = self.classifier.classify(slide_info)
        tags = self.classifier.get_tags(slide_info)
        
        # Generate template ID
        template_id = f"{collection_id}_slide_{slide_info.slide_index}"
        
        # Extract element manifest
        element_manifest = self._extract_element_manifest(slide_info)
        
        # Extract placeholder map
        placeholder_map = self._extract_placeholder_map(slide_info)
        
        # Generate description
        description = self._generate_description(slide_info, classification)
        
        # Get color palette
        color_palette = slide_info.color_palette
        
        return SlideTemplate(
            template_id=template_id,
            collection_id=collection_id,
            slide_index=slide_info.slide_index,
            classification=classification.value,
            tags=tags,
            thumbnail_path=thumbnail_path,
            element_manifest=element_manifest,
            placeholder_map=placeholder_map,
            color_palette=color_palette,
            complexity_score=slide_info.complexity_score,
            description=description,
            created_at=datetime.now().isoformat()
        )
    
    def _extract_element_manifest(self, slide_info: SlideInfo) -> dict[str, Any]:
        """
        Extract structured manifest of all elements on the slide.
        
        Args:
            slide_info: Parsed slide information
        
        Returns:
            Dictionary with element manifest
        """
        manifest = {
            "slide_dimensions": {
                "width": slide_info.width,
                "height": slide_info.height
            },
            "shapes": [],
            "charts": [],
            "tables": [],
            "images": [],
            "groupings": []
        }
        
        # Extract shapes
        for shape in slide_info.shapes:
            shape_data = {
                "shape_id": shape.shape_id,
                "shape_type": shape.shape_type,
                "name": shape.name,
                "position": {
                    "x": shape.position.x,
                    "y": shape.position.y,
                    "width": shape.position.width,
                    "height": shape.position.height
                },
                "fill_color": shape.fill_color.hex_value if shape.fill_color else None,
                "line_color": shape.line_color.hex_value if shape.line_color else None,
                "has_text": shape.text_content is not None,
                "is_grouped": shape.is_grouped
            }
            
            if shape.text_content:
                shape_data["text"] = {
                    "content": shape.text_content.text,
                    "font": {
                        "name": shape.text_content.font.name,
                        "size": shape.text_content.font.size,
                        "bold": shape.text_content.font.bold,
                        "italic": shape.text_content.font.italic
                    }
                }
            
            manifest["shapes"].append(shape_data)
        
        # Extract charts
        for chart in slide_info.charts:
            chart_data = {
                "chart_type": chart.chart_type.value,
                "title": chart.title,
                "has_legend": chart.has_legend,
                "data_series_count": chart.data_series_count,
                "category_count": chart.category_count,
                "position": {
                    "x": chart.position.x,
                    "y": chart.position.y,
                    "width": chart.position.width,
                    "height": chart.position.height
                }
            }
            manifest["charts"].append(chart_data)
        
        # Extract tables
        for table in slide_info.tables:
            table_data = {
                "rows": table.rows,
                "columns": table.columns,
                "has_header": table.has_header,
                "cell_count": table.cell_count,
                "position": {
                    "x": table.position.x,
                    "y": table.position.y,
                    "width": table.position.width,
                    "height": table.position.height
                }
            }
            manifest["tables"].append(table_data)
        
        # Extract images
        for image in slide_info.images:
            image_data = {
                "filename": image.filename,
                "content_type": image.content_type,
                "width": image.width,
                "height": image.height,
                "position": {
                    "x": image.position.x,
                    "y": image.position.y,
                    "width": image.position.width,
                    "height": image.position.height
                }
            }
            manifest["images"].append(image_data)
        
        return manifest
    
    def _extract_placeholder_map(self, slide_info: SlideInfo) -> list[dict[str, Any]]:
        """
        Extract placeholder fields from the slide.
        
        Args:
            slide_info: Parsed slide information
        
        Returns:
            List of placeholder mappings
        """
        placeholders = []
        
        # Extract text placeholders
        for shape in slide_info.shapes:
            if shape.text_content and shape.text_content.text.strip():
                # Determine if this is a variable field or decorative text
                text = shape.text_content.text.strip()
                
                # Simple heuristic: short text in specific positions are likely placeholders
                if len(text) < 50 and shape.text_content.font.size > 12:
                    placeholder_type = self._determine_text_placeholder_type(text)
                    
                    placeholders.append({
                        "field_name": f"text_{shape.shape_id}",
                        "field_type": placeholder_type,
                        "position_info": {
                            "x": shape.position.x,
                            "y": shape.position.y,
                            "width": shape.position.width,
                            "height": shape.position.height
                        },
                        "is_required": placeholder_type in ["title", "subtitle"],
                        "sample_content": text
                    })
        
        # Extract chart data placeholders
        for chart in slide_info.charts:
            placeholders.append({
                "field_name": f"chart_{chart.chart_type.value}_{len(placeholders)}",
                "field_type": "chart_data",
                "position_info": {
                    "x": chart.position.x,
                    "y": chart.position.y,
                    "width": chart.position.width,
                    "height": chart.position.height
                },
                "is_required": True,
                "chart_metadata": {
                    "chart_type": chart.chart_type.value,
                    "data_series_count": chart.data_series_count,
                    "category_count": chart.category_count
                }
            })
        
        # Extract table data placeholders
        for table in slide_info.tables:
            placeholders.append({
                "field_name": f"table_{len(placeholders)}",
                "field_type": "table_data",
                "position_info": {
                    "x": table.position.x,
                    "y": table.position.y,
                    "width": table.position.width,
                    "height": table.position.height
                },
                "is_required": True,
                "table_metadata": {
                    "rows": table.rows,
                    "columns": table.columns,
                    "has_header": table.has_header
                }
            })
        
        return placeholders
    
    def _determine_text_placeholder_type(self, text: str) -> str:
        """
        Determine the type of text placeholder based on content.
        
        Args:
            text: Text content
        
        Returns:
            Placeholder type string
        """
        text_lower = text.lower()
        
        # Title patterns
        if any(word in text_lower for word in ["title", "heading", "header"]):
            return "title"
        
        # Subtitle patterns
        if any(word in text_lower for word in ["subtitle", "subheading", "byline"]):
            return "subtitle"
        
        # Number patterns
        if text.replace(".", "").replace(",", "").isdigit():
            return "number"
        
        # Date patterns
        if any(word in text_lower for word in ["date", "time", "year", "month"]):
            return "date"
        
        # Default to body text
        return "text"
    
    def _generate_description(self, slide_info: SlideInfo, classification: SlideCategory) -> str:
        """
        Generate a natural language description of the slide.
        
        Args:
            slide_info: Parsed slide information
            classification: Slide category
        
        Returns:
            Description string
        """
        parts = []
        
        # Add classification
        parts.append(f"A {classification.value.replace('_', ' ')} slide")
        
        # Add element counts
        elements = []
        if slide_info.charts:
            elements.append(f"{len(slide_info.charts)} chart(s)")
        if slide_info.tables:
            elements.append(f"{len(slide_info.tables)} table(s)")
        if slide_info.images:
            elements.append(f"{len(slide_info.images)} image(s)")
        if len(slide_info.shapes) > len(slide_info.charts) + len(slide_info.tables) + len(slide_info.images):
            elements.append(f"{len(slide_info.shapes)} shape(s)")
        
        if elements:
            parts.append(f"containing {', '.join(elements)}")
        
        # Add complexity
        if slide_info.complexity_score < 5:
            parts.append("with simple layout")
        elif slide_info.complexity_score < 15:
            parts.append("with moderate complexity")
        else:
            parts.append("with complex layout")
        
        # Add color information
        if slide_info.color_palette:
            parts.append(f"using {len(slide_info.color_palette)} distinct colors")
        
        return " ".join(parts) + "."
    
    def calculate_template_hash(self, slide_info: SlideInfo) -> str:
        """
        Calculate a structural hash for the template to identify similar layouts.
        
        Args:
            slide_info: Parsed slide information
        
        Returns:
            Hash string representing the template structure
        """
        import hashlib
        
        # Create a simplified structural representation
        structure_parts = []
        
        # Add shape count and types
        shape_types = [shape.shape_type for shape in slide_info.shapes]
        structure_parts.append(f"shapes:{len(shape_types)}:{','.join(sorted(shape_types))}")
        
        # Add chart types
        chart_types = [chart.chart_type.value for chart in slide_info.charts]
        structure_parts.append(f"charts:{len(chart_types)}:{','.join(sorted(chart_types))}")
        
        # Add table info
        table_info = [f"{table.rows}x{table.columns}" for table in slide_info.tables]
        structure_parts.append(f"tables:{len(table_info)}:{','.join(table_info)}")
        
        # Add layout type
        structure_parts.append(f"layout:{slide_info.layout_type.value}")
        
        # Create hash
        structure_string = "|".join(structure_parts)
        return hashlib.md5(structure_string.encode()).hexdigest()
