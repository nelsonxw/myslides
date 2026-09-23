"""
Ingestion Pipeline for MySlides.
Coordinates the entire slide ingestion process from upload to template storage.
"""
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

from myslides.config import settings
from myslides.storage.firebase_storage import FirebaseStorageService
from myslides.ingestion.pptx_parser import PPTXParser, SlideInfo
from myslides.ingestion.slide_classifier import SlideClassifier
from myslides.ingestion.template_extractor import TemplateExtractor
from myslides.ingestion.embedding_generator import EmbeddingGenerator
from myslides.database.database_manager import DatabaseManager
from myslides.database.models import SlideCollection, SlideTemplate


class IngestionPipeline:
    """Main pipeline for ingesting PPTX files and creating slide templates."""
    
    def __init__(self):
        """Initialize the ingestion pipeline with required services."""
        self.storage_service = FirebaseStorageService.get_instance()
        self.database_manager = DatabaseManager()
        self.template_extractor = TemplateExtractor()
        self.embedding_generator = EmbeddingGenerator()
    
    def ingest_pptx_file(
        self,
        local_pptx_path: Path | str,
        collection_name: str,
        generate_thumbnails: bool = True
    ) -> Dict[str, Any]:
        """
        Ingest a PPTX file through the complete pipeline.
        
        Args:
            local_pptx_path: Path to local PPTX file
            collection_name: Name for the slide collection
            generate_thumbnails: Whether to generate thumbnail images
        
        Returns:
            Dictionary with ingestion results
        """
        start_time = datetime.now()
        results = {
            "success": False,
            "collection_id": None,
            "slides_processed": 0,
            "templates_created": 0,
            "errors": [],
            "processing_time_seconds": 0
        }
        
        try:
            # Step 1: Parse PPTX file (individual slide)
            parser = PPTXParser(local_pptx_path)
            slide_info = parser.parse_slide(slide_index=0)  # Individual slides always have index 0
            slides_info = [slide_info]
            presentation_metadata = parser.get_presentation_metadata()
            
            results["slides_processed"] = 1  # Individual slides always have 1 slide
            
            # Step 2: Upload PPTX to Firebase Storage
            pptx_storage_info = self.storage_service.upload_pptx(
                local_path=local_pptx_path,
                collection_name=collection_name,
                metadata={
                    "original_filename": presentation_metadata["file_name"],
                    "slide_count": presentation_metadata["slide_count"],
                    "uploaded_at": datetime.now().isoformat()
                }
            )
            
            # Step 3: Create database collection record
            collection = self.database_manager.create_collection(
                file_name=presentation_metadata["file_name"],
                storage_path=pptx_storage_info.storage_path,
                total_slides=presentation_metadata["slide_count"],
                collection_metadata=presentation_metadata
            )
            
            results["collection_id"] = collection.id
            
            # Step 4: Process the single slide
            for slide_info in slides_info:
                try:
                    # Generate thumbnail if requested
                    thumbnail_path = None
                    if generate_thumbnails:
                        thumbnail_path = self._generate_slide_thumbnail(
                            local_pptx_path, 
                            0,  # Individual slides always have index 0
                            collection_name
                        )
                        
                        # Upload thumbnail to Firebase
                        if thumbnail_path:
                            thumbnail_storage_info = self.storage_service.upload_thumbnail(
                                local_path=thumbnail_path,
                                collection_name=collection_name,
                                slide_index=0,  # Individual slides always have index 0
                                associated_pptx_id=pptx_storage_info.id,
                                metadata={"slide_index": 0}
                            )
                            thumbnail_path = thumbnail_storage_info.storage_path
                    
                    # Extract template
                    template = self.template_extractor.extract_template(
                        slide_info=slide_info,
                        collection_id=str(collection.id),
                        original_filename=presentation_metadata["file_name"],
                        thumbnail_path=thumbnail_path
                    )
                    
                    # Calculate template hash
                    template_hash = self.template_extractor.calculate_template_hash(slide_info)
                    
                    # Generate embeddings
                    semantic_embedding = self.embedding_generator.generate_semantic_embedding(
                        slide_info, 
                        template.template_id
                    )
                    
                    visual_embedding = None
                    if thumbnail_path:
                        # For MVP, we'll skip actual visual embedding generation
                        # since it requires proper image processing
                        pass
                    
                    # Create database template record
                    template_data = {
                        "collection_id": collection.id,
                        "slide_index": 0,  # Individual slides always have index 0
                        "classification": template.classification,
                        "tags": template.tags,
                        "thumbnail_path": template.thumbnail_path,
                        "original_pptx_reference": pptx_storage_info.storage_path,
                        "element_manifest": template.element_manifest,
                        "placeholder_map": template.placeholder_map,
                        "color_palette": template.color_palette,
                        "complexity_score": template.complexity_score,
                        "description": template.description,
                        "template_hash": template_hash,
                        "visual_embedding": visual_embedding,
                        "semantic_embedding": semantic_embedding
                    }
                    
                    self.database_manager.create_template(template_data)
                    results["templates_created"] += 1
                    
                except Exception as slide_error:
                    error_msg = f"Error processing slide {slide_info.slide_index}: {str(slide_error)}"
                    results["errors"].append(error_msg)
                    print(error_msg)
            
            results["success"] = True
            
        except Exception as e:
            error_msg = f"Error during ingestion: {str(e)}"
            results["errors"].append(error_msg)
            print(error_msg)
        
        results["processing_time_seconds"] = (datetime.now() - start_time).total_seconds()
        return results
    
    def _generate_slide_thumbnail(
        self, 
        pptx_path: Path | str, 
        slide_index: int, 
        collection_name: str
    ) -> Optional[Path]:
        """
        Generate a thumbnail image for a specific slide.
        
        Args:
            pptx_path: Path to PPTX file
            slide_index: Index of the slide
            collection_name: Name of the collection
        
        Returns:
            Path to generated thumbnail or None if generation fails
        """
        # For MVP, we'll use a placeholder approach
        # In production, this would use LibreOffice headless or similar
        
        try:
            # Create thumbnail filename
            thumbnail_filename = f"{collection_name}_slide_{slide_index}.png"
            thumbnail_path = settings.thumbnails_dir / thumbnail_filename
            
            # For MVP, create a simple placeholder image
            # In production, use proper slide rendering
            from PIL import Image, ImageDraw, ImageFont
            
            # Create a simple placeholder image
            img = Image.new('RGB', (960, 540), color='white')
            draw = ImageDraw.Draw(img)
            
            # Add slide index text
            try:
                font = ImageFont.truetype("arial.ttf", 40)
            except:
                font = ImageFont.load_default()
            
            text = f"Slide {slide_index + 1}"
            draw.text((50, 50), text, fill='black', font=font)
            
            # Save thumbnail
            img.save(thumbnail_path)
            return thumbnail_path
            
        except Exception as e:
            print(f"Error generating thumbnail for slide {slide_index}: {e}")
            return None
    
    def get_ingestion_status(self) -> Dict[str, Any]:
        """
        Get the current status of the ingestion pipeline.
        
        Returns:
            Dictionary with pipeline status information
        """
        storage_status = self.storage_service.get_status()
        db_stats = self.database_manager.get_statistics()
        
        return {
            "storage": storage_status,
            "database": db_stats,
            "data_directories": {
                "uploads_dir": str(settings.uploads_dir),
                "templates_dir": str(settings.templates_dir),
                "thumbnails_dir": str(settings.thumbnails_dir),
                "chroma_db_dir": str(settings.chroma_persist_directory)
            }
        }
    
    def process_batch_files(
        self, 
        pptx_files: list[Path | str], 
        collection_name: str
    ) -> Dict[str, Any]:
        """
        Process multiple PPTX files in a batch.
        
        Args:
            pptx_files: List of PPTX file paths
            collection_name: Base name for the collection
        
        Returns:
            Dictionary with batch processing results
        """
        batch_results = {
            "success": True,
            "total_files": len(pptx_files),
            "successful_files": 0,
            "failed_files": 0,
            "total_slides_processed": 0,
            "total_templates_created": 0,
            "file_results": [],
            "errors": []
        }
        
        for i, pptx_file in enumerate(pptx_files):
            try:
                file_collection_name = f"{collection_name}_{i}"
                result = self.ingest_pptx_file(pptx_file, file_collection_name)
                
                file_result = {
                    "file": str(pptx_file),
                    "collection_name": file_collection_name,
                    "success": result["success"],
                    "slides_processed": result["slides_processed"],
                    "templates_created": result["templates_created"],
                    "errors": result["errors"]
                }
                
                batch_results["file_results"].append(file_result)
                
                if result["success"]:
                    batch_results["successful_files"] += 1
                    batch_results["total_slides_processed"] += result["slides_processed"]
                    batch_results["total_templates_created"] += result["templates_created"]
                else:
                    batch_results["failed_files"] += 1
                    batch_results["errors"].extend(result["errors"])
                    
            except Exception as e:
                batch_results["failed_files"] += 1
                error_msg = f"Error processing file {pptx_file}: {str(e)}"
                batch_results["errors"].append(error_msg)
                batch_results["file_results"].append({
                    "file": str(pptx_file),
                    "success": False,
                    "error": error_msg
                })
        
        batch_results["success"] = batch_results["failed_files"] == 0
        return batch_results
