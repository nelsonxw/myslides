"""
Generation Session service: orchestrates prompt -> v1 -> iterative preview revisions -> final .pptx download.
"""
from __future__ import annotations

import datetime
import json
import uuid
from pathlib import Path
from typing import Any
from pydantic import BaseModel, Field

from myslides.config import settings
from myslides.generation.builder import build_pptx_slide
from myslides.generation.composer import compose_slide_blueprint
from myslides.generation.intent import parse_user_intent
from myslides.generation.retrieval import retrieve_exemplars
from myslides.generation.revision import revise_slide_blueprint
from myslides.generation.spec import SlideBlueprint
from myslides.library.repository import get_standalone_session
from myslides.llm.provider import LLMProvider
from myslides.rendering.base import SlideRenderer


class SlideVersionData(BaseModel):
    version_number: int
    blueprint: SlideBlueprint
    pptx_path: str
    preview_png_path: str | None = None
    feedback_from_previous: str = ""
    change_summary: str = ""
    created_at: str = Field(default_factory=lambda: datetime.datetime.utcnow().isoformat())


class GenerationSessionState(BaseModel):
    session_id: str
    initial_prompt: str
    current_version: int = 1
    versions: list[SlideVersionData] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.datetime.utcnow().isoformat())


class SessionService:
    """Manages active generation sessions on disk."""

    def __init__(self, llm: LLMProvider, renderer: SlideRenderer):
        self.llm = llm
        self.renderer = renderer
        settings.ensure_directories()
        self.sessions_dir = settings.data_dir / "sessions"

    def _get_session_file(self, session_id: str) -> Path:
        return self.sessions_dir / f"{session_id}.json"

    def _save_state(self, state: GenerationSessionState) -> None:
        file_path = self._get_session_file(state.session_id)
        file_path.write_text(state.model_dump_json(indent=2), encoding="utf-8")

    def get_session(self, session_id: str) -> GenerationSessionState | None:
        file_path = self._get_session_file(session_id)
        if not file_path.exists():
            return None
        return GenerationSessionState.model_validate_json(file_path.read_text(encoding="utf-8"))

    def create_session(self, prompt: str) -> GenerationSessionState:
        """Initialize a new slide generation session from a user prompt."""
        session_id = f"sess_{uuid.uuid4().hex[:12]}"
        db_sess = get_standalone_session()
        try:
            # 1. Parse intent
            intent = parse_user_intent(prompt, self.llm)

            # 2. Retrieve exemplars
            exemplars = retrieve_exemplars(intent, db_sess, top_k=3)
        finally:
            db_sess.close()

        # 3. Compose initial Blueprint
        blueprint = compose_slide_blueprint(intent, exemplars, self.llm)

        # 4. Build PPTX
        sess_out_dir = self.sessions_dir / session_id
        sess_out_dir.mkdir(parents=True, exist_ok=True)
        pptx_path = sess_out_dir / "slide_v1.pptx"
        build_pptx_slide(blueprint, pptx_path)

        # 5. Render Preview PNG
        preview_path = sess_out_dir / "slide_v1.png"
        try:
            self.renderer.render_slide(pptx_path, slide_index=0, output_png_path=preview_path)
            preview_str = str(preview_path)
        except Exception as e:
            print(f"Preview render failed: {e}")
            preview_str = None

        v1 = SlideVersionData(
            version_number=1,
            blueprint=blueprint,
            pptx_path=str(pptx_path),
            preview_png_path=preview_str,
            feedback_from_previous="",
            change_summary=blueprint.change_summary,
        )

        state = GenerationSessionState(
            session_id=session_id,
            initial_prompt=prompt,
            current_version=1,
            versions=[v1],
        )
        self._save_state(state)
        return state

    def iterate_session(self, session_id: str, feedback: str) -> GenerationSessionState:
        """Create a new version based on user feedback."""
        state = self.get_session(session_id)
        if not state:
            raise ValueError(f"Session {session_id} not found")

        current_v = state.versions[-1]
        
        # 1. Revise blueprint
        new_bp = revise_slide_blueprint(current_v.blueprint, feedback, self.llm)

        # 2. Build new PPTX
        next_v_num = len(state.versions) + 1
        sess_out_dir = self.sessions_dir / session_id
        pptx_path = sess_out_dir / f"slide_v{next_v_num}.pptx"
        build_pptx_slide(new_bp, pptx_path)

        # 3. Render new Preview PNG
        preview_path = sess_out_dir / f"slide_v{next_v_num}.png"
        try:
            self.renderer.render_slide(pptx_path, slide_index=0, output_png_path=preview_path)
            preview_str = str(preview_path)
        except Exception as e:
            print(f"Preview render failed: {e}")
            preview_str = None

        new_v = SlideVersionData(
            version_number=next_v_num,
            blueprint=new_bp,
            pptx_path=str(pptx_path),
            preview_png_path=preview_str,
            feedback_from_previous=feedback,
            change_summary=new_bp.change_summary,
        )

        state.versions.append(new_v)
        state.current_version = next_v_num
        self._save_state(state)
        return state
