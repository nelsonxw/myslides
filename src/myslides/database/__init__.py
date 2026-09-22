"""
Database module for MySlides.
Handles SQLite database operations for storing templates and collections.
"""

from .models import SlideCollection, SlideTemplate, GenerationRequest
from .database_manager import DatabaseManager

__all__ = ["SlideCollection", "SlideTemplate", "GenerationRequest", "DatabaseManager"]
