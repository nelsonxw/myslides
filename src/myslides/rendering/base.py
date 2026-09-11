"""
Slide preview renderer protocol and base classes.
"""
from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable


@runtime_checkable
class SlideRenderer(Protocol):
    """Protocol for rendering a slide inside a .pptx to a PNG image file."""

    def render_slide(self, pptx_path: Path | str, slide_index: int = 0, output_png_path: Path | str | None = None) -> Path:
        """Render slide_index of pptx_path to PNG. Return output path."""
        ...
