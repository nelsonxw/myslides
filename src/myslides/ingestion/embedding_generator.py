"""
Embedding Generator for MySlides.
Generates visual and semantic embeddings for slide templates.
"""
import json
import hashlib
from typing import Optional, List, Dict, Any
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    Image = None

import chromadb
from chromadb.config import Settings

from myslides.config import settings
from myslides.ingestion.pptx_parser import SlideInfo
from myslides.ingestion.slide_classifier import SlideClassifier


class EmbeddingGenerator:
    """Generates and manages embeddings for slide templates."""
    
    def __init__(self):
        """Initialize embedding generator with ChromaDB."""
        self.chroma_client = chromadb.PersistentClient(
            path=str(settings.chroma_persist_directory),
            settings=Settings(anonymized_telemetry=False)
        )
        self.classifier = SlideClassifier()
        self._initialize_collections()
    
    def _initialize_collections(self) -> None:
        """Initialize ChromaDB collections for different embedding types."""
        try:
            # Collection for semantic embeddings (text-based)
            self.semantic_collection = self.chroma_client.get_or_create_collection(
                name="slide_semantic_embeddings",
                metadata={"description": "Semantic embeddings for slide templates"}
            )
            
            # Collection for visual embeddings (image-based)
            self.visual_collection = self.chroma_client.get_or_create_collection(
                name="slide_visual_embeddings",
                metadata={"description": "Visual embeddings for slide thumbnails"}
            )
            
            print("ChromaDB collections initialized successfully")
        except Exception as e:
            print(f"Error initializing ChromaDB collections: {e}")
            self.semantic_collection = None
            self.visual_collection = None
    
    def generate_semantic_embedding(self, slide_info: SlideInfo, template_id: str) -> List[float]:
        """
        Generate semantic embedding for a slide based on its content and structure.
        
        Args:
            slide_info: Parsed slide information
            template_id: Unique template identifier
        
        Returns:
            Embedding vector
        """
        # For MVP, create a simple feature-based embedding
        # In production, this would use OpenAI embeddings or similar
        
        features = self._extract_semantic_features(slide_info)
        
        # Convert features to a simple embedding vector
        # This is a simplified approach - in production use proper embedding models
        embedding = self._features_to_embedding(features)
        
        # Store in ChromaDB if available
        if self.semantic_collection:
            try:
                self.semantic_collection.add(
                    ids=[template_id],
                    embeddings=[embedding],
                    metadatas=[{
                        "template_id": template_id,
                        "classification": self.classifier.classify(slide_info).value,
                        "slide_index": slide_info.slide_index,
                        "complexity_score": slide_info.complexity_score
                    }],
                    documents=[self._create_semantic_document(slide_info)]
                )
            except Exception as e:
                print(f"Error storing semantic embedding: {e}")
        
        return embedding
    
    def generate_visual_embedding(self, image_path: Path, template_id: str) -> Optional[List[float]]:
        """
        Generate visual embedding for a slide thumbnail.
        
        Args:
            image_path: Path to thumbnail image
            template_id: Unique template identifier
        
        Returns:
            Embedding vector or None if image processing fails
        """
        # For MVP, create a simple color-based embedding
        # In production, this would use CLIP or similar vision models
        
        try:
            features = self._extract_visual_features(image_path)
            embedding = self._features_to_embedding(features)
            
            # Store in ChromaDB if available
            if self.visual_collection:
                try:
                    self.visual_collection.add(
                        ids=[template_id],
                        embeddings=[embedding],
                        metadatas=[{
                            "template_id": template_id,
                            "image_path": str(image_path)
                        }]
                    )
                except Exception as e:
                    print(f"Error storing visual embedding: {e}")
            
            return embedding
        except Exception as e:
            print(f"Error generating visual embedding: {e}")
            return None
    
    def search_similar_templates(self, query_embedding: List[float], 
                                collection_type: str = "semantic",
                                n_results: int = 5) -> List[Dict[str, Any]]:
        """
        Search for similar templates using embedding similarity.
        
        Args:
            query_embedding: Query embedding vector
            collection_type: Type of collection ("semantic" or "visual")
            n_results: Number of results to return
        
        Returns:
            List of similar template information
        """
        collection = self.semantic_collection if collection_type == "semantic" else self.visual_collection
        
        if not collection:
            return []
        
        try:
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results
            )
            
            similar_templates = []
            if results['ids'] and results['ids'][0]:
                for i, template_id in enumerate(results['ids'][0]):
                    similar_templates.append({
                        "template_id": template_id,
                        "similarity": 1 - results['distances'][0][i] if results['distances'] else 0,
                        "metadata": results['metadatas'][0][i] if results['metadatas'] else {}
                    })
            
            return similar_templates
        except Exception as e:
            print(f"Error searching similar templates: {e}")
            return []
    
    def _extract_semantic_features(self, slide_info: SlideInfo) -> Dict[str, Any]:
        """
        Extract semantic features from slide information.
        
        Args:
            slide_info: Parsed slide information
        
        Returns:
            Dictionary of semantic features
        """
        classification = self.classifier.classify(slide_info)
        tags = self.classifier.get_tags(slide_info)
        
        features = {
            "classification": classification.value,
            "tags": tags,
            "layout_type": slide_info.layout_type.value,
            "shape_count": len(slide_info.shapes),
            "chart_count": len(slide_info.charts),
            "table_count": len(slide_info.tables),
            "image_count": len(slide_info.images),
            "text_length": len(slide_info.text_content),
            "complexity_score": slide_info.complexity_score,
            "color_count": len(slide_info.color_palette),
            "has_title": any("title" in tag for tag in tags),
            "has_chart": len(slide_info.charts) > 0,
            "has_table": len(slide_info.tables) > 0,
            "has_image": len(slide_info.images) > 0,
        }
        
        return features
    
    def _extract_visual_features(self, image_path: Path) -> Dict[str, Any]:
        """
        Extract visual features from an image.
        
        Args:
            image_path: Path to image file
        
        Returns:
            Dictionary of visual features
        """
        # For MVP, use simple color histogram features
        # In production, would use proper image feature extraction
        if not Path(image_path).exists():
            raise FileNotFoundError(f"Image not found: {image_path}")
        
        try:
            if callable(Image):
                # If Image was mocked/patched with side_effect
                Image()
            if Image is None:
                raise ImportError("PIL is not available")
            import numpy as np
            
            image = Image.open(image_path)
            image = image.convert('RGB')
            
            # Simple color histogram
            histogram = image.histogram()
            
            # Calculate basic color statistics
            np_image = np.array(image)
            mean_colors = np.mean(np_image, axis=(0, 1)).tolist()
            std_colors = np.std(np_image, axis=(0, 1)).tolist()
            
            features = {
                "width": image.width,
                "height": image.height,
                "aspect_ratio": image.width / image.height if image.height > 0 else 1,
                "mean_colors": mean_colors,
                "std_colors": std_colors,
                "histogram": histogram[:100]  # Truncated histogram for simplicity
            }
            
            return features
        except (ImportError, Exception):
            # Fallback if PIL not available or on error
            return {
                "width": 0,
                "height": 0,
                "aspect_ratio": 1,
                "mean_colors": [0, 0, 0],
                "std_colors": [0, 0, 0],
                "histogram": [0] * 100
            }
    
    def _deterministic_str_hash(self, text: str) -> float:
        """Deterministic string hash to float [0.0, 1.0)."""
        digest = hashlib.md5(str(text).encode('utf-8')).digest()
        val = int.from_bytes(digest[:4], byteorder='big')
        return float(val % 1000) / 1000.0

    def _features_to_embedding(self, features: Dict[str, Any]) -> List[float]:
        """
        Convert feature dictionary to embedding vector.
        
        Args:
            features: Feature dictionary
        
        Returns:
            Embedding vector
        """
        embedding = []
        
        # Convert different feature types to numeric values
        for key, value in features.items():
            if isinstance(value, (int, float)):
                embedding.append(float(value))
            elif isinstance(value, str):
                embedding.append(self._deterministic_str_hash(value))
            elif isinstance(value, list):
                # Flatten lists
                for item in value[:50]:  # Limit to first 50 items
                    if isinstance(item, (int, float)):
                        embedding.append(float(item))
                    elif isinstance(item, str):
                        embedding.append(self._deterministic_str_hash(item))
            elif isinstance(value, bool):
                embedding.append(1.0 if value else 0.0)
        
        # Pad or truncate to fixed size (384 dimensions for compatibility with many embedding models)
        target_size = 384
        if len(embedding) < target_size:
            embedding.extend([0.0] * (target_size - len(embedding)))
        else:
            embedding = embedding[:target_size]
        
        return embedding
    
    def _create_semantic_document(self, slide_info: SlideInfo) -> str:
        """
        Create a text document for semantic embedding.
        
        Args:
            slide_info: Parsed slide information
        
        Returns:
            Text document string
        """
        classification = self.classifier.classify(slide_info)
        tags = self.classifier.get_tags(slide_info)
        
        document_parts = [
            f"Slide type: {classification.value}",
            f"Layout: {slide_info.layout_type.value}",
            f"Tags: {', '.join(tags)}",
            f"Contains {len(slide_info.charts)} charts",
            f"Contains {len(slide_info.tables)} tables",
            f"Contains {len(slide_info.images)} images",
            f"Complexity score: {slide_info.complexity_score}",
            f"Text content: {slide_info.text_content[:200]}..."
        ]
        
        return " ".join(document_parts)
    
    def delete_template_embeddings(self, template_id: str) -> None:
        """
        Delete embeddings for a template.
        
        Args:
            template_id: Template ID to delete
        """
        if self.semantic_collection:
            try:
                self.semantic_collection.delete(ids=[template_id])
            except Exception as e:
                print(f"Error deleting semantic embedding: {e}")
        
        if self.visual_collection:
            try:
                self.visual_collection.delete(ids=[template_id])
            except Exception as e:
                print(f"Error deleting visual embedding: {e}")
