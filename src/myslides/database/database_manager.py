"""
Database Manager for MySlides.
Handles database operations for collections, templates, and generation requests.
"""
from typing import List, Optional, Dict, Any
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
    
    def list_collections(self, user_id: Optional[str] = None) -> List[SlideCollection]:
        """
        List all collections, optionally filtered by user.
        
        Args:
            user_id: Optional user ID for filtering
        
        Returns:
            List of SlideCollection objects
        """
        with self.get_session() as session:
            query = session.query(SlideCollection)
            if user_id:
                query = query.filter(SlideCollection.user_id == user_id)
            return query.order_by(SlideCollection.upload_date.desc()).all()
    
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
    
    def list_templates(self, collection_id: Optional[int] = None, 
                      classification: Optional[str] = None) -> List[SlideTemplate]:
        """
        List templates, optionally filtered by collection or classification.
        
        Args:
            collection_id: Optional collection ID for filtering
            classification: Optional classification for filtering
        
        Returns:
            List of SlideTemplate objects
        """
        with self.get_session() as session:
            query = session.query(SlideTemplate)
            if collection_id:
                query = query.filter(SlideTemplate.collection_id == collection_id)
            if classification:
                query = query.filter(SlideTemplate.classification == classification)
            return query.order_by(SlideTemplate.created_at.desc()).all()
    
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
    def create_generation_request(self, prompt_text: str, user_id: Optional[str] = None) -> GenerationRequest:
        """
        Create a new generation request.
        
        Args:
            prompt_text: User's prompt text
            user_id: Optional user ID
        
        Returns:
            Created GenerationRequest object
        """
        with self.get_session() as session:
            request = GenerationRequest(
                prompt_text=prompt_text,
                user_id=user_id
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
    def create_deck(self, title: str, slides: List[int], user_id: Optional[str] = None) -> GeneratedDeck:
        """
        Create a new generated deck.
        
        Args:
            title: Deck title
            slides: Ordered list of generation request IDs
            user_id: Optional user ID
        
        Returns:
            Created GeneratedDeck object
        """
        with self.get_session() as session:
            deck = GeneratedDeck(
                title=title,
                slides=slides,
                user_id=user_id
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
