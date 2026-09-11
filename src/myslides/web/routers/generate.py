"""
Generation session router: create session from prompt, iterate with feedback, get preview and download PPTX.
"""
from __future__ import annotations

from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from myslides.llm.factory import get_llm_provider, is_using_mock_provider
from myslides.rendering.powerpoint_com import get_default_renderer
from myslides.sessions.service import GenerationSessionState, SessionService
from myslides.web.schemas import CreateSessionRequest, IterateSessionRequest

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


class LLMStatusResponse(BaseModel):
    using_mock: bool
    message: str


@router.get("/llm-status", response_model=LLMStatusResponse)
def get_llm_status():
    """Check if the app is using MockLLMProvider or a real LLM."""
    using_mock = is_using_mock_provider()
    if using_mock:
        return LLMStatusResponse(
            using_mock=True,
            message="WARNING: Using MockLLMProvider in fallback mode. Set CLIENT_ID and CLIENT_SECRET environment variables to use the real LLM."
        )
    return LLMStatusResponse(
        using_mock=False,
        message="LLM provider configured and ready."
    )


def get_service() -> SessionService:
    llm = get_llm_provider()
    renderer = get_default_renderer()
    return SessionService(llm=llm, renderer=renderer)


@router.post("", response_model=GenerationSessionState)
def create_slide_session(payload: CreateSessionRequest):
    service = get_service()
    state = service.create_session(payload.prompt)
    return state


@router.get("/{session_id}", response_model=GenerationSessionState)
def get_session_details(session_id: str):
    service = get_service()
    state = service.get_session(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found")
    return state


@router.post("/{session_id}/iterate", response_model=GenerationSessionState)
def iterate_slide_session(session_id: str, payload: IterateSessionRequest):
    service = get_service()
    try:
        state = service.iterate_session(session_id, payload.feedback)
        return state
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{session_id}/versions/{version_number}/preview.png")
def get_version_preview(session_id: str, version_number: int):
    service = get_service()
    state = service.get_session(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found")

    target_v = next((v for v in state.versions if v.version_number == version_number), None)
    if not target_v or not target_v.preview_png_path or not Path(target_v.preview_png_path).exists():
        # Generate on demand if missing
        if target_v and target_v.pptx_path and Path(target_v.pptx_path).exists():
            try:
                p_path = service.renderer.render_slide(target_v.pptx_path, 0)
                return FileResponse(p_path, media_type="image/png")
            except Exception:
                pass
        raise HTTPException(status_code=404, detail="Preview image not available")

    return FileResponse(target_v.preview_png_path, media_type="image/png")


@router.get("/{session_id}/versions/{version_number}/download")
def download_slide_pptx(session_id: str, version_number: int):
    service = get_service()
    state = service.get_session(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found")

    target_v = next((v for v in state.versions if v.version_number == version_number), None)
    if not target_v or not Path(target_v.pptx_path).exists():
        raise HTTPException(status_code=404, detail="PPTX file not found")

    safe_title = "".join(c for c in target_v.blueprint.title if c.isalnum() or c in (" ", "_", "-")).strip() or "slide"
    filename = f"{safe_title}_v{version_number}.pptx"

    return FileResponse(
        target_v.pptx_path,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        filename=filename,
    )
