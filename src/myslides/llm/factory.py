"""
Factory for default LLM provider.
"""
from __future__ import annotations

import warnings
from myslides.config import settings
from myslides.llm.dell_gateway import DellGatewayProvider, MockLLMProvider
from myslides.llm.provider import LLMProvider


def get_llm_provider() -> LLMProvider:
    """Return configured LLM provider based on settings/env."""
    if settings.client_id and settings.client_secret:
        return DellGatewayProvider()
    # Fallback to mock if credentials not provided
    warnings.warn(
        "LLM credentials not configured. Using MockLLMProvider in fallback mode. "
        "Set CLIENT_ID and CLIENT_SECRET environment variables to use the real LLM.",
        RuntimeWarning,
        stacklevel=2
    )
    return MockLLMProvider()


def is_using_mock_provider() -> bool:
    """Check if the current configuration will use MockLLMProvider."""
    return not (settings.client_id and settings.client_secret)
