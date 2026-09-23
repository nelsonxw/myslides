"""
Configuration settings for MySlides application.
Handles Firebase credentials, storage paths, and application settings.
"""
import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings

# Load .env file from multiple possible locations at module level
# This must happen before Settings is instantiated
def _load_env_files() -> None:
    """Load .env file from multiple possible locations."""
    current = Path(__file__).resolve()
    candidate_paths = [
        current.parents[2] / ".env",  # myslides root
        current.parents[3] / "project-tracker" / ".env",  # Windsurf/project-tracker directory
        current.parents[3] / "llm_test" / ".env",  # Windsurf/llm_test directory
        Path.cwd() / ".env",
    ]
    for env_path in candidate_paths:
        if env_path.exists():
            load_dotenv(env_path, override=True)
            break

_load_env_files()


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
    
    # LLM Settings - Dell Dev GenAI Gateway
    llm_base_url: str = "https://aia.gateway.dell.com/genai/dev/v1"
    llm_client_id: Optional[str] = Field(default=None, alias="CLIENT_ID")
    llm_client_secret: Optional[str] = Field(default=None, alias="CLIENT_SECRET")
    llm_use_sso: bool = Field(default=False, alias="USE_SSO")
    llm_server_side_token_refresh: bool = Field(default=False, alias="ENABLE_TOKEN_REFRESH_AT_SERVER_SIDE")
    llm_model: str = "gpt-oss-120b"
    # Legacy settings for backward compatibility
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    anthropic_api_key: Optional[str] = Field(default=None, alias="ANTHROPIC_API_KEY")
    
    # Data directories
    data_dir: Path = Path(__file__).parent.parent.parent / "data"
    uploads_dir: Path = data_dir / "uploads"
    templates_dir: Path = data_dir / "templates"
    thumbnails_dir: Path = data_dir / "thumbnails"
    
    # Database
    database_url: str = f"sqlite:///{data_dir / 'myslides.db'}"
    
    # Vector Database
    chroma_persist_directory: Path = data_dir / "chroma_db"
    
    model_config = {
        "env_file": None,  # We load .env manually with load_dotenv
        "env_file_encoding": "utf-8",
        "extra": "ignore",
        "populate_by_name": True,  # Allow field aliases
    }
    
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
