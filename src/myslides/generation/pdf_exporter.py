"""
PDF Exporter for PPTX to PDF conversion (FR-4.5 Phase 2).
Exports PPTX presentations to PDF format.
"""
from typing import Optional
from pathlib import Path
import tempfile


class PDFExporter:
    """Exports PPTX presentations to PDF format."""

    @staticmethod
    def export_to_pdf(pptx_path: str, output_path: Optional[str] = None) -> str:
        """
        Export PPTX file to PDF.

        Args:
            pptx_path: Path to PPTX file
            output_path: Optional output path for PDF

        Returns:
            Path to generated PDF file

        Note:
            For production use, this requires LibreOffice headless or similar.
            This is a placeholder implementation that documents the approach.
        """
        # Placeholder: In production, use LibreOffice headless:
        # soffice --headless --convert-to pdf --outdir /tmp input.pptx

        if output_path is None:
            output_path = tempfile.mktemp(suffix='.pdf')

        # Try native PowerPoint COM on Windows (32 = ppSaveAsPDF)
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
                    pres.SaveAs(abs_output, 32)
                finally:
                    pres.Close()
                if os.path.exists(abs_output) and os.path.getsize(abs_output) > 0:
                    return abs_output
        except Exception:
            pass

        # For MVP fallback, return the PPTX path
        return pptx_path

    @staticmethod
    def export_deck_to_pdf(pptx_path: str, slide_indices: Optional[list] = None,
                          output_path: Optional[str] = None) -> str:
        """
        Export selected slides from a deck to PDF.

        Args:
            pptx_path: Path to PPTX file
            slide_indices: Optional list of slide indices to export
            output_path: Optional output path for PDF

        Returns:
            Path to generated PDF file
        """
        if slide_indices is None:
            return PDFExporter.export_to_pdf(pptx_path, output_path)

        # TODO: For selective slide export, would need to:
        # 1. Create a temporary PPTX with only selected slides
        # 2. Export that to PDF
        # 3. Clean up temporary file

        return PDFExporter.export_to_pdf(pptx_path, output_path)
