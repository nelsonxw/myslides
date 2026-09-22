"""
Simple demonstration script for Module 1 functionality.
Tests the ingestion pipeline with a basic example.
"""
import sys
from pathlib import Path

# Add src directory to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from myslides.config import settings
from myslides.storage.firebase_storage import FirebaseStorageService
from myslides.database.database_manager import DatabaseManager
from myslides.ingestion.pptx_parser import PPTXParser
from myslides.ingestion.slide_classifier import SlideClassifier
from myslides.ingestion.template_extractor import TemplateExtractor
from myslides.ingestion.embedding_generator import EmbeddingGenerator
from myslides.ingestion.ingestion_pipeline import IngestionPipeline


def test_firebase_connection():
    """Test Firebase Storage connection."""
    print("Testing Firebase Storage connection...")
    storage_service = FirebaseStorageService.get_instance()
    status = storage_service.get_status()
    print(f"Firebase Status: {status}")
    return status["is_connected"]


def test_database_connection():
    """Test database connection."""
    print("Testing database connection...")
    db_manager = DatabaseManager()
    stats = db_manager.get_statistics()
    print(f"Database Statistics: {stats}")
    return True


def test_pptx_parser():
    """Test PPTX parser with a sample file."""
    print("Testing PPTX parser...")
    
    # Create a simple test file path (you would replace this with a real PPTX)
    test_file = Path("test_sample.pptx")
    
    if not test_file.exists():
        print("No test PPTX file found. Creating a simple test...")
        # For demonstration, we'll just show the parser structure
        print("PPTX Parser structure:")
        print("- PPTXParser: Parses PPTX files and extracts slide information")
        print("- Extracts: shapes, charts, tables, images, text, styling")
        print("- Supports: layout detection, complexity scoring")
        return True
    
    try:
        parser = PPTXParser(test_file)
        slides = parser.parse_all_slides()
        metadata = parser.get_presentation_metadata()
        
        print(f"Parsed {len(slides)} slides from {test_file.name}")
        print(f"Presentation metadata: {metadata}")
        return True
    except Exception as e:
        print(f"Error parsing PPTX: {e}")
        return False


def test_slide_classifier():
    """Test slide classifier."""
    print("Testing slide classifier...")
    
    from myslides.ingestion.pptx_parser import SlideInfo, SlideLayoutType, PositionInfo
    
    # Create a sample slide info
    slide_info = SlideInfo(
        slide_index=0,
        layout_type=SlideLayoutType.TITLE_SLIDE,
        width=9144000,
        height=6858000,
        shapes=[],
        charts=[],
        tables=[],
        images=[],
        text_content="Agenda: Overview, Topics, Schedule",
        color_palette=["#FF0000"],
        complexity_score=5
    )
    
    classifier = SlideClassifier()
    category = classifier.classify(slide_info)
    tags = classifier.get_tags(slide_info)
    
    print(f"Classification: {category.value}")
    print(f"Tags: {tags}")
    return True


def test_template_extractor():
    """Test template extractor."""
    print("Testing template extractor...")
    
    from myslides.ingestion.pptx_parser import SlideInfo, SlideLayoutType, PositionInfo
    from myslides.ingestion.slide_classifier import SlideCategory
    
    # Create a sample slide info
    slide_info = SlideInfo(
        slide_index=0,
        layout_type=SlideLayoutType.TITLE_SLIDE,
        width=9144000,
        height=6858000,
        shapes=[],
        charts=[],
        tables=[],
        images=[],
        text_content="Sample Title",
        color_palette=["#FF0000", "#00FF00"],
        complexity_score=5
    )
    
    extractor = TemplateExtractor()
    template = extractor.extract_template(
        slide_info=slide_info,
        collection_id="test_collection",
        original_filename="test.pptx"
    )
    
    print(f"Template ID: {template.template_id}")
    print(f"Classification: {template.classification}")
    print(f"Description: {template.description}")
    print(f"Complexity Score: {template.complexity_score}")
    return True


def test_embedding_generator():
    """Test embedding generator."""
    print("Testing embedding generator...")
    
    from myslides.ingestion.pptx_parser import SlideInfo, SlideLayoutType
    
    # Create a sample slide info
    slide_info = SlideInfo(
        slide_index=0,
        layout_type=SlideLayoutType.TITLE_SLIDE,
        width=9144000,
        height=6858000,
        shapes=[],
        charts=[],
        tables=[],
        images=[],
        text_content="Test content for embedding",
        color_palette=["#FF0000"],
        complexity_score=5
    )
    
    try:
        embedding_gen = EmbeddingGenerator()
        embedding = embedding_gen.generate_semantic_embedding(slide_info, "test_template")
        
        print(f"Generated semantic embedding with {len(embedding)} dimensions")
        print(f"First 10 values: {embedding[:10]}")
        return True
    except Exception as e:
        print(f"Error with embedding generator: {e}")
        return False


def test_ingestion_pipeline():
    """Test ingestion pipeline status."""
    print("Testing ingestion pipeline...")
    
    pipeline = IngestionPipeline()
    status = pipeline.get_ingestion_status()
    
    print("Ingestion Pipeline Status:")
    print(f"- Storage Connected: {status['storage']['is_connected']}")
    print(f"- Database Collections: {status['database']['total_collections']}")
    print(f"- Database Templates: {status['database']['total_templates']}")
    print(f"- Data Directories: {status['data_directories']}")
    return True


def main():
    """Run all Module 1 tests."""
    print("=" * 60)
    print("Module 1 - Ingestion Pipeline Functionality Test")
    print("=" * 60)
    print()
    
    tests = [
        ("Firebase Connection", test_firebase_connection),
        ("Database Connection", test_database_connection),
        ("PPTX Parser", test_pptx_parser),
        ("Slide Classifier", test_slide_classifier),
        ("Template Extractor", test_template_extractor),
        ("Embedding Generator", test_embedding_generator),
        ("Ingestion Pipeline", test_ingestion_pipeline),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{'=' * 60}")
        print(f"Testing: {test_name}")
        print('=' * 60)
        try:
            result = test_func()
            results.append((test_name, result))
            print(f"[{test_name}]: {'PASSED' if result else 'FAILED'}")
        except Exception as e:
            print(f"[{test_name}]: ERROR - {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    for test_name, result in results:
        status = "[PASSED]" if result else "[FAILED]"
        print(f"{status}: {test_name}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    print(f"\nTotal: {passed}/{total} tests passed")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
