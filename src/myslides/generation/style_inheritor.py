"""
Style Inheritor for MySlides.
Handles style inheritance from templates to generated slides (FR-4.4).
"""
from typing import Optional, List, Dict, Any
from pptx.dml.color import RGBColor
from pptx.util import Pt
from pptx.enum.text import PP_ALIGN


class StyleInheritor:
    """Applies visual styles from templates to generated slides."""
    
    def __init__(self, color_palette: Optional[List[str]] = None):
        """
        Initialize the style inheritor.
        
        Args:
            color_palette: List of hex color codes to use as the style palette
        """
        self.color_palette = color_palette or []
        self._color_cache: Dict[str, RGBColor] = {}
    
    def apply_palette_to_shape(self, shape, color_index: int = 0) -> None:
        """
        Apply a color from the palette to a shape's fill.
        
        Args:
            shape: pptx shape object
            color_index: Index in the palette to use
        """
        if not self.color_palette or color_index >= len(self.color_palette):
            return
        
        hex_color = self.color_palette[color_index]
        rgb = self._hex_to_rgb(hex_color)
        
        if hasattr(shape, 'fill') and shape.fill:
            try:
                shape.fill.solid()
                shape.fill.fore_color.rgb = rgb
            except Exception:
                pass
    
    def apply_palette_to_text_frame(self, text_frame, color_index: int = 0) -> None:
        """
        Apply a color from the palette to text.
        
        Args:
            text_frame: pptx text frame object
            color_index: Index in the palette to use
        """
        if not self.color_palette or color_index >= len(self.color_palette):
            return
        
        hex_color = self.color_palette[color_index]
        rgb = self._hex_to_rgb(hex_color)
        
        for paragraph in text_frame.paragraphs:
            for run in paragraph.runs:
                run.font.color.rgb = rgb
    
    def apply_font_style(self, text_run, font_name: str = "Calibri", 
                        font_size: float = 11.0, bold: bool = False, 
                        italic: bool = False) -> None:
        """
        Apply font styling to a text run.
        
        Args:
            text_run: pptx text run object
            font_name: Font family name
            font_size: Font size in points
            bold: Whether text is bold
            italic: Whether text is italic
        """
        if text_run is None or not hasattr(text_run, 'font'):
            return
        text_run.font.name = font_name
        text_run.font.size = Pt(font_size)
        text_run.font.bold = bold
        text_run.font.italic = italic
    
    def apply_alignment(self, paragraph, alignment: str = "left") -> None:
        """
        Apply text alignment to a paragraph.
        
        Args:
            paragraph: pptx paragraph object
            alignment: Alignment type ("left", "center", "right", "justify")
        """
        alignment_map = {
            "left": PP_ALIGN.LEFT,
            "center": PP_ALIGN.CENTER,
            "right": PP_ALIGN.RIGHT,
            "justify": PP_ALIGN.JUSTIFY
        }
        paragraph.alignment = alignment_map.get(alignment.lower(), PP_ALIGN.LEFT)
    
    def get_primary_color(self) -> Optional[RGBColor]:
        """Get the primary color from the palette."""
        if self.color_palette:
            return self._hex_to_rgb(self.color_palette[0])
        return None
    
    def get_secondary_color(self) -> Optional[RGBColor]:
        """Get the secondary color from the palette."""
        if len(self.color_palette) > 1:
            return self._hex_to_rgb(self.color_palette[1])
        return None
    
    def get_accent_color(self, index: int = 2) -> Optional[RGBColor]:
        """
        Get an accent color from the palette.
        
        Args:
            index: Index of the accent color (default 2 for third color)
        """
        if len(self.color_palette) > index:
            return self._hex_to_rgb(self.color_palette[index])
        return None
    
    def _hex_to_rgb(self, hex_color: str) -> RGBColor:
        """
        Convert hex color string to RGBColor object.
        
        Args:
            hex_color: Hex color string (e.g., "#FF0000")
        
        Returns:
            RGBColor object
        """
        if hex_color in self._color_cache:
            return self._color_cache[hex_color]
        
        # Remove # if present
        hex_color = hex_color.lstrip("#")
        
        # Parse hex values
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        
        rgb = RGBColor(r, g, b)
        self._color_cache[hex_color] = rgb
        return rgb
    
    def apply_shape_border(self, shape, border_color: Optional[str] = None, 
                          border_width: float = 1.0) -> None:
        """
        Apply border styling to a shape.
        
        Args:
            shape: pptx shape object
            border_color: Hex color for border (uses palette if None)
            border_width: Border width in points
        """
        if not shape.line:
            return
        
        if border_color is None and self.color_palette:
            border_color = self.color_palette[0]
        
        if border_color:
            rgb = self._hex_to_rgb(border_color)
            shape.line.color.rgb = rgb
        
        shape.line.width = Pt(border_width)
    
    def apply_shape_shadow(self, shape, shadow_enabled: bool = True) -> None:
        """
        Apply shadow effect to a shape.
        
        Args:
            shape: pptx shape object
            shadow_enabled: Whether to enable shadow
        """
        if shadow_enabled and shape.shadow:
            shape.shadow.inherit = True
        elif not shadow_enabled and shape.shadow:
            shape.shadow.inherit = False
