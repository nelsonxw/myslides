"""
Library Exemplar Retrieval: finds the best matching high-scoring template slides for a given intent.
"""
from __future__ import annotations

from typing import Any
from sqlalchemy.orm import Session
from myslides.generation.spec import SlideIntentSpec
from myslides.library.models import SlideRecord, SlideScoreRecord


def retrieve_exemplars(
    intent: SlideIntentSpec,
    db_session: Session,
    top_k: int = 3,
) -> list[dict[str, Any]]:
    """Retrieve top-scoring template slides that match the desired archetype/content."""
    query = (
        db_session.query(SlideRecord)
        .join(SlideRecord.score)
        .filter(SlideRecord.score.has())
    )

    # First attempt: match exact archetype
    archetype_matches = (
        query.filter(SlideRecord.archetype == intent.archetype)
        .order_by(SlideScoreRecord.total_score.desc())
        .limit(top_k)
        .all()
    )

    if len(archetype_matches) >= top_k:
        results = archetype_matches
    else:
        # Fallback to general highest-scoring slides
        fallback = (
            query.order_by(SlideScoreRecord.total_score.desc())
            .limit(top_k)
            .all()
        )
        results = list({s.id: s for s in (archetype_matches + fallback)}.values())[:top_k]

    exemplars = []
    for s in results:
        features = s.features.features_json if s.features else {}
        exemplars.append({
            "slide_id": s.id,
            "title": s.title_text,
            "archetype": s.archetype,
            "score": s.score.total_score if s.score else 80.0,
            "shape_count": s.features.shape_count if s.features else 4,
            "tags": s.tags,
            "layout_summary": f"Layout with {len(features.get('shapes', []))} shapes, whitespace: {features.get('whitespace_ratio', 0.4)}",
        })

    return exemplars
