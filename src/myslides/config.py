"""
Configuration settings for MySlides application.
Handles Firebase credentials, storage paths, and application settings.
"""
import os
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Application
    app_name: str = "MySlides"
    app_version: str = "0.1.0"
    debug: bool = True
    
    # Firebase Storage
    storage_bucket: str = "slide-preview.firebasestorage.app"
    credentials_path: str = ""
    firebase_verify_ssl: bool = False
    firebase_ca_bundle: Optional[str] = None
    
    # LLM Settings
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    
    # Data directories
    data_dir: Path = Path(__file__).parent.parent.parent / "data"
    uploads_dir: Path = data_dir / "uploads"
    templates_dir: Path = data_dir / "templates"
    thumbnails_dir: Path = data_dir / "thumbnails"
    
    # Database
    database_url: str = f"sqlite:///{data_dir / 'myslides.db'}"
    
    # Vector Database
    chroma_persist_directory: Path = data_dir / "chroma_db"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"
    
    def resolve_credentials_path(self) -> Optional[Path]:
        """Resolve Firebase service account credentials path."""
        if self.credentials_path:
            cred_path = Path(self.credentials_path)
            if cred_path.exists():
                return cred_path
        
        # Try default locations
        default_paths = [
            Path(__file__).parent.parent.parent / "serviceAccountKey.json",
            Path(__file__).parent.parent.parent.parent / "slide_scrapper" / "backend" / "serviceAccountKey.json",
            Path.home() / ".config" / "myslides" / "serviceAccountKey.json",
        ]
        
        for path in default_paths:
            if path.exists():
                return path
        
        return None
    
    def ensure_data_directories(self) -> None:
        """Create necessary data directories if they don't exist."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        self.thumbnails_dir.mkdir(parents=True, exist_ok=True)
        self.chroma_persist_directory.mkdir(parents=True, exist_ok=True)


# Global settings instance
settings = Settings()
settings.ensure_data_directories()
