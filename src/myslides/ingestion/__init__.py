"""
Ingestion module for MySlides.
Handles PPTX parsing, slide classification, template extraction, and embedding generation.
"""

from .pptx_parser import PPTXParser
from .slide_classifier import SlideClassifier
from .template_extractor import TemplateExtractor
from .embedding_generator import EmbeddingGenerator
from .ingestion_pipeline import IngestionPipeline

__all__ = ["PPTXParser", "SlideClassifier", "TemplateExtractor", "EmbeddingGenerator", "IngestionPipeline"]
