"""
Diagram Generator for MySlides.
Handles programmatic creation of diagrams (FR-4.3).
"""
from typing import List, Optional
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE, MSO_CONNECTOR
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor

from myslides.generation.generation_models import ProcessStep, TimelineEvent
from myslides.generation.style_inheritor import StyleInheritor


class DiagramGenerator:
    """Generates PowerPoint diagrams from structured data."""
    
    def __init__(self, presentation: Presentation, style_inheritor: Optional[StyleInheritor] = None):
        """
        Initialize the diagram generator.
        
        Args:
            presentation: pptx Presentation object
            style_inheritor: StyleInheritor for applying styles
        """
        self.presentation = presentation
        self.style_inheritor = style_inheritor or StyleInheritor()
    
    def create_process_flow(self, slide, steps: List[ProcessStep], 
                           horizontal: bool = True, shape_type: str = "rectangle") -> None:
        """
        Create a process flow diagram.
        
        Args:
            slide: pptx slide object
            steps: List of ProcessStep objects
            horizontal: Whether flow is horizontal (True) or vertical (False)
            shape_type: Type of shape to use ("rectangle", "chevron", "rounded_rectangle", "oval", "diamond")
        """
        if not steps:
            return
        
        slide_width = self.presentation.slide_width
        slide_height = self.presentation.slide_height
        
        # Calculate dimensions
        if horizontal:
            shape_width = Inches(1.7)
            shape_height = Inches(1.1)
            spacing = Inches(0.35)
            total_width = (len(steps) * shape_width) + ((len(steps) - 1) * spacing)
            start_x = (slide_width - total_width) // 2
            start_y = int(slide_height * 0.45)
        else:
            shape_width = Inches(2.2)
            shape_height = Inches(0.8)
            spacing = Inches(0.3)
            total_height = (len(steps) * shape_height) + ((len(steps) - 1) * spacing)
            start_x = (slide_width - shape_width) // 2
            start_y = (slide_height - total_height) // 2
        
        # Create shapes for each step
        for i, step in enumerate(steps):
            if horizontal:
                x = start_x + (i * (shape_width + spacing))
                y = start_y
            else:
                x = start_x
                y = start_y + (i * (shape_height + spacing))
            
            shape = self._add_shape(slide, shape_type, x, y, shape_width, shape_height)
            
            # Apply style
            color_index = i % len(self.style_inheritor.color_palette) if self.style_inheritor.color_palette else 0
            self.style_inheritor.apply_palette_to_shape(shape, color_index)
            
            # Add text
            text_frame = shape.text_frame
            text_frame.word_wrap = True
            
            # Add step label / number
            p = text_frame.paragraphs[0]
            if step.number is not None:
                p.text = f"{step.number}. {step.label}"
            else:
                p.text = step.label
            if p.runs:
                self.style_inheritor.apply_font_style(p.runs[0], font_size=14.0, bold=True)
            
            # Add description if provided
            if step.description:
                p_desc = text_frame.add_paragraph()
                p_desc.text = step.description
                if p_desc.runs:
                    self.style_inheritor.apply_font_style(p_desc.runs[0], font_size=10.0)
            
            # Add arrow between steps (except last)
            if i < len(steps) - 1:
                self._add_arrow(slide, shape, horizontal, spacing)
    
    def create_timeline(self, slide, events: List[TimelineEvent], 
                       horizontal: bool = True) -> None:
        """
        Create a timeline diagram.
        
        Args:
            slide: pptx slide object
            events: List of TimelineEvent objects
            horizontal: Whether timeline is horizontal (True) or vertical (False)
        """
        if not events:
            return
        
        slide_width = self.presentation.slide_width
        slide_height = self.presentation.slide_height
        
        # Calculate dimensions
        if horizontal:
            spacing = Inches(1.5)
            total_width = len(events) * spacing
            start_x = (slide_width - total_width) // 2 + Inches(0.75)
            start_y = slide_height // 2
        else:
            spacing = Inches(1.2)
            total_height = len(events) * spacing
            start_x = slide_width // 2
            start_y = (slide_height - total_height) // 2 + Inches(0.6)
        
        # Draw timeline connector line
        if horizontal:
            line_start_x = start_x - Inches(0.75)
            line_end_x = start_x + ((len(events) - 1) * spacing) + Inches(0.75)
            self._add_line(slide, line_start_x, start_y, line_end_x, start_y)
        else:
            line_start_y = start_y - Inches(0.6)
            line_end_y = start_y + ((len(events) - 1) * spacing) + Inches(0.6)
            self._add_line(slide, start_x, line_start_y, start_x, line_end_y)
        
        # Add event markers
        for i, event in enumerate(events):
            if horizontal:
                x = start_x + (i * spacing)
                y = start_y
            else:
                x = start_x
                y = start_y + (i * spacing)
            
            # Add circle marker
            marker = slide.shapes.add_shape(
                MSO_SHAPE.OVAL,
                x - Inches(0.1),
                y - Inches(0.1),
                Inches(0.2),
                Inches(0.2)
            )
            self.style_inheritor.apply_palette_to_shape(marker, 0)
            
            # Add date and title
            if horizontal:
                date_box = slide.shapes.add_textbox(
                    x - Inches(0.5),
                    y - Inches(0.8),
                    Inches(1.0),
                    Inches(0.3)
                )
                date_frame = date_box.text_frame
                date_frame.text = event.date
                if date_frame.paragraphs and date_frame.paragraphs[0].runs:
                    self.style_inheritor.apply_font_style(date_frame.paragraphs[0].runs[0], font_size=10.0)
                
                title_box = slide.shapes.add_textbox(
                    x - Inches(0.5),
                    y + Inches(0.15),
                    Inches(1.0),
                    Inches(0.5)
                )
                title_frame = title_box.text_frame
                title_frame.word_wrap = True
                title_frame.text = event.title
                if title_frame.paragraphs and title_frame.paragraphs[0].runs:
                    self.style_inheritor.apply_font_style(title_frame.paragraphs[0].runs[0], font_size=11.0, bold=True)
            else:
                date_box = slide.shapes.add_textbox(
                    x - Inches(1.5),
                    y - Inches(0.15),
                    Inches(1.0),
                    Inches(0.3)
                )
                date_frame = date_box.text_frame
                date_frame.text = event.date
                if date_frame.paragraphs and date_frame.paragraphs[0].runs:
                    self.style_inheritor.apply_font_style(date_frame.paragraphs[0].runs[0], font_size=10.0)
                
                title_box = slide.shapes.add_textbox(
                    x + Inches(0.15),
                    y - Inches(0.15),
                    Inches(2.0),
                    Inches(0.5)
                )
                title_frame = title_box.text_frame
                title_frame.word_wrap = True
                title_frame.text = event.title
                if title_frame.paragraphs and title_frame.paragraphs[0].runs:
                    self.style_inheritor.apply_font_style(title_frame.paragraphs[0].runs[0], font_size=11.0, bold=True)
    
    def _add_shape(self, slide, shape_type: str, x, y, width, height):
        """Add a shape to the slide."""
        shape_type_map = {
            "rectangle": MSO_SHAPE.ROUNDED_RECTANGLE,
            "chevron": MSO_SHAPE.CHEVRON,
            "rounded_rectangle": MSO_SHAPE.ROUNDED_RECTANGLE,
            "oval": MSO_SHAPE.OVAL,
            "diamond": MSO_SHAPE.DIAMOND
        }
        
        mso_type = shape_type_map.get(shape_type.lower(), MSO_SHAPE.ROUNDED_RECTANGLE)
        return slide.shapes.add_shape(mso_type, int(x), int(y), int(width), int(height))
    
    def _add_arrow(self, slide, from_shape, horizontal: bool, spacing) -> None:
        """Add an arrow shape between process steps."""
        arrow_len = Inches(0.18)
        arrow_thick = Inches(0.14)
        
        if horizontal:
            arrow_x = from_shape.left + from_shape.width + (spacing - arrow_len) // 2
            arrow_y = from_shape.top + (from_shape.height - arrow_thick) // 2
            arrow = slide.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, arrow_x, arrow_y, arrow_len, arrow_thick)
        else:
            arrow_x = from_shape.left + (from_shape.width - arrow_thick) // 2
            arrow_y = from_shape.top + from_shape.height + (spacing - arrow_len) // 2
            arrow = slide.shapes.add_shape(MSO_SHAPE.DOWN_ARROW, arrow_x, arrow_y, arrow_thick, arrow_len)
        
        if self.style_inheritor.color_palette:
            self.style_inheritor.apply_palette_to_shape(arrow, 0)
    
    def _add_line(self, slide, start_x, start_y, end_x, end_y) -> None:
        """Add a connector line to the slide."""
        connector = slide.shapes.add_connector(
            MSO_CONNECTOR.STRAIGHT,
            int(start_x),
            int(start_y),
            int(end_x),
            int(end_y)
        )
        if self.style_inheritor.color_palette:
            primary_color = self.style_inheritor.get_primary_color()
            if primary_color:
                connector.line.color.rgb = primary_color
        connector.line.width = Pt(2.0)
