"""
MySlides configuration management.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv


def find_env_file() -> Path | None:
    current = Path(__file__).resolve()
    candidates = [
        current.parents[2] / ".env",  # myslides/.env
        current.parents[3] / ".env",  # workspace/.env
        current.parents[3] / "project-tracker" / ".env",  # fallback to existing project-tracker .env
        Path.cwd() / ".env",
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


env_path = find_env_file()
if env_path:
    load_dotenv(env_path)
else:
    load_dotenv()


@dataclass
class Settings:
    # Project Paths
    base_dir: Path = Path(__file__).resolve().parents[2]
    data_dir: Path = Path(os.getenv("MYSLIDES_DATA_DIR", str(Path(__file__).resolve().parents[2] / "data"))).resolve()
    
    # LLM Settings
    client_id: str = os.getenv("CLIENT_ID", "")
    client_secret: str = os.getenv("CLIENT_SECRET", "")
    use_sso: bool = os.getenv("USE_SSO", "false").lower() == "true"
    enable_server_token_refresh: bool = os.getenv("ENABLE_TOKEN_REFRESH_AT_SERVER_SIDE", "false").lower() == "true"
    llm_model: str = os.getenv("MYSLIDES_LLM_MODEL", "gpt-oss-120b")
    llm_base_url: str = os.getenv("MYSLIDES_LLM_BASE_URL", "https://aia.gateway.dell.com/genai/dev/v1")
    
    # Template & Brand Assets
    base_template_path: Path = Path(os.getenv("MYSLIDES_BASE_TEMPLATE", str(Path(__file__).resolve().parents[3] / "ppt" / "templates" / "Dell_Brand_PPT_Template_May2025.pptx"))).resolve()
    icon_dir: Path = Path(os.getenv("MYSLIDES_ICON_DIR", str(Path(__file__).resolve().parents[3] / "ppt" / "scripts" / "executive_examples" / "icons" / "all"))).resolve()
    icon_catalog_path: Path = Path(os.getenv("MYSLIDES_ICON_CATALOG", str(Path(__file__).resolve().parents[3] / "ppt" / "scripts" / "executive_examples" / "icons" / "FLUENT_ICON_CATALOG.md"))).resolve()
    
    # Renderer
    renderer: str = os.getenv("MYSLIDES_RENDERER", "powerpoint")  # powerpoint | mock | html
    
    # Scrapers
    github_token: str = os.getenv("MYSLIDES_GITHUB_TOKEN", "")

    def ensure_directories(self) -> None:
        """Ensure runtime directories exist."""
        (self.data_dir / "assets").mkdir(parents=True, exist_ok=True)
        (self.data_dir / "previews").mkdir(parents=True, exist_ok=True)
        (self.data_dir / "sessions").mkdir(parents=True, exist_ok=True)
        (self.data_dir / "knowledge").mkdir(parents=True, exist_ok=True)


settings = Settings()
