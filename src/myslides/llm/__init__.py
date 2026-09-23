"""
LLM Integration Module for MySlides.

Provides prompt parsing, intent extraction, and conversational refinement
using OpenAI or Anthropic language models.
"""

from .llm_client import LLMClient, LLMProvider
from .prompt_parser import PromptParser
from .deck_planner import DeckPlanner, DeckPlan
from .conversation_manager import ConversationManager, ConversationContext

__all__ = [
    "LLMClient",
    "LLMProvider",
    "PromptParser",
    "DeckPlanner",
    "DeckPlan",
    "ConversationManager",
    "ConversationContext",
]
