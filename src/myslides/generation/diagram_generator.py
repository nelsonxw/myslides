"""
Diagram Generator for MySlides.
Handles programmatic creation of diagrams (FR-4.3).
"""
from typing import List, Optional, Dict, Any
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

    def create_cycle_diagram(self, slide, steps: List[ProcessStep]) -> None:
        """
        Create a circular cycle diagram (FR-4.3 Phase 2).

        Args:
            slide: pptx slide object
            steps: List of ProcessStep objects
        """
        if not steps:
            return

        import math

        slide_width = self.presentation.slide_width
        slide_height = self.presentation.slide_height
        center_x = slide_width // 2
        center_y = slide_height // 2
        radius = Inches(2.2)
        node_radius = Inches(0.65)
        angle_step = 360.0 / len(steps)

        positions = []
        for i, step in enumerate(steps):
            angle = i * angle_step
            rad = math.radians(angle - 90)
            x = center_x + int(radius * math.cos(rad))
            y = center_y + int(radius * math.sin(rad))
            positions.append((x, y))

            shape = self._add_shape(slide, "oval", x - node_radius, y - node_radius, node_radius * 2, node_radius * 2)
            self.style_inheritor.apply_palette_to_shape(shape, i)

            text_frame = shape.text_frame
            text_frame.text = f"{step.number}\n{step.label}"
            if text_frame.paragraphs and text_frame.paragraphs[0].runs:
                self.style_inheritor.apply_font_style(text_frame.paragraphs[0].runs[0], font_size=10.0, bold=True)

        # Connect all nodes in a closed loop cycle
        for i in range(len(steps)):
            x, y = positions[i]
            next_x, next_y = positions[(i + 1) % len(steps)]
            self._add_curved_arrow(slide, x, y, next_x, next_y)

    def create_hierarchy_diagram(self, slide, hierarchy: Dict[str, Any]) -> None:
        """
        Create a hierarchy/org chart diagram (FR-4.3 Phase 2).

        Args:
            slide: pptx slide object
            hierarchy: Dictionary with 'root' and 'children' structure
        """
        root = hierarchy.get('root', {})
        children = hierarchy.get('children', [])

        slide_width = self.presentation.slide_width
        slide_height = self.presentation.slide_height

        # Root node
        root_x = (slide_width - Inches(2.5)) // 2
        root_y = Inches(1.5)
        root_shape = self._add_shape(slide, "rectangle", root_x, root_y, Inches(2.5), Inches(0.8))
        self.style_inheritor.apply_palette_to_shape(root_shape, 0)

        root_frame = root_shape.text_frame
        root_frame.text = root.get('label', 'Root')
        if root_frame.paragraphs and root_frame.paragraphs[0].runs:
            self.style_inheritor.apply_font_style(root_frame.paragraphs[0].runs[0], font_size=12.0, bold=True)

        # Children nodes
        if children:
            child_width = Inches(2.0)
            child_height = Inches(0.7)
            spacing = Inches(0.3)
            total_width = (len(children) * child_width) + ((len(children) - 1) * spacing)
            start_x = (slide_width - total_width) // 2
            child_y = Inches(3.5)

            for i, child in enumerate(children):
                child_x = start_x + i * (child_width + spacing)
                child_shape = self._add_shape(slide, "rectangle", child_x, child_y, child_width, child_height)
                self.style_inheritor.apply_palette_to_shape(child_shape, 1)

                child_frame = child_shape.text_frame
                child_frame.text = child.get('label', f'Child {i + 1}')
                if child_frame.paragraphs and child_frame.paragraphs[0].runs:
                    self.style_inheritor.apply_font_style(child_frame.paragraphs[0].runs[0], font_size=11.0)

                # Connector line
                connector_x = child_x + child_width // 2
                self._add_line(slide, root_x + Inches(1.25), root_y + Inches(0.8), connector_x, child_y)

    def create_pyramid_diagram(self, slide, levels: List[Dict[str, Any]]) -> None:
        """
        Create a pyramid/funnel diagram (FR-4.3 Phase 2).

        Args:
            slide: pptx slide object
            levels: List of level dictionaries with 'label' and 'value'
        """
        if not levels:
            return

        slide_width = self.presentation.slide_width
        slide_height = self.presentation.slide_height
        base_width = Inches(5.0)
        base_height = Inches(4.0)
        start_x = (slide_width - base_width) // 2
        start_y = (slide_height - base_height) // 2

        level_height = base_height / len(levels)

        for i, level in enumerate(levels):
            top_width = base_width * (1 - (i + 1) / len(levels))
            bottom_width = base_width * (1 - i / len(levels))
            level_y = start_y + i * level_height

            # Use trapezoid-like rectangle with adjusted width
            level_width = (top_width + bottom_width) // 2
            level_x = start_x + (base_width - level_width) // 2

            shape = self._add_shape(slide, "rectangle", level_x, level_y, level_width, level_height)
            self.style_inheritor.apply_palette_to_shape(shape, i)

            text_box = slide.shapes.add_textbox(
                level_x + Inches(0.5),
                level_y + level_height // 2 - Inches(0.2),
                level_width - Inches(1.0),
                Inches(0.4)
            )
            text_frame = text_box.text_frame
            text_frame.text = level.get('label', f'Level {i + 1}')
            if text_frame.paragraphs and text_frame.paragraphs[0].runs:
                self.style_inheritor.apply_font_style(text_frame.paragraphs[0].runs[0], font_size=11.0, bold=True)

    def create_matrix_diagram(self, slide, quadrants: List[Dict[str, Any]]) -> None:
        """
        Create a 2x2 matrix/quadrant diagram (FR-4.3 Phase 2).

        Args:
            slide: pptx slide object
            quadrants: List of 4 quadrant dictionaries with 'label' and 'description'
        """
        slide_width = self.presentation.slide_width
        slide_height = self.presentation.slide_height
        matrix_size = Inches(5.0)
        start_x = (slide_width - matrix_size) // 2
        start_y = (slide_height - matrix_size) // 2
        quadrant_size = matrix_size // 2

        quadrant_positions = [
            (start_x, start_y),
            (start_x + quadrant_size, start_y),
            (start_x, start_y + quadrant_size),
            (start_x + quadrant_size, start_y + quadrant_size)
        ]

        for i, quadrant in enumerate(quadrants[:4]):
            qx, qy = quadrant_positions[i]
            shape = self._add_shape(slide, "rectangle", qx, qy, quadrant_size, quadrant_size)
            self.style_inheritor.apply_palette_to_shape(shape, i)

            text_box = slide.shapes.add_textbox(
                qx + Inches(0.2),
                qy + quadrant_size // 2 - Inches(0.4),
                quadrant_size - Inches(0.4),
                Inches(0.8)
            )
            text_frame = text_box.text_frame
            text_frame.word_wrap = True
            text_frame.text = quadrant.get('label', f'Quadrant {i + 1}')
            if text_frame.paragraphs and text_frame.paragraphs[0].runs:
                self.style_inheritor.apply_font_style(text_frame.paragraphs[0].runs[0], font_size=11.0, bold=True)

    def create_venn_diagram(self, slide, sets: List[Dict[str, Any]]) -> None:
        """
        Create a Venn diagram with overlapping circles (FR-4.3 Phase 2).

        Args:
            slide: pptx slide object
            sets: List of set dictionaries with 'label'
        """
        if not sets or len(sets) > 3:
            return

        slide_width = self.presentation.slide_width
        slide_height = self.presentation.slide_height
        center_x = slide_width // 2
        center_y = slide_height // 2
        radius = Inches(1.3)
        offset = Inches(0.8)

        positions = [
            (center_x - offset, center_y),
            (center_x + offset, center_y),
            (center_x, center_y - offset)
        ]

        for i, set_data in enumerate(sets[:3]):
            sx, sy = positions[i]
            shape = self._add_shape(slide, "oval", sx - radius, sy - radius, radius * 2, radius * 2)
            self.style_inheritor.apply_palette_to_shape(shape, i)
            self._apply_shape_transparency(shape, 0.4)

            text_box = slide.shapes.add_textbox(
                sx - Inches(0.8),
                sy - Inches(0.2),
                Inches(1.6),
                Inches(0.4)
            )
            text_frame = text_box.text_frame
            text_frame.text = set_data.get('label', f'Set {i + 1}')
            if text_frame.paragraphs and text_frame.paragraphs[0].runs:
                self.style_inheritor.apply_font_style(text_frame.paragraphs[0].runs[0], font_size=11.0, bold=True)

    def _apply_shape_transparency(self, shape, opacity_percent: float = 0.5) -> None:
        """Apply opacity to a shape fill via OpenXML alpha element."""
        try:
            from pptx.oxml import parse_xml
            fill_el = shape.fill._fill._xPr
            srgb = fill_el.find('{http://schemas.openxmlformats.org/drawingml/2006/main}srgbClr')
            if srgb is not None:
                alpha_val = int(opacity_percent * 100000)
                alpha = parse_xml(f'<a:alpha xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" val="{alpha_val}"/>')
                srgb.append(alpha)
        except Exception:
            pass

    def _add_curved_arrow(self, slide, start_x, start_y, end_x, end_y) -> None:
        """Add a curved connector for cycle diagrams."""
        connector = slide.shapes.add_connector(
            MSO_CONNECTOR.CURVE,
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
