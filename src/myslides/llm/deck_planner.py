"""
Deck Planner for MySlides.

Plans multi-slide deck structures from natural language prompts.
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from myslides.llm.llm_client import LLMClient, LLMProvider
from myslides.llm.prompt_parser import PromptParser
from myslides.generation.generation_models import GenerationIntent, SlideType


@dataclass
class DeckPlan:
    """Structured plan for a multi-slide deck."""
    title: str
    description: str
    slide_intents: List[GenerationIntent] = field(default_factory=list)
    estimated_slide_count: int = 0
    suggested_flow: List[str] = field(default_factory=list)  # Flow description for each slide
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert deck plan to dictionary."""
        return {
            "title": self.title,
            "description": self.description,
            "slide_intents": [
                {
                    "slide_type": intent.slide_type.value,
                    "content": intent.content,
                    "data_type": intent.data_type,
                    "element_preferences": intent.element_preferences,
                    "color_preference": intent.color_preference,
                    "tone": intent.tone
                }
                for intent in self.slide_intents
            ],
            "estimated_slide_count": self.estimated_slide_count,
            "suggested_flow": self.suggested_flow
        }


class DeckPlanner:
    """Plans multi-slide deck structures from prompts."""
    
    def __init__(self, llm_client: Optional[LLMClient] = None):
        """
        Initialize deck planner.
        
        Args:
            llm_client: Optional LLM client (defaults to OpenAI if not provided)
        """
        self.llm_client = llm_client or LLMClient(provider=LLMProvider.OPENAI)
        self.system_prompt = self._build_system_prompt()
    
    def _build_system_prompt(self) -> str:
        """Build the system prompt for deck planning."""
        return """You are an expert at planning presentation decks from natural language requests.

Your task is to analyze a user's request for a multi-slide presentation and create a structured deck plan with:
1. A clear title for the deck
2. A brief description of the deck's purpose
3. A logical flow of slides (typically 5-15 slides)
4. For each slide, extract the structured intent (slide type, content, etc.)

Common deck structures:
- Pitch deck: Title, Problem, Solution, Market, Business Model, Competition, Traction, Team, Ask
- Product demo: Title, Overview, Features, Use Cases, Pricing, Call to Action
- Educational: Title, Learning Objectives, Key Concepts, Examples, Summary, Resources
- Progress report: Title, Executive Summary, Key Metrics, Achievements, Challenges, Next Steps

Supported slide types:
- title_slide, content_slide, section_header, text_heavy, comparison, process_flow, timeline,
  org_chart, data_chart, matrix, funnel, pyramid, dashboard, image_showcase, table_view, mixed

Respond with valid JSON only, no additional text."""
    
    def plan_deck(self, prompt: str) -> DeckPlan:
        """
        Plan a multi-slide deck from a natural language prompt.
        
        Args:
            prompt: The user's request for a deck (e.g., "Create a 10-slide pitch deck for a fintech startup")
        
        Returns:
            DeckPlan object with structured slide intents
        """
        user_prompt = self._build_user_prompt(prompt)
        
        response = self.llm_client.generate_json_completion(
            prompt=user_prompt,
            system_prompt=self.system_prompt,
            temperature=0.5,
            max_tokens=2000
        )
        
        return self._response_to_deck_plan(response)
    
    def _build_user_prompt(self, prompt: str) -> str:
        """Build the user prompt for the LLM."""
        return f"""Analyze the following deck generation request and create a structured deck plan:

User Request: "{prompt}"

Extract the following fields in JSON format:
{{
  "title": "deck title",
  "description": "brief description of deck purpose",
  "slide_intents": [
    {{
      "slide_type": "title_slide",
      "content": {{
        "title": "slide title",
        "subtitle": "optional subtitle"
      }},
      "tone": "professional"
    }},
    {{
      "slide_type": "content_slide",
      "content": {{
        "title": "slide title",
        "bullet_points": ["point1", "point2"]
      }},
      "tone": "professional"
    }}
  ],
  "suggested_flow": [
    "Brief description of slide 1 purpose",
    "Brief description of slide 2 purpose"
  ]
}}

Create a logical flow with appropriate slide types. Ensure the deck has a clear beginning, middle, and end."""
    
    def _response_to_deck_plan(self, response: Dict[str, Any]) -> DeckPlan:
        """
        Convert LLM response to DeckPlan.
        
        Args:
            response: Parsed JSON response from LLM
        
        Returns:
            DeckPlan object
        """
        slide_intents = []
        for intent_dict in response.get("slide_intents", []):
            slide_intents.append(PromptParser.response_to_intent(intent_dict))
        
        return DeckPlan(
            title=response.get("title", "Untitled Deck"),
            description=response.get("description", ""),
            slide_intents=slide_intents,
            estimated_slide_count=len(slide_intents),
            suggested_flow=response.get("suggested_flow", [])
        )
    
    def refine_deck_plan(
        self,
        current_plan: DeckPlan,
        refinement_prompt: str
    ) -> DeckPlan:
        """
        Refine an existing deck plan based on user feedback.
        
        Args:
            current_plan: The current deck plan
            refinement_prompt: User's refinement request (e.g., "Add a slide about competitors")
        
        Returns:
            Refined DeckPlan object
        """
        user_prompt = self._build_refinement_prompt(current_plan, refinement_prompt)
        
        response = self.llm_client.generate_json_completion(
            prompt=user_prompt,
            system_prompt=self.system_prompt,
            temperature=0.5,
            max_tokens=2000
        )
        
        return self._response_to_deck_plan(response)
    
    def _build_refinement_prompt(self, current_plan: DeckPlan, refinement_prompt: str) -> str:
        """Build a prompt for refining an existing deck plan."""
        return f"""Current deck plan:
Title: {current_plan.title}
Description: {current_plan.description}
Slide count: {current_plan.estimated_slide_count}

Current slides:
{self._format_current_slides(current_plan)}

User refinement request: "{refinement_prompt}"

Update the deck plan according to the user's request. Return the updated plan in the same JSON format."""
    
    def _format_current_slides(self, plan: DeckPlan) -> str:
        """Format current slides for display in prompt."""
        lines = []
        for i, intent in enumerate(plan.slide_intents, 1):
            lines.append(f"{i}. {intent.slide_type.value}: {intent.content.get('title', 'Untitled')}")
        return "\n".join(lines)
