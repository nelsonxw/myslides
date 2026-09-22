"""
Check how many PowerPoint files are in Firebase Storage.
"""
import sys
from pathlib import Path

# Add src directory to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from myslides.storage.firebase_storage import FirebaseStorageService


def count_pptx_files():
    """Count PPTX files in Firebase Storage."""
    print("Checking Firebase Storage for PowerPoint files...")
    
    storage_service = FirebaseStorageService.get_instance()
    
    if not storage_service.is_connected:
        print("ERROR: Firebase Storage is not connected")
        return
    
    print(f"Connected to bucket: {storage_service.bucket_name}")
    
    # List all files in the bucket
    try:
        all_files = []
        blobs = storage_service.bucket.list_blobs()
        
        pptx_count = 0
        pptx_files = []
        
        for blob in blobs:
            if blob.name.endswith('.pptx'):
                pptx_count += 1
                pptx_files.append({
                    'name': blob.name,
                    'size': blob.size,
                    'updated': blob.updated.isoformat() if blob.updated else None
                })
            all_files.append(blob.name)
        
        print(f"\nTotal files in storage: {len(all_files)}")
        print(f"PowerPoint files (.pptx): {pptx_count}")
        
        if pptx_files:
            print(f"\nPowerPoint files found:")
            for i, file_info in enumerate(pptx_files, 1):
                print(f"{i}. {file_info['name']}")
                print(f"   Size: {file_info['size']} bytes")
                print(f"   Updated: {file_info['updated']}")
        else:
            print("\nNo PowerPoint files found in Firebase Storage")
            
        # Also check specific folders
        print(f"\nChecking specific folders...")
        
        # Check slides folder
        try:
            slides_blobs = list(storage_service.bucket.list_blobs(prefix="slides/"))
            slides_pptx = [b for b in slides_blobs if b.name.endswith('.pptx')]
            print(f"slides/ folder: {len(slides_pptx)} PPTX files")
        except Exception as e:
            print(f"Error checking slides/ folder: {e}")
        
        # Check myslides folder
        try:
            myslides_blobs = list(storage_service.bucket.list_blobs(prefix="myslides/"))
            myslides_pptx = [b for b in myslides_blobs if b.name.endswith('.pptx')]
            print(f"myslides/ folder: {len(myslides_pptx)} PPTX files")
        except Exception as e:
            print(f"Error checking myslides/ folder: {e}")
            
        return pptx_count
        
    except Exception as e:
        print(f"Error listing files: {e}")
        import traceback
        traceback.print_exc()
        return 0


if __name__ == "__main__":
    count = count_pptx_files()
    print(f"\nTotal PPTX files found: {count}")
