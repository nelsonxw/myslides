"""
Factory for default LLM provider.
"""
from __future__ import annotations

from myslides.config import settings
from myslides.llm.dell_gateway import DellGatewayProvider, MockLLMProvider
from myslides.llm.provider import LLMProvider


def get_llm_provider() -> LLMProvider:
    """Return configured LLM provider based on settings/env."""
    if settings.client_id and settings.client_secret:
        return DellGatewayProvider()
    # Fallback to mock if credentials not provided
    return MockLLMProvider()
