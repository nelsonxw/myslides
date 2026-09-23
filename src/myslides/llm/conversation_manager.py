"""
Conversation Manager for MySlides.

Manages conversational context for iterative slide refinement.
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timezone
from myslides.llm.llm_client import LLMClient, LLMProvider
from myslides.llm.prompt_parser import PromptParser
from myslides.generation.generation_models import GenerationIntent


def _utc_now() -> datetime:
    """Helper to return current UTC datetime."""
    return datetime.now(timezone.utc)


@dataclass
class ConversationTurn:
    """A single turn in a conversation."""
    user_message: str
    assistant_response: str
    intent: Optional[GenerationIntent] = None
    timestamp: datetime = field(default_factory=_utc_now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert turn to dictionary."""
        return {
            "user_message": self.user_message,
            "assistant_response": self.assistant_response,
            "intent": {
                "slide_type": self.intent.slide_type.value if self.intent else None,
                "content": self.intent.content if self.intent else None
            } if self.intent else None,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class ConversationContext:
    """Context for an ongoing conversation about slide generation."""
    conversation_id: str
    turns: List[ConversationTurn] = field(default_factory=list)
    current_intent: Optional[GenerationIntent] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=_utc_now)
    updated_at: datetime = field(default_factory=_utc_now)
    
    def add_turn(self, user_message: str, assistant_response: str, intent: Optional[GenerationIntent] = None) -> None:
        """Add a new turn to the conversation."""
        turn = ConversationTurn(
            user_message=user_message,
            assistant_response=assistant_response,
            intent=intent
        )
        self.turns.append(turn)
        self.updated_at = _utc_now()
        if intent:
            self.current_intent = intent
    
    def get_recent_turns(self, count: int = 5) -> List[ConversationTurn]:
        """Get the most recent conversation turns."""
        return self.turns[-count:] if self.turns else []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary."""
        return {
            "conversation_id": self.conversation_id,
            "turns": [turn.to_dict() for turn in self.turns],
            "current_intent": {
                "slide_type": self.current_intent.slide_type.value if self.current_intent else None,
                "content": self.current_intent.content if self.current_intent else None
            } if self.current_intent else None,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }


class ConversationManager:
    """Manages conversational context for slide generation refinement."""
    
    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        prompt_parser: Optional[PromptParser] = None
    ):
        """
        Initialize conversation manager.
        
        Args:
            llm_client: Optional LLM client (defaults to OpenAI if not provided)
            prompt_parser: Optional PromptParser instance for dependency injection
        """
        self.llm_client = llm_client or LLMClient(provider=LLMProvider.OPENAI)
        self.prompt_parser = prompt_parser or PromptParser(llm_client=self.llm_client)
        self.active_conversations: Dict[str, ConversationContext] = {}
        self.system_prompt = self._build_system_prompt()
    
    def _build_system_prompt(self) -> str:
        """Build the system prompt for conversational refinement."""
        return """You are an expert at refining slide generation requests through conversation.

Your task is to analyze a user's follow-up request in the context of the previous conversation and extract the refined structured intent.

Common refinement patterns:
- Change slide type: "Make it a timeline instead" -> Update slide_type
- Modify content: "Change the title to X" or "Add a bullet point about Y" -> Update content
- Adjust styling: "Use the blue color scheme" -> Update color_preference
- Add elements: "Add a callout box highlighting step 3" -> Update element_preferences
- Remove elements: "Remove the subtitle" -> Clear subtitle from content

Always preserve context from previous turns unless explicitly asked to change it.

Respond with valid JSON only, no additional text."""
    
    def create_conversation(self, conversation_id: Optional[str] = None) -> ConversationContext:
        """
        Create a new conversation context.
        
        Args:
            conversation_id: Optional custom ID (auto-generated if not provided)
        
        Returns:
            New ConversationContext object
        """
        if conversation_id is None:
            conversation_id = f"conv_{_utc_now().timestamp()}"
        
        context = ConversationContext(conversation_id=conversation_id)
        self.active_conversations[conversation_id] = context
        return context
    
    def get_conversation(self, conversation_id: str) -> Optional[ConversationContext]:
        """
        Get an existing conversation context.
        
        Args:
            conversation_id: The conversation ID
        
        Returns:
            ConversationContext if found, None otherwise
        """
        return self.active_conversations.get(conversation_id)
    
    def process_message(
        self,
        conversation_id: str,
        user_message: str,
        initial_prompt: bool = False
    ) -> Tuple[str, GenerationIntent]:
        """
        Process a user message in a conversation.
        
        Args:
            conversation_id: The conversation ID
            user_message: The user's message
            initial_prompt: Whether this is the initial prompt (no context)
        
        Returns:
            Tuple of (assistant_response, refined_intent)
        """
        context = self.get_conversation(conversation_id)
        if not context:
            context = self.create_conversation(conversation_id)
        
        if initial_prompt or not context.turns:
            # Initial prompt - use standard parsing
            intent = self.prompt_parser.parse_prompt(user_message)
            response = f"I'll create a {intent.slide_type.value} slide with the content you specified."
        else:
            # Follow-up - use context-aware parsing
            intent = self.prompt_parser.parse_with_context(
                prompt=user_message,
                previous_intent=context.current_intent,
                conversation_history=[turn.to_dict() for turn in context.get_recent_turns(3)]
            )
            response = self._generate_response_message(user_message, intent, context)
        
        # Add turn to conversation
        context.add_turn(user_message, response, intent)
        
        return response, intent
    
    def _generate_response_message(
        self,
        user_message: str,
        intent: GenerationIntent,
        context: ConversationContext
    ) -> str:
        """Generate a natural language response to the user."""
        if context.current_intent and context.current_intent.slide_type != intent.slide_type:
            return f"I've changed the slide type to {intent.slide_type.value}."
        elif context.current_intent and context.current_intent.content.get("title") != intent.content.get("title"):
            return f"I've updated the title to '{intent.content.get('title')}'."
        else:
            return f"I've refined the {intent.slide_type.value} slide based on your request."
    
    def refine_intent(
        self,
        conversation_id: str,
        refinement_prompt: str
    ) -> GenerationIntent:
        """
        Refine the current intent based on a follow-up prompt.
        
        Args:
            conversation_id: The conversation ID
            refinement_prompt: The user's refinement request
        
        Returns:
            Refined GenerationIntent
        """
        context = self.get_conversation(conversation_id)
        if not context:
            raise ValueError(f"Conversation {conversation_id} not found")
        
        if not context.current_intent:
            raise ValueError("No current intent to refine. Start with an initial prompt.")
        
        refined_intent = self.prompt_parser.parse_with_context(
            prompt=refinement_prompt,
            previous_intent=context.current_intent,
            conversation_history=[turn.to_dict() for turn in context.get_recent_turns(3)]
        )
        
        # Update context
        response = self._generate_response_message(refinement_prompt, refined_intent, context)
        context.add_turn(refinement_prompt, response, refined_intent)
        
        return refined_intent
    
    def delete_conversation(self, conversation_id: str) -> bool:
        """
        Delete a conversation context.
        
        Args:
            conversation_id: The conversation ID
        
        Returns:
            True if deleted, False if not found
        """
        if conversation_id in self.active_conversations:
            del self.active_conversations[conversation_id]
            return True
        return False
    
    def list_conversations(self) -> List[str]:
        """
        List all active conversation IDs.
        
        Returns:
            List of conversation IDs
        """
        return list(self.active_conversations.keys())

