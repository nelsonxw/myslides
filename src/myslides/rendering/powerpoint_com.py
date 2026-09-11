"""
High-fidelity slide renderer using Windows PowerPoint COM automation via pywin32.
"""
from __future__ import annotations

import os
import threading
from pathlib import Path
from myslides.config import settings

# Lock to serialize PowerPoint COM calls across threads
_com_lock = threading.Lock()


class PowerPointComRenderer:
    """Renders slides to crisp 1080p PNG images using installed Microsoft PowerPoint."""

    def __init__(self):
        self._powerpoint_app = None

    def render_slide(
        self,
        pptx_path: Path | str,
        slide_index: int = 0,
        output_png_path: Path | str | None = None,
    ) -> Path:
        """Export a slide from PPTX to PNG."""
        import pythoncom
        import win32com.client

        pptx_file = Path(pptx_path).resolve()
        if not pptx_file.exists():
            raise FileNotFoundError(f"PPTX not found: {pptx_file}")

        if output_png_path is None:
            settings.ensure_directories()
            out_file = settings.data_dir / "previews" / f"{pptx_file.stem}_slide_{slide_index}.png"
        else:
            out_file = Path(output_png_path).resolve()

        out_file.parent.mkdir(parents=True, exist_ok=True)

        with _com_lock:
            pythoncom.CoInitialize()
            ppt_app = None
            presentation = None
            try:
                # Open hidden PowerPoint instance
                ppt_app = win32com.client.DispatchEx("PowerPoint.Application")
                # WithWindow=False (2) opens presentation invisibly
                presentation = ppt_app.Presentations.Open(
                    str(pptx_file),
                    ReadOnly=True,
                    Untitled=False,
                    WithWindow=False,
                )
                
                # PowerPoint COM slide index is 1-based
                ppt_slide_idx = slide_index + 1
                if ppt_slide_idx > presentation.Slides.Count:
                    raise IndexError(f"Slide index {slide_index} out of range ({presentation.Slides.Count} slides)")

                slide = presentation.Slides(ppt_slide_idx)
                # Export with 1920x1080 resolution
                slide.Export(str(out_file), "PNG", 1920, 1080)
                return out_file
            finally:
                if presentation:
                    try:
                        presentation.Close()
                    except Exception:
                        pass
                    presentation = None
                if ppt_app:
                    try:
                        ppt_app.Quit()
                    except Exception:
                        pass
                    ppt_app = None
                try:
                    pythoncom.CoUninitialize()
                except Exception:
                    pass


class MockRenderer:
    """Mock renderer generating a placeholder PNG for offline/non-Windows environments."""

    def render_slide(
        self,
        pptx_path: Path | str,
        slide_index: int = 0,
        output_png_path: Path | str | None = None,
    ) -> Path:
        from PIL import Image, ImageDraw

        pptx_file = Path(pptx_path).resolve()
        if output_png_path is None:
            settings.ensure_directories()
            out_file = settings.data_dir / "previews" / f"{pptx_file.stem}_slide_{slide_index}.png"
        else:
            out_file = Path(output_png_path).resolve()

        out_file.parent.mkdir(parents=True, exist_ok=True)
        img = Image.new("RGB", (1920, 1080), color=(29, 44, 59))  # Cosmos background
        draw = ImageDraw.Draw(img)
        draw.rectangle([50, 50, 1870, 1030], outline=(6, 114, 203), width=4)
        draw.text((100, 100), f"Preview: {pptx_file.name} (Slide {slide_index})", fill=(255, 255, 255))
        img.save(out_file, "PNG")
        return out_file


def get_default_renderer():
    """Return configured SlideRenderer."""
    if os.name == "nt" and settings.renderer == "powerpoint":
        try:
            return PowerPointComRenderer()
        except Exception:
            return MockRenderer()
    return MockRenderer()
