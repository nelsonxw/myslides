"""
Test the ingestion pipeline with real PPTX files from Firebase Storage.
"""
import sys
from pathlib import Path
import tempfile

# Add src directory to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from myslides.storage.firebase_storage import FirebaseStorageService
from myslides.ingestion.ingestion_pipeline import IngestionPipeline
from myslides.database.database_manager import DatabaseManager


def test_ingestion_from_firebase():
    """Test ingesting a few real PPTX files from Firebase Storage."""
    print("Testing ingestion with real PPTX files from Firebase Storage...")
    
    storage_service = FirebaseStorageService.get_instance()
    pipeline = IngestionPipeline()
    db_manager = DatabaseManager()
    
    if not storage_service.is_connected:
        print("ERROR: Firebase Storage is not connected")
        return False
    
    # Get some sample PPTX files from Firebase Storage
    print("Fetching sample PPTX files from Firebase Storage...")
    
    try:
        # List first few PPTX files from curated slides
        blobs = list(storage_service.bucket.list_blobs(prefix="curated slides/"))
        pptx_blobs = [b for b in blobs if b.name.endswith('.pptx')][:5]  # Get first 5
        
        if not pptx_blobs:
            print("No PPTX files found in Firebase Storage")
            return False
        
        print(f"Found {len(pptx_blobs)} sample PPTX files to process")
        
        # Download and process each file
        results = []
        for i, blob in enumerate(pptx_blobs, 1):
            print(f"\nProcessing file {i}/{len(pptx_blobs)}: {blob.name}")
            
            try:
                # Download file to temporary location
                with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as tmp_file:
                    blob.download_to_file(tmp_file)
                    tmp_path = tmp_file.name
                
                print(f"Downloaded to: {tmp_path}")
                
                # Process the file with ingestion pipeline
                collection_name = f"test_collection_{i}"
                result = pipeline.ingest_pptx_file(
                    tmp_path,
                    collection_name,
                    generate_thumbnails=False  # Skip thumbnails for faster testing
                )
                
                print(f"Ingestion result: {result['success']}")
                print(f"Slides processed: {result['slides_processed']}")
                print(f"Templates created: {result['templates_created']}")
                
                results.append(result)
                
                # Clean up temporary file
                Path(tmp_path).unlink(missing_ok=True)
                
            except Exception as e:
                print(f"Error processing {blob.name}: {e}")
                import traceback
                traceback.print_exc()
                results.append({"success": False, "error": str(e)})
        
        # Summary
        print("\n" + "=" * 60)
        print("Ingestion Summary")
        print("=" * 60)
        successful = sum(1 for r in results if r.get("success", False))
        total_slides = sum(r.get("slides_processed", 0) for r in results)
        total_templates = sum(r.get("templates_created", 0) for r in results)
        
        print(f"Files processed: {len(results)}")
        print(f"Successful: {successful}")
        print(f"Total slides processed: {total_slides}")
        print(f"Total templates created: {total_templates}")
        
        # Check database statistics
        stats = db_manager.get_statistics()
        print(f"\nDatabase Statistics:")
        print(f"Collections: {stats['total_collections']}")
        print(f"Templates: {stats['total_templates']}")
        
        return successful == len(results)
        
    except Exception as e:
        print(f"Error during ingestion test: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_ingestion_from_firebase()
    sys.exit(0 if success else 1)
