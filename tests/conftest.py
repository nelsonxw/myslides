"""
Pytest configuration and shared fixtures for MySlides tests.
"""
import pytest
import sys
from pathlib import Path

# Add the src directory to the Python path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))


@pytest.fixture
def sample_data_dir(tmp_path):
    """Create a sample data directory for testing."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "uploads").mkdir()
    (data_dir / "templates").mkdir()
    (data_dir / "thumbnails").mkdir()
    (data_dir / "chroma_db").mkdir()
    return data_dir
