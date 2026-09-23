"""
Unit tests for Conversation Manager.
"""
import pytest
from unittest.mock import Mock, patch
from datetime import datetime
from myslides.llm.conversation_manager import (
    ConversationManager,
    ConversationContext,
    ConversationTurn
)
from myslides.llm.llm_client import LLMClient
from myslides.generation.generation_models import GenerationIntent, SlideType


class TestConversationTurn:
    """Test cases for ConversationTurn dataclass."""
    
    def test_conversation_turn_creation(self):
        """Test creating a conversation turn."""
        turn = ConversationTurn(
            user_message="Test message",
            assistant_response="Test response"
        )
        assert turn.user_message == "Test message"
        assert turn.assistant_response == "Test response"
        assert turn.intent is None
        assert isinstance(turn.timestamp, datetime)
    
    def test_conversation_turn_to_dict(self):
        """Test converting turn to dictionary."""
        intent = GenerationIntent(
            slide_type=SlideType.TITLE_SLIDE,
            content={"title": "Test"}
        )
        turn = ConversationTurn(
            user_message="Test",
            assistant_response="Response",
            intent=intent
        )
        
        turn_dict = turn.to_dict()
        assert turn_dict["user_message"] == "Test"
        assert turn_dict["assistant_response"] == "Response"
        assert turn_dict["intent"]["slide_type"] == "title_slide"
        assert "timestamp" in turn_dict


class TestConversationContext:
    """Test cases for ConversationContext dataclass."""
    
    def test_conversation_context_creation(self):
        """Test creating a conversation context."""
        context = ConversationContext(conversation_id="test-conv")
        assert context.conversation_id == "test-conv"
        assert len(context.turns) == 0
        assert context.current_intent is None
        assert isinstance(context.created_at, datetime)
    
    def test_add_turn(self):
        """Test adding a turn to conversation."""
        context = ConversationContext(conversation_id="test-conv")
        intent = GenerationIntent(
            slide_type=SlideType.TITLE_SLIDE,
            content={"title": "Test"}
        )
        
        context.add_turn("User message", "Assistant response", intent)
        
        assert len(context.turns) == 1
        assert context.turns[0].user_message == "User message"
        assert context.current_intent == intent
    
    def test_get_recent_turns(self):
        """Test getting recent turns."""
        context = ConversationContext(conversation_id="test-conv")
        
        for i in range(10):
            context.add_turn(f"Message {i}", f"Response {i}")
        
        recent = context.get_recent_turns(5)
        assert len(recent) == 5
        assert recent[0].user_message == "Message 5"
    
    def test_get_recent_turns_empty(self):
        """Test getting recent turns from empty conversation."""
        context = ConversationContext(conversation_id="test-conv")
        recent = context.get_recent_turns(5)
        assert len(recent) == 0
    
    def test_to_dict(self):
        """Test converting context to dictionary."""
        intent = GenerationIntent(
            slide_type=SlideType.TITLE_SLIDE,
            content={"title": "Test"}
        )
        context = ConversationContext(conversation_id="test-conv")
        context.add_turn("Test", "Response", intent)
        
        context_dict = context.to_dict()
        assert context_dict["conversation_id"] == "test-conv"
        assert len(context_dict["turns"]) == 1
        assert context_dict["current_intent"]["slide_type"] == "title_slide"


class TestConversationManager:
    """Test cases for ConversationManager."""
    
    @patch("myslides.llm.conversation_manager.LLMClient")
    def test_initialization(self, mock_llm_client_class):
        """Test manager initialization."""
        manager = ConversationManager()
        assert manager.llm_client is not None
        assert manager.system_prompt is not None
        assert len(manager.active_conversations) == 0
    
    @patch("myslides.llm.conversation_manager.LLMClient")
    def test_initialization_custom_client(self, mock_llm_client_class):
        """Test manager initialization with custom LLM client."""
        custom_client = Mock(spec=LLMClient)
        manager = ConversationManager(llm_client=custom_client)
        assert manager.llm_client == custom_client
    
    @patch("myslides.llm.conversation_manager.LLMClient")
    def test_create_conversation(self, mock_llm_client_class):
        """Test creating a new conversation."""
        manager = ConversationManager()
        context = manager.create_conversation()
        
        assert context.conversation_id in manager.active_conversations
        assert len(context.turns) == 0
    
    @patch("myslides.llm.conversation_manager.LLMClient")
    def test_create_conversation_custom_id(self, mock_llm_client_class):
        """Test creating conversation with custom ID."""
        manager = ConversationManager()
        context = manager.create_conversation(conversation_id="custom-id")
        
        assert context.conversation_id == "custom-id"
        assert "custom-id" in manager.active_conversations
    
    @patch("myslides.llm.conversation_manager.LLMClient")
    def test_get_conversation(self, mock_llm_client_class):
        """Test getting an existing conversation."""
        manager = ConversationManager()
        context = manager.create_conversation(conversation_id="test-id")
        
        retrieved = manager.get_conversation("test-id")
        assert retrieved is not None
        assert retrieved.conversation_id == "test-id"
    
    @patch("myslides.llm.conversation_manager.LLMClient")
    def test_get_conversation_not_found(self, mock_llm_client_class):
        """Test getting non-existent conversation returns None."""
        manager = ConversationManager()
        retrieved = manager.get_conversation("non-existent")
        assert retrieved is None
    
    def test_process_message_initial_prompt(self):
        """Test processing initial prompt."""
        from myslides.llm.prompt_parser import PromptParser
        mock_parser = Mock(spec=PromptParser)
        mock_llm_client = Mock(spec=LLMClient)
        intent = GenerationIntent(
            slide_type=SlideType.TITLE_SLIDE,
            content={"title": "Test"}
        )
        mock_parser.parse_prompt.return_value = intent
        
        manager = ConversationManager(llm_client=mock_llm_client, prompt_parser=mock_parser)
        response, parsed_intent = manager.process_message(
            "conv-1",
            "Create a title slide",
            initial_prompt=True
        )
        
        assert "I'll create a title_slide slide" in response
        assert parsed_intent.slide_type == SlideType.TITLE_SLIDE
        assert len(manager.get_conversation("conv-1").turns) == 1
    
    def test_process_message_follow_up(self):
        """Test processing follow-up message."""
        from myslides.llm.prompt_parser import PromptParser
        mock_parser = Mock(spec=PromptParser)
        mock_llm_client = Mock(spec=LLMClient)
        initial_intent = GenerationIntent(
            slide_type=SlideType.DATA_CHART,
            content={"title": "Revenue", "chart_data": {"chart_type": "bar_vertical"}}
        )
        refined_intent = GenerationIntent(
            slide_type=SlideType.DATA_CHART,
            content={"title": "Revenue", "chart_data": {"chart_type": "pie"}}
        )
        mock_parser.parse_with_context.return_value = refined_intent
        
        manager = ConversationManager(llm_client=mock_llm_client, prompt_parser=mock_parser)
        context = manager.create_conversation("conv-1")
        context.add_turn("Initial", "Response", initial_intent)
        
        response, parsed_intent = manager.process_message(
            "conv-1",
            "Change to pie chart",
            initial_prompt=False
        )
        
        assert parsed_intent.content["chart_data"]["chart_type"] == "pie"
        assert len(context.turns) == 2
    
    def test_process_message_creates_conversation(self):
        """Test processing message creates conversation if not exists."""
        from myslides.llm.prompt_parser import PromptParser
        mock_parser = Mock(spec=PromptParser)
        mock_llm_client = Mock(spec=LLMClient)
        intent = GenerationIntent(
            slide_type=SlideType.CONTENT_SLIDE,
            content={"title": "Test"}
        )
        mock_parser.parse_prompt.return_value = intent
        
        manager = ConversationManager(llm_client=mock_llm_client, prompt_parser=mock_parser)
        response, parsed_intent = manager.process_message(
            "new-conv",
            "Create a slide"
        )
        
        assert manager.get_conversation("new-conv") is not None
    
    def test_refine_intent(self):
        """Test refining current intent."""
        from myslides.llm.prompt_parser import PromptParser
        mock_parser = Mock(spec=PromptParser)
        mock_llm_client = Mock(spec=LLMClient)
        refined_intent = GenerationIntent(
            slide_type=SlideType.PROCESS_FLOW,
            content={"title": "Updated Process", "steps": ["Step 1", "Step 2"]}
        )
        mock_parser.parse_with_context.return_value = refined_intent
        
        manager = ConversationManager(llm_client=mock_llm_client, prompt_parser=mock_parser)
        context = manager.create_conversation("conv-1")
        initial_intent = GenerationIntent(
            slide_type=SlideType.PROCESS_FLOW,
            content={"title": "Process", "steps": ["Step 1"]}
        )
        context.add_turn("Initial", "Response", initial_intent)
        
        result = manager.refine_intent("conv-1", "Add a second step")
        
        assert result.content["title"] == "Updated Process"
        assert len(result.content["steps"]) == 2
        assert len(context.turns) == 2
    
    @patch("myslides.llm.conversation_manager.LLMClient")
    def test_refine_intent_no_conversation(self, mock_llm_client_class):
        """Test refining intent fails without conversation."""
        manager = ConversationManager()
        
        with pytest.raises(ValueError, match="Conversation.*not found"):
            manager.refine_intent("non-existent", "Refine this")
    
    @patch("myslides.llm.conversation_manager.LLMClient")
    def test_refine_intent_no_current_intent(self, mock_llm_client_class):
        """Test refining intent fails without current intent."""
        manager = ConversationManager()
        manager.create_conversation("conv-1")
        
        with pytest.raises(ValueError, match="No current intent to refine"):
            manager.refine_intent("conv-1", "Refine this")
    
    @patch("myslides.llm.conversation_manager.LLMClient")
    def test_delete_conversation(self, mock_llm_client_class):
        """Test deleting a conversation."""
        manager = ConversationManager()
        manager.create_conversation("conv-1")
        
        result = manager.delete_conversation("conv-1")
        
        assert result is True
        assert manager.get_conversation("conv-1") is None
    
    @patch("myslides.llm.conversation_manager.LLMClient")
    def test_delete_conversation_not_found(self, mock_llm_client_class):
        """Test deleting non-existent conversation returns False."""
        manager = ConversationManager()
        result = manager.delete_conversation("non-existent")
        assert result is False
    
    @patch("myslides.llm.conversation_manager.LLMClient")
    def test_list_conversations(self, mock_llm_client_class):
        """Test listing all active conversations."""
        manager = ConversationManager()
        manager.create_conversation("conv-1")
        manager.create_conversation("conv-2")
        manager.create_conversation("conv-3")
        
        ids = manager.list_conversations()
        
        assert len(ids) == 3
        assert "conv-1" in ids
        assert "conv-2" in ids
        assert "conv-3" in ids
    
    @patch("myslides.llm.conversation_manager.LLMClient")
    def test_list_conversations_empty(self, mock_llm_client_class):
        """Test listing conversations when none exist."""
        manager = ConversationManager()
        ids = manager.list_conversations()
        assert len(ids) == 0
    
    @patch("myslides.llm.conversation_manager.LLMClient")
    def test_generate_response_message_type_change(self, mock_llm_client_class):
        """Test response generation for slide type change."""
        manager = ConversationManager()
        context = ConversationContext(conversation_id="test")
        context.current_intent = GenerationIntent(
            slide_type=SlideType.DATA_CHART,
            content={"title": "Test"}
        )
        
        new_intent = GenerationIntent(
            slide_type=SlideType.PROCESS_FLOW,
            content={"title": "Test"}
        )
        
        response = manager._generate_response_message("Change to process flow", new_intent, context)
        assert "changed the slide type" in response.lower()
    
    @patch("myslides.llm.conversation_manager.LLMClient")
    def test_generate_response_message_title_change(self, mock_llm_client_class):
        """Test response generation for title change."""
        manager = ConversationManager()
        context = ConversationContext(conversation_id="test")
        context.current_intent = GenerationIntent(
            slide_type=SlideType.TITLE_SLIDE,
            content={"title": "Old Title"}
        )
        
        new_intent = GenerationIntent(
            slide_type=SlideType.TITLE_SLIDE,
            content={"title": "New Title"}
        )
        
        response = manager._generate_response_message("Change title", new_intent, context)
        assert "updated the title" in response.lower()
