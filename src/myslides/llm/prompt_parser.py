"""
Prompt Parser for MySlides.

Converts natural language prompts into structured GenerationIntent objects
using LLM-based intent extraction.
"""
from typing import Optional, Dict, Any
from myslides.llm.llm_client import LLMClient, LLMProvider
from myslides.generation.generation_models import (
    GenerationIntent,
    SlideType,
    ChartSubType,
)


class PromptParser:
    """Parses natural language prompts into structured generation intents."""
    
    def __init__(self, llm_client: Optional[LLMClient] = None):
        """
        Initialize prompt parser.
        
        Args:
            llm_client: Optional LLM client (defaults to OpenAI if not provided)
        """
        self.llm_client = llm_client or LLMClient(provider=LLMProvider.OPENAI)
        self.system_prompt = self._build_system_prompt()
    
    def _build_system_prompt(self) -> str:
        """Build the system prompt for intent extraction."""
        return """You are an expert at analyzing slide generation requests and extracting structured intent.

Your task is to analyze a user's natural language request for creating a PowerPoint slide and extract:
1. The slide type (from the predefined list)
2. The content structure (title, subtitle, steps, events, chart data, etc.)
3. Any element preferences (shapes, layouts, etc.)
4. Color preferences if specified
5. The tone/style (professional, casual, creative, etc.)

Supported slide types:
- title_slide: Cover slides with title and subtitle
- content_slide: General content with body text
- section_header: Section divider slides
- text_heavy: Bullet points or paragraph-heavy slides
- comparison: Side-by-side comparisons (2-column, 3-column)
- process_flow: Linear or branching process diagrams
- timeline: Horizontal or vertical timelines
- org_chart: Hierarchical organization charts
- data_chart: Charts (bar, line, pie, etc.)
- matrix: Quadrant or matrix layouts
- funnel: Funnel diagrams
- pyramid: Pyramid diagrams
- dashboard: Multiple charts/metrics
- image_showcase: Image-focused slides
- table_view: Table-focused slides
- mixed: Combination of multiple element types

Chart sub-types:
- bar_vertical, bar_horizontal, bar_stacked, bar_grouped
- line_single, line_multi
- pie, donut
- area, scatter, combo, waterfall

Respond with valid JSON only, no additional text."""
    
    def parse_prompt(self, prompt: str) -> GenerationIntent:
        """
        Parse a natural language prompt into a GenerationIntent.
        
        Args:
            prompt: The user's natural language request
        
        Returns:
            GenerationIntent object with extracted structured data
        """
        user_prompt = self._build_user_prompt(prompt)
        
        response = self.llm_client.generate_json_completion(
            prompt=user_prompt,
            system_prompt=self.system_prompt,
            temperature=0.3,
            max_tokens=1000
        )
        
        return self._response_to_intent(response)
    
    def _build_user_prompt(self, prompt: str) -> str:
        """Build the user prompt for the LLM."""
        return f"""Analyze the following slide generation request and extract the structured intent:

User Request: "{prompt}"

Extract the following fields in JSON format:
{{
  "slide_type": "one of the supported slide types",
  "content": {{
    "title": "main title",
    "subtitle": "optional subtitle",
    "body_text": "optional body text",
    "bullet_points": ["optional", "list", "of", "items"],
    "steps": ["step1", "step2"] or [{{"label": "Step 1", "description": "...", "number": 1}}],
    "events": [{{"date": "2020", "title": "Event", "description": "..."}}],
    "chart_data": {{
      "chart_type": "bar_vertical",
      "title": "chart title",
      "categories": ["Q1", "Q2", "Q3", "Q4"],
      "series_data": {{"Series A": [100, 150, 200, 180]}},
      "has_legend": true,
      "show_data_labels": false
    }}
  }},
  "data_type": "optional data type hint",
  "element_preferences": ["optional", "style", "preferences"],
  "color_preference": "optional color scheme name",
  "tone": "professional"
}}

Only include fields that are relevant to the request. For process flows, include steps. For timelines, include events. For charts, include chart_data."""
    
    @staticmethod
    def normalize_slide_type(slide_type_str: str) -> SlideType:
        """Normalize a slide type string to a SlideType enum."""
        if not slide_type_str:
            return SlideType.CONTENT_SLIDE
            
        cleaned = slide_type_str.strip().lower()
        
        # Direct enum value match
        try:
            return SlideType(cleaned)
        except ValueError:
            pass
            
        # Common aliases
        aliases = {
            "title": SlideType.TITLE_SLIDE,
            "cover": SlideType.TITLE_SLIDE,
            "content": SlideType.CONTENT_SLIDE,
            "body": SlideType.CONTENT_SLIDE,
            "bullets": SlideType.TEXT_HEAVY,
            "text": SlideType.TEXT_HEAVY,
            "process": SlideType.PROCESS_FLOW,
            "flow": SlideType.PROCESS_FLOW,
            "steps": SlideType.PROCESS_FLOW,
            "workflow": SlideType.PROCESS_FLOW,
            "chart": SlideType.DATA_CHART,
            "graph": SlideType.DATA_CHART,
            "bar_chart": SlideType.DATA_CHART,
            "pie_chart": SlideType.DATA_CHART,
            "line_chart": SlideType.DATA_CHART,
            "side_by_side": SlideType.COMPARISON,
            "vs": SlideType.COMPARISON,
            "compare": SlideType.COMPARISON,
            "milestones": SlideType.TIMELINE,
            "roadmap": SlideType.TIMELINE,
            "hierarchy": SlideType.ORG_CHART,
            "table": SlideType.TABLE_VIEW,
            "image": SlideType.IMAGE_SHOWCASE,
            "images": SlideType.IMAGE_SHOWCASE,
        }
        return aliases.get(cleaned, SlideType.CONTENT_SLIDE)

    @staticmethod
    def normalize_chart_subtype(chart_type_str: str) -> ChartSubType:
        """Normalize a chart type string to a ChartSubType enum."""
        if not chart_type_str:
            return ChartSubType.BAR_VERTICAL
            
        cleaned = chart_type_str.strip().lower()
        
        try:
            return ChartSubType(cleaned)
        except ValueError:
            pass
            
        aliases = {
            "bar": ChartSubType.BAR_VERTICAL,
            "column": ChartSubType.BAR_VERTICAL,
            "horizontal_bar": ChartSubType.BAR_HORIZONTAL,
            "stacked_bar": ChartSubType.BAR_STACKED,
            "grouped_bar": ChartSubType.BAR_GROUPED,
            "line": ChartSubType.LINE_SINGLE,
            "line_chart": ChartSubType.LINE_SINGLE,
            "multi_line": ChartSubType.LINE_MULTI,
            "pie_chart": ChartSubType.PIE,
            "donut_chart": ChartSubType.DONUT,
            "doughnut": ChartSubType.DONUT,
        }
        return aliases.get(cleaned, ChartSubType.BAR_VERTICAL)

    @classmethod
    def response_to_intent(cls, response: Dict[str, Any]) -> GenerationIntent:
        """
        Convert LLM response dict to GenerationIntent.
        
        Args:
            response: Parsed JSON response from LLM
        
        Returns:
            GenerationIntent object
        """
        slide_type_str = response.get("slide_type", "content_slide")
        slide_type = cls.normalize_slide_type(slide_type_str)
        
        # Convert chart_type string to ChartSubType if present
        content = response.get("content", {})
        if not isinstance(content, dict):
            content = {}
            
        if "chart_data" in content and isinstance(content["chart_data"], dict) and "chart_type" in content["chart_data"]:
            chart_raw = content["chart_data"]["chart_type"]
            if isinstance(chart_raw, str):
                content["chart_data"]["chart_type"] = cls.normalize_chart_subtype(chart_raw)
        
        return GenerationIntent(
            slide_type=slide_type,
            content=content,
            data_type=response.get("data_type"),
            element_preferences=response.get("element_preferences", []),
            color_preference=response.get("color_preference"),
            tone=response.get("tone", "professional")
        )

    def _response_to_intent(self, response: Dict[str, Any]) -> GenerationIntent:
        """Internal adapter delegating to response_to_intent."""
        return self.response_to_intent(response)
    
    def parse_with_context(
        self,
        prompt: str,
        previous_intent: Optional[GenerationIntent] = None,
        conversation_history: Optional[list] = None
    ) -> GenerationIntent:
        """
        Parse a prompt with conversational context.
        
        Args:
            prompt: The user's current request
            previous_intent: Previous generation intent for context
            conversation_history: List of previous conversation turns
        
        Returns:
            GenerationIntent object with refined intent
        """
        if not previous_intent and not conversation_history:
            # No context, use standard parsing
            return self.parse_prompt(prompt)
        
        # Build context-aware prompt
        context_prompt = self._build_context_prompt(
            prompt, previous_intent, conversation_history
        )
        
        response = self.llm_client.generate_json_completion(
            prompt=context_prompt,
            system_prompt=self.system_prompt,
            temperature=0.3,
            max_tokens=1000
        )
        
        return self._response_to_intent(response)
    
    def _build_context_prompt(
        self,
        prompt: str,
        previous_intent: Optional[GenerationIntent],
        conversation_history: Optional[list]
    ) -> str:
        """Build a context-aware prompt for conversational refinement."""
        context_parts = []
        
        if previous_intent:
            context_parts.append(f"Previous slide intent: {previous_intent}")
        
        if conversation_history:
            context_parts.append("Conversation history:")
            for turn in conversation_history[-3:]:  # Last 3 turns
                context_parts.append(f"  User: {turn.get('user', '')}")
                context_parts.append(f"  Assistant: {turn.get('assistant', '')}")
        
        context_str = "\n".join(context_parts)
        
        return f"""{context_str}

Current user request: "{prompt}"

Analyze the current request in the context of the previous interaction. Extract the refined structured intent in the same JSON format as before."""
