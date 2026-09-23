"""
Database Manager for MySlides.
Handles database operations for collections, templates, and generation requests.
"""
from typing import List, Optional, Dict, Any, Union
from contextlib import contextmanager
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker, Session

from myslides.config import settings
from myslides.database.models import Base, SlideCollection, SlideTemplate, GenerationRequest, GeneratedDeck


class DatabaseManager:
    """Manager for database operations."""
    
    def __init__(self):
        """Initialize database manager."""
        self.engine = create_engine(settings.database_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, expire_on_commit=False, bind=self.engine)
        self._initialize_database()
    
    def _initialize_database(self) -> None:
        """Create database tables if they don't exist."""
        Base.metadata.create_all(bind=self.engine)
    
    @contextmanager
    def get_session(self):
        """Provide a transactional scope around a series of operations."""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    # Collection operations
    def create_collection(self, file_name: str, storage_path: str, 
                          total_slides: int = 0, collection_metadata: Optional[Dict] = None,
                          metadata: Optional[Dict] = None) -> SlideCollection:
        """
        Create a new slide collection.
        
        Args:
            file_name: Name of the uploaded file
            storage_path: Firebase Storage path
            total_slides: Number of slides in the collection
            collection_metadata: Additional metadata
            metadata: Alias for collection_metadata
        
        Returns:
            Created SlideCollection object
        """
        meta = collection_metadata if collection_metadata is not None else (metadata or {})
        with self.get_session() as session:
            collection = SlideCollection(
                file_name=file_name,
                storage_path=storage_path,
                total_slides=total_slides,
                collection_metadata=meta
            )
            session.add(collection)
            session.flush()
            session.refresh(collection)
            return collection
    
    def get_collection(self, collection_id: int) -> Optional[SlideCollection]:
        """
        Get a collection by ID.
        
        Args:
            collection_id: Collection ID
        
        Returns:
            SlideCollection object or None
        """
        with self.get_session() as session:
            return session.query(SlideCollection).filter(SlideCollection.id == collection_id).first()
    
    def list_collections(self, user_id: Optional[str] = None,
                         skip: int = 0,
                         limit: Optional[int] = None) -> List[SlideCollection]:
        """
        List all collections, optionally filtered by user.
        
        Args:
            user_id: Optional user ID for filtering
            skip: Number of records to skip
            limit: Maximum number of records to return
        
        Returns:
            List of SlideCollection objects
        """
        with self.get_session() as session:
            query = session.query(SlideCollection)
            if user_id:
                query = query.filter(SlideCollection.user_id == user_id)
            query = query.order_by(SlideCollection.upload_date.desc())
            if skip > 0:
                query = query.offset(skip)
            if limit is not None:
                query = query.limit(limit)
            return query.all()
    
    def delete_collection(self, collection_id: int) -> bool:
        """
        Delete a collection and all its templates.
        
        Args:
            collection_id: Collection ID
        
        Returns:
            True if successful, False otherwise
        """
        with self.get_session() as session:
            collection = session.query(SlideCollection).filter(SlideCollection.id == collection_id).first()
            if collection:
                session.delete(collection)
                return True
            return False
    
    # Template operations
    def create_template(self, template_data: Dict[str, Any]) -> SlideTemplate:
        """
        Create a new slide template.
        
        Args:
            template_data: Dictionary with template fields
        
        Returns:
            Created SlideTemplate object
        """
        with self.get_session() as session:
            template = SlideTemplate(**template_data)
            session.add(template)
            session.flush()
            session.refresh(template)
            return template
    
    def get_template(self, template_id: int) -> Optional[SlideTemplate]:
        """
        Get a template by ID.
        
        Args:
            template_id: Template ID
        
        Returns:
            SlideTemplate object or None
        """
        with self.get_session() as session:
            return session.query(SlideTemplate).filter(SlideTemplate.id == template_id).first()
    
    def get_template_by_id(self, template_id: str) -> Optional[SlideTemplate]:
        """
        Get a template by ID string or composite key.
        Supports integer ID, "{collection_id}_slide_{slide_index}", template_hash,
        or manifest template_id.

        Args:
            template_id: Template identifier

        Returns:
            SlideTemplate object or None
        """
        with self.get_session() as session:
            # 1. Numeric primary key (e.g. 1 or "1")
            if isinstance(template_id, int) or (isinstance(template_id, str) and template_id.isdigit()):
                tmpl = session.query(SlideTemplate).filter(SlideTemplate.id == int(template_id)).first()
                if tmpl:
                    return tmpl

            # 2. Composite key "{collection_id}_slide_{slide_index}"
            if isinstance(template_id, str) and "_slide_" in template_id:
                parts = template_id.split("_slide_")
                if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                    coll_id = int(parts[0])
                    slide_idx = int(parts[1])
                    tmpl = session.query(SlideTemplate).filter(
                        SlideTemplate.collection_id == coll_id,
                        SlideTemplate.slide_index == slide_idx
                    ).first()
                    if tmpl:
                        return tmpl

            # 3. Check by template_hash
            tmpl = session.query(SlideTemplate).filter(SlideTemplate.template_hash == str(template_id)).first()
            if tmpl:
                return tmpl

            # 4. Fallback: search in element_manifest
            templates = session.query(SlideTemplate).all()
            for template in templates:
                manifest = template.element_manifest or {}
                if isinstance(manifest, dict) and manifest.get("template_id") == str(template_id):
                    return template
            return None
    
    def list_templates(self, collection_id: Optional[int] = None, 
                      classification: Optional[str] = None,
                      skip: int = 0,
                      limit: Optional[int] = None) -> List[SlideTemplate]:
        """
        List templates, optionally filtered by collection or classification.
        
        Args:
            collection_id: Optional collection ID for filtering
            classification: Optional classification for filtering
            skip: Number of records to skip
            limit: Maximum number of records to return
        
        Returns:
            List of SlideTemplate objects
        """
        with self.get_session() as session:
            query = session.query(SlideTemplate)
            if collection_id:
                query = query.filter(SlideTemplate.collection_id == collection_id)
            if classification:
                query = query.filter(SlideTemplate.classification == classification)
            query = query.order_by(SlideTemplate.created_at.desc())
            if skip > 0:
                query = query.offset(skip)
            if limit is not None:
                query = query.limit(limit)
            return query.all()

    def list_templates_by_classification(self, classification: str,
                                         skip: int = 0,
                                         limit: Optional[int] = None) -> List[SlideTemplate]:
        """
        List templates filtered by classification.

        Args:
            classification: Slide classification string
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of SlideTemplate objects
        """
        return self.list_templates(classification=classification, skip=skip, limit=limit)
    
    def update_template(self, template_id: int, update_data: Dict[str, Any]) -> Optional[SlideTemplate]:
        """
        Update a template.
        
        Args:
            template_id: Template ID
            update_data: Dictionary with fields to update
        
        Returns:
            Updated SlideTemplate object or None
        """
        with self.get_session() as session:
            template = session.query(SlideTemplate).filter(SlideTemplate.id == template_id).first()
            if template:
                for key, value in update_data.items():
                    if hasattr(template, key):
                        setattr(template, key, value)
                session.flush()
                session.refresh(template)
                return template
            return None
    
    def delete_template(self, template_id: int) -> bool:
        """
        Delete a template.
        
        Args:
            template_id: Template ID
        
        Returns:
            True if successful, False otherwise
        """
        with self.get_session() as session:
            template = session.query(SlideTemplate).filter(SlideTemplate.id == template_id).first()
            if template:
                session.delete(template)
                return True
            return False
    
    def search_templates_by_tags(self, tags: List[str]) -> List[SlideTemplate]:
        """
        Search templates by tags.
        
        Args:
            tags: List of tags to search for
        
        Returns:
            List of matching SlideTemplate objects
        """
        with self.get_session() as session:
            # For MVP, simple JSON contains search
            # In production, would use proper JSON query or join table
            templates = session.query(SlideTemplate).all()
            results = []
            for template in templates:
                if template.tags:
                    if any(tag in template.tags for tag in tags):
                        results.append(template)
            return results
    
    def get_templates_by_hash(self, template_hash: str) -> List[SlideTemplate]:
        """
        Get templates with a specific structural hash.
        
        Args:
            template_hash: Template hash string
        
        Returns:
            List of matching SlideTemplate objects
        """
        with self.get_session() as session:
            return session.query(SlideTemplate).filter(
                SlideTemplate.template_hash == template_hash
            ).all()
    
    # Generation request operations
    def create_generation_request(self,
                                  prompt_text: Union[str, Dict[str, Any]],
                                  user_id: Optional[str] = None,
                                  **kwargs) -> GenerationRequest:
        """
        Create a new generation request. Supports dictionary data or argument values.
        
        Args:
            prompt_text: User's prompt text or dictionary containing request attributes
            user_id: Optional user ID
            **kwargs: Additional request fields (parsed_intent, status, etc.)
        
        Returns:
            Created GenerationRequest object
        """
        with self.get_session() as session:
            if isinstance(prompt_text, dict):
                data = dict(prompt_text)
                data.update(kwargs)
                user = str(data.get("user_id")) if data.get("user_id") is not None else user_id
                request = GenerationRequest(
                    user_id=user,
                    prompt_text=data.get("prompt_text", ""),
                    parsed_intent=data.get("parsed_intent"),
                    matched_template_ids=data.get("matched_template_ids"),
                    selected_template_id=data.get("selected_template_id"),
                    generated_file_path=data.get("generated_file_path"),
                    status=data.get("status", "pending"),
                    error_message=data.get("error_message"),
                    processing_time_seconds=data.get("processing_time_seconds")
                )
            else:
                user = str(user_id) if user_id is not None else None
                request = GenerationRequest(
                    prompt_text=prompt_text,
                    user_id=user,
                    **kwargs
                )
            session.add(request)
            session.flush()
            session.refresh(request)
            return request
    
    def update_generation_request(self, request_id: int, update_data: Dict[str, Any]) -> Optional[GenerationRequest]:
        """
        Update a generation request.
        
        Args:
            request_id: Request ID
            update_data: Dictionary with fields to update
        
        Returns:
            Updated GenerationRequest object or None
        """
        with self.get_session() as session:
            request = session.query(GenerationRequest).filter(GenerationRequest.id == request_id).first()
            if request:
                for key, value in update_data.items():
                    if hasattr(request, key):
                        setattr(request, key, value)
                session.flush()
                session.refresh(request)
                return request
            return None
    
    def get_generation_request(self, request_id: int) -> Optional[GenerationRequest]:
        """
        Get a generation request by ID.
        
        Args:
            request_id: Request ID
        
        Returns:
            GenerationRequest object or None
        """
        with self.get_session() as session:
            return session.query(GenerationRequest).filter(GenerationRequest.id == request_id).first()
    
    def list_generation_requests(self, user_id: Optional[str] = None, 
                                status: Optional[str] = None) -> List[GenerationRequest]:
        """
        List generation requests, optionally filtered by user or status.
        
        Args:
            user_id: Optional user ID for filtering
            status: Optional status for filtering
        
        Returns:
            List of GenerationRequest objects
        """
        with self.get_session() as session:
            query = session.query(GenerationRequest)
            if user_id:
                query = query.filter(GenerationRequest.user_id == user_id)
            if status:
                query = query.filter(GenerationRequest.status == status)
            return query.order_by(GenerationRequest.timestamp.desc()).all()
    
    # Generated deck operations
    def create_deck(self,
                    title: Union[str, Dict[str, Any]],
                    slides: Optional[List[int]] = None,
                    user_id: Optional[str] = None,
                    **kwargs) -> GeneratedDeck:
        """
        Create a new generated deck. Supports dictionary or parameter inputs.
        
        Args:
            title: Deck title or dictionary containing deck attributes
            slides: Ordered list of generation request IDs
            user_id: Optional user ID
            **kwargs: Additional fields
        
        Returns:
            Created GeneratedDeck object
        """
        with self.get_session() as session:
            if isinstance(title, dict):
                data = dict(title)
                data.update(kwargs)
                user = str(data.get("user_id")) if data.get("user_id") is not None else user_id
                deck = GeneratedDeck(
                    title=data.get("title", "Untitled Deck"),
                    slides=data.get("slides", []),
                    user_id=user,
                    export_file_path=data.get("export_file_path")
                )
            else:
                user = str(user_id) if user_id is not None else None
                deck = GeneratedDeck(
                    title=title,
                    slides=slides or [],
                    user_id=user,
                    **kwargs
                )
            session.add(deck)
            session.flush()
            session.refresh(deck)
            return deck
    
    def get_deck(self, deck_id: int) -> Optional[GeneratedDeck]:
        """
        Get a deck by ID.

        Args:
            deck_id: Deck ID

        Returns:
            GeneratedDeck object or None
        """
        with self.get_session() as session:
            return session.query(GeneratedDeck).filter(GeneratedDeck.id == deck_id).first()

    def update_deck(self, deck_id: int, update_data: Dict[str, Any]) -> Optional[GeneratedDeck]:
        """
        Update a deck.

        Args:
            deck_id: Deck ID
            update_data: Dictionary with fields to update

        Returns:
            Updated GeneratedDeck object or None
        """
        with self.get_session() as session:
            deck = session.query(GeneratedDeck).filter(GeneratedDeck.id == deck_id).first()
            if deck:
                for key, value in update_data.items():
                    if hasattr(deck, key):
                        setattr(deck, key, value)
                session.flush()
                session.refresh(deck)
                return deck
            return None
    
    def list_decks(self, user_id: Optional[str] = None) -> List[GeneratedDeck]:
        """
        List all decks, optionally filtered by user.
        
        Args:
            user_id: Optional user ID for filtering
        
        Returns:
            List of GeneratedDeck objects
        """
        with self.get_session() as session:
            query = session.query(GeneratedDeck)
            if user_id:
                query = query.filter(GeneratedDeck.user_id == user_id)
            return query.order_by(GeneratedDeck.created_at.desc()).all()
    
    # Statistics
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get database statistics.
        
        Returns:
            Dictionary with statistics
        """
        with self.get_session() as session:
            total_collections = session.query(func.count(SlideCollection.id)).scalar()
            total_templates = session.query(func.count(SlideTemplate.id)).scalar()
            total_requests = session.query(func.count(GenerationRequest.id)).scalar()
            total_decks = session.query(func.count(GeneratedDeck.id)).scalar()
            
            # Get classification breakdown
            classification_counts = session.query(
                SlideTemplate.classification,
                func.count(SlideTemplate.id)
            ).group_by(SlideTemplate.classification).all()
            
            return {
                "total_collections": total_collections,
                "total_templates": total_templates,
                "total_requests": total_requests,
                "total_decks": total_decks,
                "classification_breakdown": dict(classification_counts)
            }
