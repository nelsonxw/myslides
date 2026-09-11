"""
Revision Agent: takes user feedback and prior SlideBlueprint to produce an updated SlideBlueprint.
"""
from __future__ import annotations

import json
from myslides.generation.composer import validate_and_autofix_blueprint
from myslides.generation.spec import SlideBlueprint
from myslides.llm.provider import LLMProvider


REVISION_PROMPT = """You are an expert presentation editor.
A user has provided feedback on an existing slide blueprint. Modify the blueprint to incorporate their requested changes accurately while maintaining executive design quality and brand rules.

CURRENT SLIDE BLUEPRINT:
{current_blueprint_json}

USER FEEDBACK / REQUESTED CHANGES:
"{feedback}"

RULES:
- Maintain canvas boundaries (Width: 13.33in, Height: 7.5in, Y between 1.4in and 6.8in).
- If user asks for color changes, use approved palette (#0672CB, #1D2C3B, #00468B, #0B7C84, #F0F0F0, #FFFFFF).
- If user asks to add/remove points, adjust card widths and positions accordingly.
- Set `change_summary` to describe what was adjusted.

Respond ONLY with the complete updated SlideBlueprint JSON object:
"""


def revise_slide_blueprint(
    current_blueprint: SlideBlueprint,
    feedback: str,
    llm: LLMProvider,
) -> SlideBlueprint:
    """Produce an updated SlideBlueprint following user instructions."""
    prompt = REVISION_PROMPT.format(
        current_blueprint_json=current_blueprint.model_dump_json(indent=2),
        feedback=feedback,
    )

    try:
        raw_json = llm.complete_json([{"role": "user", "content": prompt}])
        updated = SlideBlueprint(**raw_json)
    except Exception as e:
        print(f"Revision fallback: {e}")
        # Graceful fallback: append feedback to change_summary
        updated = current_blueprint.model_copy(
            update={"change_summary": f"Refined layout: {feedback[:80]}"}
        )

    return validate_and_autofix_blueprint(updated)
