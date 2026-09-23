"""
Slide Generator for MySlides.
Handles template-based slide assembly (FR-4.1).
"""
from typing import Optional, Dict, Any, List
from pathlib import Path
from pptx import Presentation
from pptx.util import Inches, Pt

from myslides.generation.generation_models import (
    GenerationIntent, GenerationConfig, SlideType, ProcessStep
)
from myslides.generation.chart_generator import ChartGenerator
from myslides.generation.diagram_generator import DiagramGenerator
from myslides.generation.style_inheritor import StyleInheritor


class SlideGenerator:
    """Generates slides from structured intent using templates."""
    
    def __init__(self, config: Optional[GenerationConfig] = None, presentation: Optional[Presentation] = None):
        """
        Initialize the slide generator.
        
        Args:
            config: GenerationConfig with template and style information
            presentation: Optional existing presentation; creates a new one if omitted
        """
        self.config = config or GenerationConfig()
        self.presentation = presentation if presentation is not None else Presentation()
        
        # Initialize sub-components
        self.style_inheritor = StyleInheritor(
            color_palette=self.config.template_color_palette
        )
        self.chart_generator = ChartGenerator(self.presentation)
        self.diagram_generator = DiagramGenerator(
            self.presentation, 
            self.style_inheritor
        )
    
    def generate_slide(self, intent: GenerationIntent) -> Presentation:
        """
        Generate a single slide from structured intent.
        
        Args:
            intent: GenerationIntent with slide specifications
        
        Returns:
            pptx Presentation object with the generated slide
        """
        slide_layout = self._get_slide_layout(intent.slide_type)
        slide = self.presentation.slides.add_slide(slide_layout)
        
        if self.config.template_element_manifest:
            self._apply_template_background(slide)
        
        self._generate_content(slide, intent)
        return self.presentation
    
    def generate_deck(self, intents: List[GenerationIntent]) -> Presentation:
        """
        Generate a multi-slide presentation deck (FR-4.5).
        
        Args:
            intents: List of GenerationIntent objects, one per slide
        
        Returns:
            pptx Presentation object containing all generated slides
        """
        for intent in intents:
            self.generate_slide(intent)
        return self.presentation
    
    def _get_slide_layout(self, slide_type: SlideType):
        """Get appropriate slide layout for the slide type."""
        return self.presentation.slide_layouts[6]  # Blank layout
    
    def _apply_template_background(self, slide) -> None:
        """Apply background from template if available."""
        if self.style_inheritor.color_palette:
            background = slide.background
            if background and hasattr(background, "fill") and background.fill:
                try:
                    background.fill.solid()
                    primary = self.style_inheritor.get_primary_color()
                    if primary:
                        background.fill.fore_color.rgb = primary
                except Exception:
                    pass
    
    def _generate_content(self, slide, intent: GenerationIntent) -> None:
        """Generate slide content based on intent."""
        text_content = intent.get_text_content()
        
        if text_content and text_content.title:
            self._add_title(slide, text_content.title)
        
        if text_content and text_content.subtitle:
            self._add_subtitle(slide, text_content.subtitle)
        
        has_subtitle = bool(text_content and text_content.subtitle)
        chart_top = 2.2 if has_subtitle else 1.8
        chart_height = 4.6 if has_subtitle else 5.0
        
        if intent.slide_type == SlideType.DATA_CHART:
            chart_data = intent.get_chart_data()
            if chart_data:
                self.chart_generator.add_chart_to_slide(
                    slide, chart_data, top=chart_top, height=chart_height
                )
        
        elif intent.slide_type == SlideType.PROCESS_FLOW:
            steps = intent.get_process_steps()
            if steps:
                self.diagram_generator.create_process_flow(slide, steps)
        
        elif intent.slide_type == SlideType.TIMELINE:
            events = intent.get_timeline_events()
            if events:
                self.diagram_generator.create_timeline(slide, events)
        
        elif intent.slide_type == SlideType.TEXT_HEAVY:
            if text_content and text_content.bullet_points:
                self._add_bullet_points(slide, text_content.bullet_points)
            elif text_content and text_content.body_text:
                self._add_body_text(slide, text_content.body_text)
        
        elif intent.slide_type == SlideType.COMPARISON:
            self._add_comparison_layout(slide, intent)
        
        elif intent.slide_type == SlideType.TITLE_SLIDE:
            pass
        
        else:
            if text_content and text_content.bullet_points:
                self._add_bullet_points(slide, text_content.bullet_points)
    
    def _add_title(self, slide, title: str) -> None:
        """Add title to slide."""
        title_box = slide.shapes.add_textbox(
            Inches(0.5),
            Inches(0.5),
            Inches(9.0),
            Inches(1.0)
        )
        title_frame = title_box.text_frame
        title_frame.text = title
        title_frame.word_wrap = True
        
        if title_frame.paragraphs:
            p = title_frame.paragraphs[0]
            if p.runs:
                self.style_inheritor.apply_font_style(
                    p.runs[0],
                    font_size=36.0,
                    bold=True
                )
            self.style_inheritor.apply_alignment(p, "center")
    
    def _add_subtitle(self, slide, subtitle: str) -> None:
        """Add subtitle to slide."""
        subtitle_box = slide.shapes.add_textbox(
            Inches(0.5),
            Inches(1.5),
            Inches(9.0),
            Inches(0.6)
        )
        subtitle_frame = subtitle_box.text_frame
        subtitle_frame.text = subtitle
        subtitle_frame.word_wrap = True
        
        if subtitle_frame.paragraphs:
            p = subtitle_frame.paragraphs[0]
            if p.runs:
                self.style_inheritor.apply_font_style(
                    p.runs[0],
                    font_size=18.0
                )
            self.style_inheritor.apply_alignment(p, "center")
    
    def _add_bullet_points(self, slide, bullet_points: List[str]) -> None:
        """Add bullet points to slide."""
        content_box = slide.shapes.add_textbox(
            Inches(0.5),
            Inches(2.5),
            Inches(9.0),
            Inches(4.0)
        )
        text_frame = content_box.text_frame
        text_frame.word_wrap = True
        
        for i, point in enumerate(bullet_points):
            p = text_frame.paragraphs[0] if i == 0 else text_frame.add_paragraph()
            p.text = point
            p.level = 0
            p.space_after = Pt(12)
            if p.runs:
                self.style_inheritor.apply_font_style(
                    p.runs[0],
                    font_size=14.0
                )
    
    def _add_body_text(self, slide, body_text: str) -> None:
        """Add body text to slide."""
        content_box = slide.shapes.add_textbox(
            Inches(0.5),
            Inches(2.5),
            Inches(9.0),
            Inches(4.0)
        )
        text_frame = content_box.text_frame
        text_frame.text = body_text
        text_frame.word_wrap = True
        
        if text_frame.paragraphs and text_frame.paragraphs[0].runs:
            self.style_inheritor.apply_font_style(
                text_frame.paragraphs[0].runs[0],
                font_size=14.0
            )
    
    def _add_comparison_layout(self, slide, intent: GenerationIntent) -> None:
        """Add a two-column comparison layout."""
        text_content = intent.get_text_content()
        if not text_content or not text_content.bullet_points:
            return
        
        mid_point = len(text_content.bullet_points) // 2
        left_points = text_content.bullet_points[:mid_point]
        right_points = text_content.bullet_points[mid_point:]
        
        # Left column
        left_box = slide.shapes.add_textbox(
            Inches(0.5),
            Inches(2.5),
            Inches(4.0),
            Inches(4.0)
        )
        left_frame = left_box.text_frame
        left_frame.word_wrap = True
        for i, point in enumerate(left_points):
            p = left_frame.paragraphs[0] if i == 0 else left_frame.add_paragraph()
            p.text = point
            p.level = 0
            if p.runs:
                self.style_inheritor.apply_font_style(p.runs[0], font_size=14.0)
        
        # Right column
        right_box = slide.shapes.add_textbox(
            Inches(5.0),
            Inches(2.5),
            Inches(4.0),
            Inches(4.0)
        )
        right_frame = right_box.text_frame
        right_frame.word_wrap = True
        for i, point in enumerate(right_points):
            p = right_frame.paragraphs[0] if i == 0 else right_frame.add_paragraph()
            p.text = point
            p.level = 0
            if p.runs:
                self.style_inheritor.apply_font_style(p.runs[0], font_size=14.0)
    
    def adapt_element_count(self, intent: GenerationIntent, target_count: int) -> None:
        """
        Adapt template to match required element count (FR-3.3).
        
        Args:
            intent: GenerationIntent with current content
            target_count: Target number of elements
        """
        if intent.slide_type == SlideType.PROCESS_FLOW:
            steps = intent.get_process_steps()
            current_count = len(steps)
            
            if current_count < target_count:
                for i in range(current_count, target_count):
                    steps.append(ProcessStep(label=f"Step {i + 1}", number=i + 1))
                intent.content["steps"] = [s.label for s in steps]
            elif current_count > target_count:
                intent.content["steps"] = [s.label for s in steps[:target_count]]
