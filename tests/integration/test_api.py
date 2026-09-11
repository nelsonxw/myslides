"""
Integration tests for FastAPI endpoints and generation sessions.
"""
from pathlib import Path
from fastapi.testclient import TestClient
import pytest

from myslides.library.models import Source
from myslides.library.repository import get_session, init_db
from myslides.web.app import create_app


@pytest.fixture
def client(tmp_path, monkeypatch):
    # Route data directory to temporary folder
    monkeypatch.setenv("MYSLIDES_DATA_DIR", str(tmp_path))
    from myslides.config import settings
    settings.data_dir = tmp_path
    settings.ensure_directories()
    
    app = create_app()
    return TestClient(app)


def test_api_sources_crud(client):
    # List initial sources
    res = client.get("/api/sources")
    assert res.status_code == 200
    
    # Add new source
    res_add = client.post(
        "/api/sources",
        json={
            "name": "Integration Test Source",
            "kind": "generic_url",
            "url_or_path": "https://example.com/templates.html",
            "license": "CC BY 4.0",
        },
    )
    assert res_add.status_code == 200
    data = res_add.json()
    source_id = data["id"]
    assert data["name"] == "Integration Test Source"

    # Delete source
    res_del = client.delete(f"/api/sources/{source_id}")
    assert res_del.status_code == 200


def test_api_library_and_rules(client):
    # Rules endpoint
    res_rules = client.get("/api/library/rules")
    assert res_rules.status_code == 200
    rules = res_rules.json()
    assert "visuals" in rules
    assert "layout" in rules
    assert "formatting" in rules

    # Slides list
    res_slides = client.get("/api/library/slides")
    assert res_slides.status_code == 200
    data = res_slides.json()
    assert "slides" in data
    assert isinstance(data["slides"], list)


def test_api_session_lifecycle(client):
    # Create session
    prompt = "Executive KPI scorecard for executive leadership"
    res_create = client.post("/api/sessions", json={"prompt": prompt})
    assert res_create.status_code == 200
    sess_data = res_create.json()
    sess_id = sess_data["session_id"]
    assert len(sess_data["versions"]) == 1
    assert sess_data["current_version"] == 1

    # Iterate session with feedback
    feedback = "Make the cards darker and add a 4th milestone"
    res_iter = client.post(f"/api/sessions/{sess_id}/iterate", json={"feedback": feedback})
    assert res_iter.status_code == 200
    iter_data = res_iter.json()
    assert len(iter_data["versions"]) == 2
    assert iter_data["current_version"] == 2

    # Download v2 PPTX
    res_dl = client.get(f"/api/sessions/{sess_id}/versions/2/download")
    assert res_dl.status_code == 200
    assert len(res_dl.content) > 1000
