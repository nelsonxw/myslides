"""
PPTX Exporter for MySlides.
Handles PPTX file export functionality (FR-4.5).
"""
from pathlib import Path
from typing import Optional
from pptx import Presentation


class PPTXExporter:
    """Exports generated presentations to PPTX files."""
    
    def __init__(self, presentation: Presentation):
        """
        Initialize the PPTX exporter.
        
        Args:
            presentation: pptx Presentation object to export
        """
        self.presentation = presentation
    
    def save(self, output_path: str) -> str:
        """
        Save the presentation to a PPTX file.
        
        Args:
            output_path: Path where the PPTX file should be saved
        
        Returns:
            Absolute path to the saved file
        """
        # Ensure the directory exists
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Save the presentation
        self.presentation.save(str(output_file))
        
        return str(output_file.absolute())
    
    def save_to_temp(self, filename: str = "generated_slide.pptx") -> str:
        """
        Save the presentation to a temporary directory.
        
        Args:
            filename: Name for the output file
        
        Returns:
            Absolute path to the saved file
        """
        import tempfile
        
        temp_dir = Path(tempfile.gettempdir())
        output_path = temp_dir / filename
        
        return self.save(str(output_path))
    
    def validate(self) -> bool:
        """
        Validate that the presentation is well-formed.
        
        Returns:
            True if valid, False otherwise
        """
        try:
            # Check that presentation has at least one slide
            if len(self.presentation.slides) == 0:
                return False
            
            # Check that each slide has shapes
            for slide in self.presentation.slides:
                if len(slide.shapes) == 0:
                    # Blank slides are allowed, but warn
                    pass
            
            return True
        except Exception:
            return False
    
    @staticmethod
    def create_empty() -> Presentation:
        """
        Create a new empty presentation.
        
        Returns:
            New pptx Presentation object
        """
        return Presentation()
    
    @staticmethod
    def load_from_file(file_path: str) -> Optional[Presentation]:
        """
        Load an existing presentation from file.
        
        Args:
            file_path: Path to the PPTX file
        
        Returns:
            Presentation object or None if loading fails
        """
        try:
            return Presentation(file_path)
        except Exception:
            return None
