"""
Firebase Storage Service for MySlides.
Handles authentication, uploading PPTX files and thumbnails,
listing stored files, and managing storage operations.
"""
import datetime
import json
import urllib3
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Optional

import firebase_admin
from firebase_admin import credentials, storage
from google.cloud.storage.blob import Blob

from myslides.config import settings


@dataclass
class StoredPPTXFile:
    """Data class representing a stored PPTX file in Firebase Storage."""
    id: str
    filename: str
    storage_path: str
    download_url: str
    public_url: str
    file_size: int
    uploaded_at: str
    metadata: dict[str, Any]


@dataclass
class StoredThumbnail:
    """Data class representing a stored thumbnail in Firebase Storage."""
    id: str
    filename: str
    storage_path: str
    download_url: str
    public_url: str
    file_size: int
    uploaded_at: str
    associated_pptx_id: str


class FirebaseStorageService:
    """Service for managing Firebase Storage operations."""
    
    _instance: Optional["FirebaseStorageService"] = None
    
    def __init__(self):
        self.bucket_name = settings.storage_bucket.replace("gs://", "").strip("/")
        self.app: Optional[firebase_admin.App] = None
        self.bucket: Optional[Any] = None
        self.is_connected = False
        self.connection_error: Optional[str] = None
        self._init_firebase()
    
    @classmethod
    def get_instance(cls) -> "FirebaseStorageService":
        """Get singleton instance of FirebaseStorageService."""
        if cls._instance is None:
            cls._instance = FirebaseStorageService()
        return cls._instance
    
    def _init_firebase(self) -> None:
        """Initialize Firebase Admin SDK with service account credentials."""
        try:
            cred_path = settings.resolve_credentials_path()
            if cred_path:
                cred = credentials.Certificate(str(cred_path))
            else:
                # Try application default credentials
                try:
                    cred = credentials.ApplicationDefault()
                except Exception:
                    cred = None
            
            if not firebase_admin._apps:
                if cred:
                    self.app = firebase_admin.initialize_app(
                        cred,
                        {"storageBucket": self.bucket_name}
                    )
                else:
                    self.app = firebase_admin.initialize_app(
                        options={"storageBucket": self.bucket_name}
                    )
            else:
                self.app = firebase_admin.get_app()
            
            self.bucket = storage.bucket(self.bucket_name, app=self.app)
            self._configure_client_ssl()
            self.is_connected = True
            self.connection_error = None
            print(f"Firebase Storage initialized successfully: {self.bucket_name}")
        except Exception as e:
            self.is_connected = False
            self.connection_error = str(e)
            print(f"Warning: Firebase Storage init failed ({self.bucket_name}): {e}")
    
    def _configure_client_ssl(self) -> None:
        """Configure SSL verification on the Google Cloud Storage client."""
        if not self.bucket or not hasattr(self.bucket, 'client'):
            return
        
        client = self.bucket.client
        verify_value = settings.firebase_ca_bundle if settings.firebase_ca_bundle else settings.firebase_verify_ssl
        
        if not settings.firebase_verify_ssl:
            urllib3.disable_warnings()
        
        if hasattr(client, '_http') and client._http:
            client._http.verify = verify_value
        
        if hasattr(client, '_connection') and hasattr(self.bucket.client._connection, 'http') and self.bucket.client._connection.http:
            self.bucket.client._connection.http.verify = verify_value
    
    def get_status(self) -> dict[str, Any]:
        """Get current connection status and configuration."""
        return {
            "bucket_name": self.bucket_name,
            "is_connected": self.is_connected,
            "credentials_found": bool(settings.resolve_credentials_path()),
            "credentials_path": str(settings.resolve_credentials_path() or settings.credentials_path),
            "firebase_verify_ssl": settings.firebase_verify_ssl,
            "firebase_ca_bundle": settings.firebase_ca_bundle,
            "error": self.connection_error,
        }
    
    def upload_pptx(
        self,
        local_path: Path | str,
        collection_name: str,
        metadata: dict[str, Any]
    ) -> StoredPPTXFile:
        """
        Upload a PPTX file to Firebase Storage.
        
        Args:
            local_path: Path to local PPTX file
            collection_name: Name of the slide collection
            metadata: Additional metadata to store with the file
        
        Returns:
            StoredPPTXFile with storage information
        """
        local_file = Path(local_path).resolve()
        if not local_file.exists():
            raise FileNotFoundError(f"File not found: {local_file}")
        
        filename = local_file.name
        storage_path = f"myslides/collections/{collection_name}/pptx/{filename}"
        timestamp_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        
        # Add timestamp to metadata
        upload_metadata = {
            **metadata,
            "uploaded_at": timestamp_iso,
            "collection_name": collection_name,
        }
        
        if self.is_connected and self.bucket:
            blob = self.bucket.blob(storage_path)
            blob.metadata = upload_metadata
            blob.upload_from_filename(
                str(local_file),
                content_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                timeout=60
            )
            try:
                blob.make_public()
            except Exception:
                pass
            
            download_url = self._get_blob_url(blob, storage_path)
            public_url = self._get_public_blob_url(blob, storage_path)
        else:
            # Local fallback
            download_url = f"/api/storage/download/local/{filename}"
            public_url = ""
        
        return StoredPPTXFile(
            id=storage_path,
            filename=filename,
            storage_path=storage_path,
            download_url=download_url,
            public_url=public_url,
            file_size=local_file.stat().st_size,
            uploaded_at=timestamp_iso,
            metadata=upload_metadata
        )
    
    def upload_thumbnail(
        self,
        local_path: Path | str,
        collection_name: str,
        slide_index: int,
        associated_pptx_id: str,
        metadata: dict[str, Any]
    ) -> StoredThumbnail:
        """
        Upload a thumbnail image to Firebase Storage.
        
        Args:
            local_path: Path to local thumbnail file
            collection_name: Name of the slide collection
            slide_index: Index of the slide in the presentation
            associated_pptx_id: ID of the associated PPTX file
            metadata: Additional metadata to store with the file
        
        Returns:
            StoredThumbnail with storage information
        """
        local_file = Path(local_path).resolve()
        if not local_file.exists():
            raise FileNotFoundError(f"File not found: {local_file}")
        
        filename = local_file.name
        storage_path = f"myslides/collections/{collection_name}/thumbnails/{slide_index}_{filename}"
        timestamp_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        
        # Add timestamp to metadata
        upload_metadata = {
            **metadata,
            "uploaded_at": timestamp_iso,
            "collection_name": collection_name,
            "slide_index": str(slide_index),
            "associated_pptx_id": associated_pptx_id,
        }
        
        if self.is_connected and self.bucket:
            blob = self.bucket.blob(storage_path)
            blob.metadata = upload_metadata
            blob.upload_from_filename(
                str(local_file),
                content_type="image/png",
                timeout=60
            )
            try:
                blob.make_public()
            except Exception:
                pass
            
            download_url = self._get_blob_url(blob, storage_path)
            public_url = self._get_public_blob_url(blob, storage_path)
        else:
            # Local fallback
            download_url = f"/api/storage/download/local/{filename}"
            public_url = ""
        
        return StoredThumbnail(
            id=storage_path,
            filename=filename,
            storage_path=storage_path,
            download_url=download_url,
            public_url=public_url,
            file_size=local_file.stat().st_size,
            uploaded_at=timestamp_iso,
            associated_pptx_id=associated_pptx_id
        )
    
    def download_file(self, storage_path: str, local_destination: Path | str) -> Path:
        """
        Download a file from Firebase Storage to local destination.
        
        Args:
            storage_path: Path in Firebase Storage
            local_destination: Local path to save the file
        
        Returns:
            Path to downloaded file
        """
        if not self.is_connected or not self.bucket:
            raise RuntimeError("Firebase Storage not connected")
        
        blob = self.bucket.blob(storage_path)
        if not blob.exists():
            raise FileNotFoundError(f"File not found in storage: {storage_path}")
        
        local_path = Path(local_destination)
        local_path.parent.mkdir(parents=True, exist_ok=True)
        
        blob.download_to_filename(str(local_path))
        return local_path
    
    def list_collection_files(self, collection_name: str) -> list[dict[str, Any]]:
        """
        List all files in a specific collection.
        
        Args:
            collection_name: Name of the collection
        
        Returns:
            List of file information dictionaries
        """
        if not self.is_connected or not self.bucket:
            return []
        
        files = []
        prefix = f"myslides/collections/{collection_name}/"
        
        try:
            blobs = self.bucket.list_blobs(prefix=prefix)
            for blob in blobs:
                if blob.name.endswith('/') or blob.name.endswith('.placeholder'):
                    continue
                
                file_info = {
                    "name": blob.name.split('/')[-1],
                    "storage_path": blob.name,
                    "size": blob.size,
                    "updated": blob.updated.isoformat() if blob.updated else None,
                    "content_type": blob.content_type,
                    "metadata": blob.metadata or {}
                }
                files.append(file_info)
        except Exception as e:
            print(f"Error listing collection files: {e}")
        
        return files
    
    def delete_file(self, storage_path: str) -> bool:
        """
        Delete a file from Firebase Storage.
        
        Args:
            storage_path: Path in Firebase Storage
        
        Returns:
            True if successful, False otherwise
        """
        if not self.is_connected or not self.bucket:
            return False
        
        try:
            blob = self.bucket.blob(storage_path)
            if blob.exists():
                blob.delete()
                return True
            return False
        except Exception as e:
            print(f"Error deleting file {storage_path}: {e}")
            return False
    
    def delete_collection(self, collection_name: str) -> dict[str, Any]:
        """
        Delete all files in a collection.
        
        Args:
            collection_name: Name of the collection to delete
        
        Returns:
            Dictionary with deletion results
        """
        if not self.is_connected or not self.bucket:
            return {"success": False, "error": "Not connected to Firebase Storage"}
        
        deleted_count = 0
        errors = []
        
        prefix = f"myslides/collections/{collection_name}/"
        
        try:
            blobs = list(self.bucket.list_blobs(prefix=prefix))
            for blob in blobs:
                try:
                    blob.delete()
                    deleted_count += 1
                except Exception as e:
                    errors.append(f"Failed to delete {blob.name}: {e}")
        except Exception as e:
            errors.append(f"Error listing blobs: {e}")
        
        return {
            "success": len(errors) == 0,
            "deleted_count": deleted_count,
            "errors": errors
        }
    
    def _get_blob_url(self, blob: Optional[Blob], path: str) -> str:
        """Generate authenticated backend URL for a blob."""
        return f"/api/storage/download/{path}"
    
    def _get_public_blob_url(self, blob: Optional[Blob], path: str) -> str:
        """Generate public HTTPS URL for a blob."""
        return f"https://storage.googleapis.com/{self.bucket_name}/{path}"
