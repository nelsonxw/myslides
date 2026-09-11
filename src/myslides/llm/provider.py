"""
LLM Provider abstraction.
"""
from __future__ import annotations

import json
import re
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class LLMProvider(Protocol):
    """Protocol for LLM interactions."""

    def complete(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        """Return raw text response."""
        ...

    def complete_json(self, messages: list[dict[str, str]], **kwargs: Any) -> dict[str, Any]:
        """Return parsed JSON object from LLM response."""
        ...


def extract_json(text: str) -> dict[str, Any]:
    """Robustly parse JSON from markdown code fence or plain text."""
    text = text.strip()
    # Try markdown block
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    candidate = match.group(1).strip() if match else text
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        # Try finding outermost braces
        start = candidate.find("{")
        end = candidate.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(candidate[start : end + 1])
        raise
