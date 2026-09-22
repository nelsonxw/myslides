"""
Test runner script for MySlides application.
"""
import sys
import subprocess
from pathlib import Path

def run_tests():
    """Run all tests for the MySlides application."""
    # Add src directory to path
    src_path = Path(__file__).parent / "src"
    sys.path.insert(0, str(src_path))
    
    # Run pytest
    result = subprocess.run(
        ["python", "-m", "pytest", "tests/", "-v", "--tb=short"],
        cwd=Path(__file__).parent
    )
    
    return result.returncode

if __name__ == "__main__":
    sys.exit(run_tests())
