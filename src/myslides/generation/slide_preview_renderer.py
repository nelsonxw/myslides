"""
Slide Preview Renderer for PPTX to image conversion (FR-4.5 Phase 2).
Generates PNG previews from PPTX slides.
"""
from typing import Optional, List
from pathlib import Path
from pptx import Presentation
import tempfile


class SlidePreviewRenderer:
    """Renders PPTX slides to PNG images for preview."""

    @staticmethod
    def render_slide_to_image(pptx_path: str, slide_index: int = 0,
                             output_path: Optional[str] = None) -> str:
        """
        Render a single slide from PPTX to PNG image.

        Args:
            pptx_path: Path to PPTX file
            slide_index: Index of slide to render (0-based)
            output_path: Optional output path for PNG

        Returns:
            Path to generated PNG file

        Note:
            For production use, this requires LibreOffice headless or similar.
            This is a placeholder implementation that documents the approach.
        """
        # Placeholder: In production, use LibreOffice headless:
        # soffice --headless --convert-to png --outdir /tmp input.pptx

        # For MVP, we return the PPTX path as a fallback
        # The frontend can display a placeholder icon instead
        if output_path is None:
            output_path = tempfile.mktemp(suffix='.png')

        # Try native PowerPoint COM on Windows
        try:
            import os
            import pythoncom
            import win32com.client

            abs_pptx = os.path.abspath(pptx_path)
            abs_output = os.path.abspath(output_path)
            if os.path.exists(abs_pptx):
                pythoncom.CoInitialize()
                app = win32com.client.Dispatch('PowerPoint.Application')
                pres = app.Presentations.Open(abs_pptx, WithWindow=False)
                try:
                    if slide_index < len(pres.Slides):
                        pres.Slides[slide_index + 1].Export(abs_output, 'PNG', 1920, 1080)
                finally:
                    pres.Close()
                if os.path.exists(abs_output) and os.path.getsize(abs_output) > 0:
                    return abs_output
        except Exception:
            pass

        return pptx_path

    @staticmethod
    def render_all_slides(pptx_path: str, output_dir: Optional[str] = None) -> List[str]:
        """
        Render all slides from PPTX to PNG images.

        Args:
            pptx_path: Path to PPTX file
            output_dir: Optional output directory

        Returns:
            List of paths to generated PNG files
        """
        if output_dir is None:
            output_dir = tempfile.mkdtemp()

        presentation = Presentation(pptx_path)
        output_paths = []

        for i in range(len(presentation.slides)):
            output_path = str(Path(output_dir) / f"slide_{i}.png")
            output_paths.append(SlidePreviewRenderer.render_slide_to_image(
                pptx_path, i, output_path
            ))

        return output_paths

    @staticmethod
    def get_slide_metadata(pptx_path: str, slide_index: int = 0) -> dict:
        """
        Get metadata about a slide for preview purposes.

        Args:
            pptx_path: Path to PPTX file
            slide_index: Index of slide (0-based)

        Returns:
            Dictionary with slide metadata (title, shape count, etc.)
        """
        presentation = Presentation(pptx_path)
        if slide_index >= len(presentation.slides):
            return {}

        slide = presentation.slides[slide_index]
        return {
            "slide_index": slide_index,
            "shape_count": len(slide.shapes),
            "has_chart": any(shape.has_chart for shape in slide.shapes),
            "has_table": any(shape.has_table for shape in slide.shapes),
            "has_image": any(shape.shape_type == 13 for shape in slide.shapes)
        }
