"""
Ingest all 1,528 PowerPoint slides from Firebase Storage.
Complete classification, embedding generation, and storage for the entire template catalog.
"""
import sys
import time
from pathlib import Path
import tempfile
from datetime import datetime
from typing import List, Dict

# Add src directory to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from myslides.storage.firebase_storage import FirebaseStorageService
from myslides.ingestion.ingestion_pipeline import IngestionPipeline
from myslides.database.database_manager import DatabaseManager


class BatchIngestionProcessor:
    """Process large batches of PPTX files with progress tracking."""
    
    def __init__(self, batch_size: int = 50):
        """
        Initialize the batch processor.
        
        Args:
            batch_size: Number of files to process in each batch
        """
        self.batch_size = batch_size
        self.storage_service = FirebaseStorageService.get_instance()
        self.pipeline = IngestionPipeline()
        self.db_manager = DatabaseManager()
        
        # Statistics
        self.total_files = 0
        self.processed_files = 0
        self.successful_files = 0
        self.failed_files = 0
        self.total_slides_processed = 0
        self.total_templates_created = 0
        self.errors = []
        self.start_time = None
        
    def get_all_pptx_files(self) -> List:
        """Get all PPTX files from Firebase Storage."""
        print("Scanning Firebase Storage for PPTX files...")
        
        all_blobs = list(self.storage_service.bucket.list_blobs(prefix="curated slides/"))
        pptx_blobs = [b for b in all_blobs if b.name.endswith('.pptx')]
        
        self.total_files = len(pptx_blobs)
        print(f"Found {self.total_files} PPTX files to process")
        
        return pptx_blobs
    
    def process_file(self, blob, index: int) -> Dict:
        """
        Process a single PPTX file.
        
        Args:
            blob: Firebase Storage blob object
            index: File index for progress tracking
        
        Returns:
            Dictionary with processing results
        """
        file_name = blob.name.split('/')[-1]
        collection_name = f"collection_{index}"
        
        result = {
            "index": index,
            "file_name": file_name,
            "storage_path": blob.name,
            "success": False,
            "slides_processed": 0,
            "templates_created": 0,
            "error": None,
            "processing_time": 0
        }
        
        start_time = time.time()
        
        try:
            # Download file to temporary location
            with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as tmp_file:
                blob.download_to_file(tmp_file)
                tmp_path = tmp_file.name
            
            # Process the file with ingestion pipeline
            ingest_result = self.pipeline.ingest_pptx_file(
                tmp_path,
                collection_name,
                generate_thumbnails=False  # Skip thumbnails for faster processing
            )
            
            result["success"] = ingest_result["success"]
            result["slides_processed"] = ingest_result["slides_processed"]
            result["templates_created"] = ingest_result["templates_created"]
            result["error"] = ingest_result.get("errors")
            
            # Clean up temporary file
            Path(tmp_path).unlink(missing_ok=True)
            
        except Exception as e:
            result["error"] = str(e)
            print(f"Error processing {file_name}: {e}")
        
        result["processing_time"] = time.time() - start_time
        return result
    
    def process_batch(self, blobs: List, start_index: int) -> Dict:
        """
        Process a batch of PPTX files.
        
        Args:
            blobs: List of Firebase Storage blobs
            start_index: Starting index for this batch
        
        Returns:
            Dictionary with batch processing results
        """
        batch_results = {
            "batch_number": (start_index // self.batch_size) + 1,
            "total_files": len(blobs),
            "successful": 0,
            "failed": 0,
            "total_slides": 0,
            "total_templates": 0,
            "processing_time": 0,
            "results": []
        }
        
        print(f"\nProcessing batch {batch_results['batch_number']} ({len(blobs)} files)...")
        batch_start_time = time.time()
        
        for i, blob in enumerate(blobs):
            file_index = start_index + i
            print(f"[{file_index + 1}/{self.total_files}] Processing: {blob.name.split('/')[-1]}")
            
            result = self.process_file(blob, file_index)
            batch_results["results"].append(result)
            
            # Update statistics
            if result["success"]:
                batch_results["successful"] += 1
                batch_results["total_slides"] += result["slides_processed"]
                batch_results["total_templates"] += result["templates_created"]
            else:
                batch_results["failed"] += 1
                if result["error"]:
                    self.errors.append({
                        "file": result["file_name"],
                        "error": result["error"]
                    })
            
            # Update global statistics
            self.processed_files += 1
            if result["success"]:
                self.successful_files += 1
                self.total_slides_processed += result["slides_processed"]
                self.total_templates_created += result["templates_created"]
            else:
                self.failed_files += 1
            
            # Progress update
            self.print_progress()
        
        batch_results["processing_time"] = time.time() - batch_start_time
        
        print(f"\nBatch {batch_results['batch_number']} completed:")
        print(f"  Successful: {batch_results['successful']}/{batch_results['total_files']}")
        print(f"  Slides processed: {batch_results['total_slides']}")
        print(f"  Templates created: {batch_results['total_templates']}")
        print(f"  Time: {batch_results['processing_time']:.2f}s")
        
        return batch_results
    
    def print_progress(self):
        """Print current progress statistics."""
        if self.start_time:
            elapsed = time.time() - self.start_time
            progress_percent = (self.processed_files / self.total_files) * 100
            
            # Calculate estimated time remaining
            if self.processed_files > 0:
                avg_time_per_file = elapsed / self.processed_files
                remaining_files = self.total_files - self.processed_files
                eta = avg_time_per_file * remaining_files
                eta_str = f"{eta/60:.1f}m" if eta > 60 else f"{eta:.1f}s"
            else:
                eta_str = "calculating..."
            
            print(f"  Progress: {progress_percent:.1f}% ({self.processed_files}/{self.total_files}) | "
                  f"Success: {self.successful_files} | "
                  f"Slides: {self.total_slides_processed} | "
                  f"Templates: {self.total_templates_created} | "
                  f"ETA: {eta_str}")
    
    def process_all_files(self):
        """Process all PPTX files in batches."""
        print("=" * 70)
        print("FULL CATALOG INGESTION - All 1,528 PowerPoint Slides")
        print("=" * 70)
        
        # Get all files
        blobs = self.get_all_pptx_files()
        
        if not blobs:
            print("No PPTX files found to process")
            return
        
        self.start_time = time.time()
        print(f"Starting ingestion at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Batch size: {self.batch_size}")
        print(f"Estimated total time: ~{(self.total_files * 2) / 60:.1f} minutes")
        print()
        
        # Process in batches
        batch_results = []
        for i in range(0, len(blobs), self.batch_size):
            batch = blobs[i:i + self.batch_size]
            batch_result = self.process_batch(batch, i)
            batch_results.append(batch_result)
            
            # Small delay between batches to prevent overwhelming the system
            if i + self.batch_size < len(blobs):
                time.sleep(1)
        
        # Final summary
        total_time = time.time() - self.start_time
        self.print_final_summary(total_time, batch_results)
        
        # Save detailed results
        self.save_results_to_file(batch_results)
    
    def print_final_summary(self, total_time: float, batch_results: List):
        """Print final processing summary."""
        print("\n" + "=" * 70)
        print("INGESTION COMPLETE - FINAL SUMMARY")
        print("=" * 70)
        print(f"Total processing time: {total_time / 60:.2f} minutes ({total_time:.2f} seconds)")
        print(f"Files processed: {self.processed_files}/{self.total_files}")
        print(f"Successful: {self.successful_files} ({(self.successful_files/self.total_files)*100:.1f}%)")
        print(f"Failed: {self.failed_files}")
        print(f"Total slides processed: {self.total_slides_processed}")
        print(f"Total templates created: {self.total_templates_created}")
        print(f"Average time per file: {total_time/self.processed_files:.2f}s")
        
        # Database statistics
        final_stats = self.db_manager.get_statistics()
        print(f"\nFinal Database Statistics:")
        print(f"  Collections: {final_stats['total_collections']}")
        print(f"  Templates: {final_stats['total_templates']}")
        print(f"  Generation Requests: {final_stats['total_requests']}")
        print(f"  Decks: {final_stats['total_decks']}")
        
        # Classification breakdown
        if final_stats['classification_breakdown']:
            print(f"\nClassification Breakdown:")
            for classification, count in sorted(final_stats['classification_breakdown'].items(), 
                                               key=lambda x: x[1], reverse=True):
                print(f"  {classification}: {count}")
        
        # Errors summary
        if self.errors:
            print(f"\nErrors encountered: {len(self.errors)}")
            print("First 10 errors:")
            for error in self.errors[:10]:
                print(f"  - {error['file']}: {error['error']}")
            if len(self.errors) > 10:
                print(f"  ... and {len(self.errors) - 10} more errors")
    
    def save_results_to_file(self, batch_results: List):
        """Save detailed results to a file."""
        results_file = Path(__file__).parent.parent / "data" / "ingestion_results.json"
        results_file.parent.mkdir(parents=True, exist_ok=True)
        
        import json
        results_data = {
            "timestamp": datetime.now().isoformat(),
            "total_files": self.total_files,
            "processed_files": self.processed_files,
            "successful_files": self.successful_files,
            "failed_files": self.failed_files,
            "total_slides_processed": self.total_slides_processed,
            "total_templates_created": self.total_templates_created,
            "processing_time_seconds": time.time() - self.start_time,
            "batch_results": batch_results,
            "errors": self.errors
        }
        
        with open(results_file, 'w') as f:
            json.dump(results_data, f, indent=2)
        
        print(f"\nDetailed results saved to: {results_file}")


def main():
    """Main entry point for full catalog ingestion."""
    # You can adjust batch size based on your system performance
    # Smaller batch size = more progress updates but potentially slower overall
    # Larger batch size = fewer progress updates but potentially faster overall
    processor = BatchIngestionProcessor(batch_size=50)
    
    try:
        processor.process_all_files()
        print("\n✓ Full catalog ingestion completed successfully!")
        return 0
    except KeyboardInterrupt:
        print("\n\nIngestion interrupted by user")
        print(f"Progress: {processor.processed_files}/{processor.total_files} files processed")
        print(f"Templates created: {processor.total_templates_created}")
        return 1
    except Exception as e:
        print(f"\n✗ Error during ingestion: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
