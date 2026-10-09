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

        import os
        import io
        import zipfile
        from PIL import Image

        abs_pptx = os.path.abspath(pptx_path)
        abs_output = os.path.abspath(output_path)
        Path(abs_output).parent.mkdir(parents=True, exist_ok=True)

        # 1. Fast path: Extract embedded high-quality slide thumbnail directly from PPTX package (2-30ms)
        try:
            if os.path.exists(abs_pptx) and slide_index == 0:
                with zipfile.ZipFile(abs_pptx, 'r') as z:
                    thumb_names = [n for n in z.namelist() if n.lower() in ('docprops/thumbnail.jpeg', 'docprops/thumbnail.png', 'docprops/thumbnail.jpg')]
                    if thumb_names:
                        raw_data = z.read(thumb_names[0])
                        img = Image.open(io.BytesIO(raw_data))
                        img.save(abs_output, 'PNG')
                        if os.path.exists(abs_output) and os.path.getsize(abs_output) > 0:
                            return abs_output
        except Exception:
            pass

        # 2. Native PowerPoint COM on Windows (for slides without embedded thumbnail or slide_index > 0)
        try:
            import pythoncom
            import win32com.client

            if os.path.exists(abs_pptx):
                pythoncom.CoInitialize()
                try:
                    app = win32com.client.Dispatch('PowerPoint.Application')
                    pres = app.Presentations.Open(abs_pptx, WithWindow=False)
                    try:
                        if slide_index < len(pres.Slides):
                            pres.Slides[slide_index + 1].Export(abs_output, 'PNG', 1920, 1080)
                    finally:
                        pres.Close()
                finally:
                    pythoncom.CoUninitialize()

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
        total_slides = len(presentation.slides)
        output_paths = []

        try:
            import os
            import pythoncom
            import win32com.client

            abs_pptx = os.path.abspath(pptx_path)
            if os.path.exists(abs_pptx):
                pythoncom.CoInitialize()
                try:
                    app = win32com.client.Dispatch('PowerPoint.Application')
                    pres = app.Presentations.Open(abs_pptx, WithWindow=False)
                    try:
                        for i in range(total_slides):
                            out_png = os.path.abspath(str(Path(output_dir) / f"slide_{i}.png"))
                            if i < len(pres.Slides):
                                pres.Slides[i + 1].Export(out_png, 'PNG', 1920, 1080)
                                if os.path.exists(out_png) and os.path.getsize(out_png) > 0:
                                    output_paths.append(out_png)
                                else:
                                    output_paths.append(pptx_path)
                            else:
                                output_paths.append(pptx_path)
                    finally:
                        pres.Close()
                finally:
                    pythoncom.CoUninitialize()

                if len(output_paths) == total_slides:
                    return output_paths
        except Exception:
            pass

        output_paths = []
        for i in range(total_slides):
            out_p = str(Path(output_dir) / f"slide_{i}.png")
            output_paths.append(SlidePreviewRenderer.render_slide_to_image(
                pptx_path, i, out_p
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
