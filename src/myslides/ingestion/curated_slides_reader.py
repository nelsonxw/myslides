"""
Curated Slides Reader for MySlides.

Handles reading, listing, syncing, and cataloging training slides
directly from the Firebase Storage 'curated slides' folder.
"""
import json
import logging
import tempfile
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from myslides.config import settings
from myslides.database.database_manager import DatabaseManager
from myslides.database.models import SlideCollection, SlideTemplate
from myslides.ingestion.embedding_generator import EmbeddingGenerator
from myslides.ingestion.pptx_parser import (
    PPTXParser,
    SlideInfo,
    ShapeInfo,
    PositionInfo,
    TextContent,
    FontInfo,
    SlideLayoutType,
)
from myslides.ingestion.slide_classifier import SlideClassifier
from myslides.ingestion.template_extractor import TemplateExtractor
from myslides.storage.firebase_storage import FirebaseStorageService

logger = logging.getLogger(__name__)


@dataclass
class CuratedSlideItem:
    """Representation of a curated training slide from Firebase Storage."""
    name: str
    storage_path: str
    size: int
    updated: Optional[str]
    download_url: str
    public_url: str
    template_id: Optional[int] = None
    classification: Optional[str] = None
    tags: Optional[List[str]] = None
    is_indexed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert dataclass to dictionary."""
        return asdict(self)


class CuratedSlidesReader:
    """Service for managing training slides sourced from Firebase Storage 'curated slides' folder."""

    def __init__(
        self,
        storage_service: Optional[FirebaseStorageService] = None,
        database_manager: Optional[DatabaseManager] = None,
        embedding_generator: Optional[EmbeddingGenerator] = None,
        template_extractor: Optional[TemplateExtractor] = None,
        slide_classifier: Optional[SlideClassifier] = None,
    ):
        """Initialize CuratedSlidesReader with required services."""
        self.storage_service = storage_service or FirebaseStorageService.get_instance()
        self.database_manager = database_manager or DatabaseManager()
        self.embedding_generator = embedding_generator or EmbeddingGenerator()
        self.template_extractor = template_extractor or TemplateExtractor()
        self.slide_classifier = slide_classifier or SlideClassifier()
        self.storage_prefix = "curated slides/"

    def list_training_slides(self) -> List[CuratedSlideItem]:
        """
        List all training slides in Firebase Storage 'curated slides' folder,
        merged with local database indexing metadata.
        """
        storage_slides = self.storage_service.list_curated_slides(prefix=self.storage_prefix)
        indexed_map = self._get_indexed_templates_map()

        items: List[CuratedSlideItem] = []
        for s in storage_slides:
            filename = s["name"]
            storage_path = s["storage_path"]
            indexed_info = indexed_map.get(filename) or indexed_map.get(storage_path)

            item = CuratedSlideItem(
                name=filename,
                storage_path=storage_path,
                size=s.get("size", 0),
                updated=s.get("updated"),
                download_url=s.get("download_url", ""),
                public_url=s.get("public_url", ""),
                template_id=indexed_info.get("template_id") if indexed_info else None,
                classification=indexed_info.get("classification") if indexed_info else None,
                tags=indexed_info.get("tags") if indexed_info else None,
                is_indexed=indexed_info is not None,
            )
            items.append(item)

        return items

    def get_catalog_status(self) -> Dict[str, Any]:
        """Get summary status of curated training slides."""
        all_slides = self.list_training_slides()
        indexed_count = sum(1 for s in all_slides if s.is_indexed)

        stats = self.database_manager.get_statistics()
        return {
            "firebase_connected": self.storage_service.is_connected,
            "storage_bucket": self.storage_service.bucket_name,
            "curated_slides_folder": self.storage_prefix,
            "total_curated_in_storage": len(all_slides),
            "total_curated_indexed": indexed_count,
            "total_templates_in_db": stats.get("total_templates", 0),
            "total_collections_in_db": stats.get("total_collections", 0),
        }

    def ingest_curated_slide(self, storage_path: str, force: bool = False, skip_llm: bool = False) -> Dict[str, Any]:
        """
        Ingest a single curated slide from Firebase Storage into the catalog.

        Args:
            storage_path: Full path in Firebase Storage (e.g. 'curated slides/xyz.pptx')
            force: Re-ingest even if already cataloged
            skip_llm: Skip LLM classification and embedding (for faster sync)

        Returns:
            Dictionary with ingestion result
        """
        filename = storage_path.split("/")[-1]

        if not force:
            existing = self._find_existing_template(filename, storage_path)
            if existing:
                return {
                    "success": True,
                    "already_indexed": True,
                    "template_id": existing.id,
                    "file_name": filename,
                    "storage_path": storage_path,
                }

        temp_dir = Path(tempfile.mkdtemp())
        local_path = temp_dir / filename

        try:
            self.storage_service.download_file(storage_path, local_path)

            parser = PPTXParser(local_path)
            slide_info = parser.parse_slide(slide_index=0)
            presentation_metadata = parser.get_presentation_metadata()

            collection = self.database_manager.create_collection(
                file_name=filename,
                storage_path=storage_path,
                total_slides=1,
                collection_metadata={
                    **presentation_metadata,
                    "source": "curated_slides_folder",
                    "storage_path": storage_path,
                },
            )

            if skip_llm:
                # Use simple placeholder classification for fast sync
                classification = "mixed"
                tags = ["pending_reindex"]
                semantic_embedding = [0.0] * 384  # Placeholder, will be updated during re-index
            else:
                try:
                    classification_category = self.slide_classifier.classify(slide_info)
                    classification = classification_category.value if hasattr(classification_category, "value") else str(classification_category)
                    tags = self.slide_classifier.get_tags(slide_info)
                except RuntimeError as e:
                    # If Gemini fails during sync, use placeholder
                    classification = "mixed"
                    tags = ["pending_reindex", "llm_failed"]
                    logger.warning(f"LLM classification failed for {filename}, using placeholder: {e}")

            extracted_template = self.template_extractor.extract_template(
                slide_info=slide_info,
                collection_id=str(collection.id),
                original_filename=filename,
                thumbnail_path=None,
            )

            template_hash = self.template_extractor.calculate_template_hash(slide_info)
            template_id_str = f"curated_{collection.id}_0"

            if not skip_llm:
                try:
                    semantic_embedding = self.embedding_generator.generate_semantic_embedding(
                        slide_info=slide_info,
                        template_id=template_id_str,
                    )
                except RuntimeError as e:
                    # If Gemini embedding fails, use placeholder
                    semantic_embedding = [0.0] * 384
                    logger.warning(f"LLM embedding failed for {filename}, using placeholder: {e}")
            else:
                semantic_embedding = [0.0] * 384  # Placeholder

            template_data = {
                "collection_id": collection.id,
                "slide_index": 0,
                "classification": classification,
                "tags": tags,
                "thumbnail_path": None,
                "original_pptx_reference": storage_path,
                "element_manifest": extracted_template.element_manifest,
                "placeholder_map": extracted_template.placeholder_map,
                "color_palette": extracted_template.color_palette,
                "complexity_score": extracted_template.complexity_score,
                "description": extracted_template.description,
                "template_hash": template_hash,
                "visual_embedding": None,
                "semantic_embedding": semantic_embedding,
            }

            db_template = self.database_manager.create_template(template_data)

            return {
                "success": True,
                "already_indexed": False,
                "template_id": db_template.id,
                "collection_id": collection.id,
                "file_name": filename,
                "storage_path": storage_path,
                "classification": classification,
            }

        except Exception as e:
            logger.error("Failed to ingest curated slide %s: %s", storage_path, e)
            return {
                "success": False,
                "error": str(e),
                "file_name": filename,
                "storage_path": storage_path,
            }
        finally:
            if local_path.exists():
                local_path.unlink(missing_ok=True)
            if temp_dir.exists():
                try:
                    temp_dir.rmdir()
                except OSError:
                    pass

    def sync_all_curated_slides(self, limit: Optional[int] = None) -> Dict[str, Any]:
        """
        Sync all curated slides from Firebase Storage into the local database catalog.
        Skips already indexed slides. Uses skip_llm=True for fast sync without Gemini calls.
        """
        all_slides = self.storage_service.list_curated_slides(prefix=self.storage_prefix)
        indexed_map = self._get_indexed_templates_map()

        pending_slides = [s for s in all_slides if s["name"] not in indexed_map and s["storage_path"] not in indexed_map]

        if limit is not None:
            pending_slides = pending_slides[:limit]

        synced_count = 0
        failed_count = 0
        errors: List[Dict[str, str]] = []

        for slide in pending_slides:
            res = self.ingest_curated_slide(slide["storage_path"], skip_llm=True)
            if res.get("success"):
                synced_count += 1
            else:
                failed_count += 1
                errors.append({"file": slide["name"], "error": res.get("error", "Unknown error")})

        return {
            "total_found": len(all_slides),
            "total_pending": len(pending_slides),
            "synced_count": synced_count,
            "failed_count": failed_count,
            "errors": errors,
        }

    def sync_and_reindex_all(self, limit: Optional[int] = None, progress_callback=None) -> Dict[str, Any]:
        """
        Combined operation: sync new slides from Firebase Storage (fast, no LLM), then re-index all with Gemini Flash.

        Args:
            limit: Optional limit on number of slides to process
            progress_callback: Optional callback for progress updates

        Returns:
            Dictionary with combined results
        """
        start_time = time.time()
        # Sync phase: fast, skips LLM calls
        sync_result = self.sync_all_curated_slides(limit=limit)

        # Re-index phase: processes ALL slides with Gemini Flash (including newly synced ones)
        reindex_result = self.reindex_all_curated_slides(
            progress_callback=progress_callback,
            limit=None  # Re-index all slides, not just the synced ones
        )

        elapsed = time.time() - start_time
        return {
            "success": True,
            "sync": sync_result,
            "reindex": reindex_result,
            "total_time_seconds": round(elapsed, 2)
        }

    def reconcile_from_ingestion_results(self, results_json_path: Optional[Path] = None) -> Dict[str, Any]:
        """
        Reconcile database records with the true Firebase Storage 'curated slides' paths.
        Uses historical ingestion results to map temporary collection names to true filenames.
        """
        if results_json_path is None:
            results_json_path = settings.data_dir / "ingestion_results.json"

        if not results_json_path.exists():
            return {"success": False, "reason": "ingestion_results.json not found"}

        with open(results_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        results: List[Dict[str, Any]] = []
        for batch in data.get("batch_results", []):
            results.extend(batch.get("results", []))

        updated_collections = 0
        updated_templates = 0

        with self.database_manager.get_session() as session:
            for item in results:
                idx = item.get("index")
                real_filename = item.get("file_name")
                real_storage_path = item.get("storage_path")

                if idx is None or not real_filename or not real_storage_path:
                    continue

                collection = session.query(SlideCollection).filter(
                    SlideCollection.storage_path.like(f"%collection_{idx}/%")
                ).first()

                if collection:
                    if collection.file_name != real_filename or collection.storage_path != real_storage_path:
                        collection.file_name = real_filename
                        collection.storage_path = real_storage_path
                        updated_collections += 1

                    template = session.query(SlideTemplate).filter(
                        SlideTemplate.collection_id == collection.id
                    ).first()
                    if template and template.original_pptx_reference != real_storage_path:
                        template.original_pptx_reference = real_storage_path
                        updated_templates += 1

            session.commit()

        return {
            "success": True,
            "total_mappings": len(results),
            "updated_collections": updated_collections,
            "updated_templates": updated_templates,
        }

    def reindex_all_curated_slides(self, progress_callback=None, limit: Optional[int] = None) -> Dict[str, Any]:
        """
        Manually re-run classification and vectorization for all training slides.
        Updates classifications, tags, and 384-d semantic embeddings in ChromaDB.
        Includes rate limiting to stay within Gemini API free tier quota (15 requests/minute).
        """
        start_time = time.time()
        categories_summary: Dict[str, int] = {}
        processed = 0

        with self.database_manager.get_session() as session:
            query = session.query(SlideTemplate)
            if limit:
                query = query.limit(limit)
            templates = query.all()
            total = len(templates)

            for i, template in enumerate(templates):
                manifest = template.element_manifest or {}
                shapes = []
                all_texts = []
                for sh in manifest.get("shapes", []):
                    pos_d = sh.get("position", {})
                    pos = PositionInfo(
                        x=pos_d.get("x", 0),
                        y=pos_d.get("y", 0),
                        width=pos_d.get("width", 0),
                        height=pos_d.get("height", 0)
                    )
                    txt = None
                    raw_t = sh.get("text")
                    if isinstance(raw_t, dict) and raw_t.get("content"):
                        text_str = str(raw_t["content"])
                        all_texts.append(text_str)
                        txt = TextContent(text=text_str, font=FontInfo("Calibri", 11, False, False, False, None), paragraphs=[text_str])
                    elif isinstance(raw_t, str) and raw_t:
                        all_texts.append(raw_t)
                        txt = TextContent(text=raw_t, font=FontInfo("Calibri", 11, False, False, False, None), paragraphs=[raw_t])

                    shapes.append(ShapeInfo(
                        shape_id=sh.get("shape_id", 0),
                        shape_type=str(sh.get("shape_type", "unknown")),
                        name=sh.get("name", ""),
                        position=pos,
                        fill_color=None,
                        line_color=None,
                        text_content=txt,
                        is_grouped=bool(sh.get("is_grouped", False)),
                        group_id=None
                    ))

                dim = manifest.get("slide_dimensions", {})
                slide_info = SlideInfo(
                    slide_index=template.slide_index,
                    layout_type=SlideLayoutType.CONTENT_SLIDE,
                    width=dim.get("width", 9144000),
                    height=dim.get("height", 5143500),
                    shapes=shapes,
                    charts=[],
                    tables=[],
                    images=[],
                    text_content=" ".join(all_texts),
                    color_palette=template.color_palette or [],
                    complexity_score=template.complexity_score or 5
                )

                # 1. Re-classify (using Gemini Flash LLM)
                try:
                    category = self.slide_classifier.classify(slide_info)
                    cat_val = category.value if hasattr(category, "value") else str(category)
                    tags = self.slide_classifier.get_tags(slide_info)
                except RuntimeError as e:
                    # If Gemini fails, skip this slide and continue
                    logger.error(f"Failed to classify slide {template.id}: {e}")
                    continue

                categories_summary[cat_val] = categories_summary.get(cat_val, 0) + 1

                # 2. Re-generate vector embedding & upsert into ChromaDB (using Gemini Embeddings)
                try:
                    template_id_str = str(template.id)
                    embedding = self.embedding_generator.generate_semantic_embedding(slide_info, template_id_str)
                except RuntimeError as e:
                    # If Gemini embedding fails, skip this slide and continue
                    logger.error(f"Failed to generate embedding for slide {template.id}: {e}")
                    continue

                # 3. Update database record
                template.classification = cat_val
                template.tags = tags
                template.semantic_embedding = embedding

                processed += 1

                if progress_callback and (i % 10 == 0 or i == total - 1):
                    progress_callback(processed, total, template.original_pptx_reference or f"Template {template.id}")

                if i % 100 == 0:
                    session.commit()

                # Rate limiting: Wait 5 seconds between slides to stay within Gemini free tier (15 req/min)
                # Each slide uses 2 API calls (classification + embedding), so ~7 slides/min max
                time.sleep(5)

            session.commit()

        elapsed = time.time() - start_time
        return {
            "success": True,
            "total_slides": total,
            "reindexed_count": processed,
            "categories_summary": categories_summary,
            "time_taken_seconds": round(elapsed, 2)
        }

    def _get_indexed_templates_map(self) -> Dict[str, Dict[str, Any]]:
        """Map of filenames and storage paths to indexed template info."""
        mapping: Dict[str, Dict[str, Any]] = {}
        with self.database_manager.get_session() as session:
            # Use a limit to avoid timeout with large datasets
            results = session.query(
                SlideCollection.file_name,
                SlideCollection.storage_path,
                SlideTemplate.id,
                SlideTemplate.classification,
                SlideTemplate.tags,
            ).join(SlideTemplate, SlideTemplate.collection_id == SlideCollection.id).limit(2000).all()

            for fname, spath, tid, classification, tags in results:
                info = {
                    "template_id": tid,
                    "classification": classification,
                    "tags": tags,
                }
                if fname:
                    mapping[fname] = info
                if spath:
                    mapping[spath] = info
        return mapping

    def _find_existing_template(self, filename: str, storage_path: str) -> Optional[SlideTemplate]:
        """Find an existing template by filename or storage path."""
        with self.database_manager.get_session() as session:
            template = (
                session.query(SlideTemplate)
                .join(SlideCollection, SlideTemplate.collection_id == SlideCollection.id)
                .filter(
                    (SlideCollection.file_name == filename)
                    | (SlideCollection.storage_path == storage_path)
                    | (SlideTemplate.original_pptx_reference == storage_path)
                )
                .first()
            )
            return template
