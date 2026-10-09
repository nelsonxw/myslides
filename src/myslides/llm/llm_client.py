"""
LLM Client for MySlides.

Provides a unified interface for interacting with Dell Dev GenAI gateway,
OpenAI, and Anthropic APIs.
"""
from enum import Enum
from typing import Optional, Dict, Any, List
from collections.abc import Generator
import json
import os
import uuid
from dataclasses import dataclass
import httpx

from myslides.config import settings


@dataclass
class AuthSettings:
    """Authentication settings for Dell Dev GenAI."""
    client_id: str
    client_secret: str
    use_sso: bool
    server_side_token_refresh: bool


class LLMProvider(Enum):
    """Supported LLM providers."""
    GEMINI = "gemini"
    DELL_GENAI = "dell_genai"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


class LLMClient:
    """Unified client for LLM API interactions."""

    def __init__(
        self,
        provider: Optional[LLMProvider] = None,
        api_key: Optional[str] = None,
        auth_settings: Optional[AuthSettings] = None
    ):
        """
        Initialize LLM client.

        Args:
            provider: The LLM provider to use (Dell GenAI, OpenAI, or Anthropic)
                      Defaults to Dell GenAI if credentials are available, otherwise OpenAI
            api_key: Optional API key override (defaults to settings)
            auth_settings: Optional auth settings for Dell GenAI
        """
        # Auto-detect provider if not specified
        if provider is None:
            provider = self._auto_detect_provider()

        self.provider = provider
        self.api_key = api_key or self._get_default_api_key()
        self.auth_settings = auth_settings or self._get_auth_settings()
        self._client = None
        self._http_client = None
        self._initialize_client()

    def _auto_detect_provider(self) -> LLMProvider:
        """Auto-detect the best available provider based on credentials."""
        # Check for Gemini API key first if configured
        if settings.gemini_api_key or os.getenv("GEMINI_API_KEY"):
            return LLMProvider.GEMINI

        # Check for Dell GenAI credentials
        if (settings.llm_client_id and settings.llm_client_secret) or \
           (os.getenv("CLIENT_ID") and os.getenv("CLIENT_SECRET")):
            return LLMProvider.DELL_GENAI

        # Fall back to OpenAI if API key is available
        if settings.openai_api_key or os.getenv("OPENAI_API_KEY"):
            return LLMProvider.OPENAI

        # Fall back to Anthropic if API key is available
        if settings.anthropic_api_key or os.getenv("ANTHROPIC_API_KEY"):
            return LLMProvider.ANTHROPIC

        # Default to Dell GenAI (will fail if no credentials)
        return LLMProvider.DELL_GENAI

    def _get_default_api_key(self) -> Optional[str]:
        """Get default API key from settings based on provider."""
        if self.provider == LLMProvider.GEMINI:
            return settings.gemini_api_key or os.getenv("GEMINI_API_KEY")
        elif self.provider == LLMProvider.OPENAI:
            return settings.openai_api_key
        elif self.provider == LLMProvider.ANTHROPIC:
            return settings.anthropic_api_key
        elif self.provider == LLMProvider.DELL_GENAI:
            return "not-empty"  # Placeholder, actual auth via headers
        return None

    def _get_auth_settings(self) -> Optional[AuthSettings]:
        """Get auth settings for Dell GenAI from environment."""
        if self.provider != LLMProvider.DELL_GENAI:
            return None

        client_id = settings.llm_client_id or os.getenv("CLIENT_ID", "")
        client_secret = settings.llm_client_secret or os.getenv("CLIENT_SECRET", "")
        use_sso = settings.llm_use_sso or os.getenv("USE_SSO", "false").lower() == "true"
        server_side_token_refresh = (
            settings.llm_server_side_token_refresh or
            os.getenv("ENABLE_TOKEN_REFRESH_AT_SERVER_SIDE", "false").lower() == "true"
        )

        if not client_id or not client_secret:
            return None

        return AuthSettings(
            client_id=client_id,
            client_secret=client_secret,
            use_sso=use_sso,
            server_side_token_refresh=server_side_token_refresh
        )

    def _initialize_client(self) -> None:
        """Initialize the appropriate client based on provider."""
        if self.provider == LLMProvider.GEMINI:
            self._initialize_gemini()
        elif self.provider == LLMProvider.DELL_GENAI:
            self._initialize_dell_genai()
        elif self.provider == LLMProvider.OPENAI:
            self._initialize_openai()
        elif self.provider == LLMProvider.ANTHROPIC:
            self._initialize_anthropic()
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

    def _initialize_gemini(self) -> None:
        """Initialize Google Gemini client."""
        if not self.api_key:
            raise ValueError("API key not provided for Gemini. Set GEMINI_API_KEY in .env")
        self._http_client = httpx.Client(timeout=60.0)

    def _initialize_dell_genai(self) -> None:
        """Initialize Dell Dev GenAI client with authentication."""
        if not self.auth_settings:
            raise ValueError("Auth settings required for Dell GenAI provider")

        try:
            from openai import OpenAI

            # Create auth provider for token refresh
            auth = _DellGenAIAuthProvider(self.auth_settings)

            # Create HTTP client with auth
            self._http_client = httpx.Client(auth=auth, verify=False)

            correlation_id = str(uuid.uuid4())
            default_headers = {
                "x-correlation-id": correlation_id,
            }
            if self.auth_settings.client_id:
                default_headers["DI-Client-Id"] = self.auth_settings.client_id

            # Initialize OpenAI client with custom base URL and HTTP client
            self._client = OpenAI(
                base_url=settings.llm_base_url,
                http_client=self._http_client,
                api_key="not-empty",
                default_headers=default_headers
            )
        except ImportError:
            raise ImportError("OpenAI package not installed. Install with: pip install openai")
        except Exception as e:
            # Clean up HTTP client if initialization fails
            if self._http_client:
                self._http_client.close()
                self._http_client = None
            raise

    def _initialize_openai(self) -> None:
        """Initialize OpenAI client."""
        if not self.api_key:
            raise ValueError("API key not provided for OpenAI")
        try:
            from openai import OpenAI
            self._client = OpenAI(api_key=self.api_key)
        except ImportError:
            raise ImportError("OpenAI package not installed. Install with: pip install openai")

    def _initialize_anthropic(self) -> None:
        """Initialize Anthropic client."""
        if not self.api_key:
            raise ValueError("API key not provided for Anthropic")
        try:
            import anthropic
            self._client = anthropic.Anthropic(api_key=self.api_key)
        except ImportError:
            raise ImportError("Anthropic package not installed. Install with: pip install anthropic")

    def close(self) -> None:
        """Close the HTTP client if open."""
        if self._http_client:
            self._http_client.close()
            self._http_client = None
    
    def generate_completion(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 3000,
        json_mode: bool = False
    ) -> str:
        """
        Generate a completion from the LLM.

        Args:
            prompt: The user prompt
            system_prompt: Optional system prompt for context
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens to generate
            json_mode: If True, request JSON output (OpenAI/Dell GenAI only)

        Returns:
            The generated text response
        """
        if self.provider == LLMProvider.GEMINI:
            return self._gemini_completion(
                prompt, system_prompt, temperature, max_tokens, json_mode
            )
        elif self.provider == LLMProvider.DELL_GENAI:
            return self._dell_genai_completion(
                prompt, system_prompt, temperature, max_tokens, json_mode
            )
        elif self.provider == LLMProvider.OPENAI:
            return self._openai_completion(
                prompt, system_prompt, temperature, max_tokens, json_mode
            )
        elif self.provider == LLMProvider.ANTHROPIC:
            return self._anthropic_completion(
                prompt, system_prompt, temperature, max_tokens
            )
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

    def _gemini_completion(
        self,
        prompt: str,
        system_prompt: Optional[str],
        temperature: float,
        max_tokens: int,
        json_mode: bool
    ) -> str:
        """Generate completion using Google Gemini REST API with demand spike fallback."""
        primary_model = settings.gemini_model or "gemini-3.8-flash"
        candidate_models = [primary_model]
        if primary_model != "gemini-3.5-flash-lite":
            candidate_models.append("gemini-3.5-flash-lite")

        last_error = None
        for model in candidate_models:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.api_key}"

            payload: Dict[str, Any] = {
                "contents": [
                    {
                        "parts": [{"text": prompt}]
                    }
                ],
                "generationConfig": {
                    "temperature": temperature,
                    "maxOutputTokens": max_tokens,
                }
            }

            if system_prompt:
                payload["systemInstruction"] = {
                    "parts": [{"text": system_prompt}]
                }

            if json_mode:
                payload["generationConfig"]["responseMimeType"] = "application/json"

            try:
                response = self._http_client.post(url, json=payload, timeout=20.0)
                if response.status_code == 200:
                    data = response.json()
                    candidates = data.get("candidates", [])
                    if not candidates:
                        return ""
                    content = candidates[0].get("content", {})
                    parts = content.get("parts", [])
                    return parts[0].get("text", "") if parts else ""
                elif response.status_code in (503, 429) and model != candidate_models[-1]:
                    # Temporary demand spike on this model, fallback to next candidate
                    continue
                else:
                    last_error = f"Gemini API error ({response.status_code}): {response.text}"
            except Exception as e:
                last_error = str(e)
                if model != candidate_models[-1]:
                    continue

        raise RuntimeError(last_error or "Gemini API failed")

    def generate_embedding(self, text: str, dimension: int = 384) -> List[float]:
        """Generate vector embedding for text using configured provider."""
        if self.provider == LLMProvider.GEMINI:
            model = settings.gemini_embedding_model or "text-embedding-004"
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:embedContent?key={self.api_key}"
            payload = {
                "model": f"models/{model}",
                "content": {
                    "parts": [{"text": text}]
                },
                "outputDimensionality": dimension
            }
            response = self._http_client.post(url, json=payload)
            if response.status_code != 200:
                raise RuntimeError(f"Gemini Embedding error ({response.status_code}): {response.text}")
            data = response.json()
            values = data.get("embedding", {}).get("values", [])
            if len(values) > dimension:
                values = values[:dimension]
            return values
        raise NotImplementedError(f"Embeddings not supported for provider: {self.provider}")

    def _dell_genai_completion(
        self,
        prompt: str,
        system_prompt: Optional[str],
        temperature: float,
        max_tokens: int,
        json_mode: bool
    ) -> str:
        """Generate completion using Dell Dev GenAI API."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        kwargs = {
            "model": settings.llm_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        response = self._client.chat.completions.create(**kwargs)
        return response.choices[0].message.content

    def _openai_completion(
        self,
        prompt: str,
        system_prompt: Optional[str],
        temperature: float,
        max_tokens: int,
        json_mode: bool
    ) -> str:
        """Generate completion using OpenAI API."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        kwargs = {
            "model": "gpt-4o",
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        response = self._client.chat.completions.create(**kwargs)
        return response.choices[0].message.content

    def _anthropic_completion(
        self,
        prompt: str,
        system_prompt: Optional[str],
        temperature: float,
        max_tokens: int
    ) -> str:
        """Generate completion using Anthropic API."""
        kwargs = {
            "model": "claude-3-5-sonnet-20241022",
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}]
        }

        if system_prompt:
            kwargs["system"] = system_prompt

        response = self._client.messages.create(**kwargs)
        return response.content[0].text
    
    def generate_json_completion(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 3000
    ) -> Dict[str, Any]:
        """
        Generate a JSON completion from the LLM.

        Args:
            prompt: The user prompt
            system_prompt: Optional system prompt for context
            temperature: Sampling temperature (lower for more deterministic JSON)
            max_tokens: Maximum tokens to generate

        Returns:
            Parsed JSON dictionary
        """
        if self.provider in (LLMProvider.DELL_GENAI, LLMProvider.OPENAI):
            response = self.generate_completion(
                prompt, system_prompt, temperature, max_tokens, json_mode=True
            )
        else:
            # For Anthropic, we need to explicitly request JSON in the prompt
            json_instruction = "\n\nRespond with valid JSON only, no additional text."
            response = self.generate_completion(
                prompt + json_instruction, system_prompt, temperature, max_tokens
            )

        # Clean markdown code fences if present in LLM response
        text = response.strip()
        if text.startswith("```"):
            first_line_end = text.find("\n")
            if first_line_end != -1:
                text = text[first_line_end + 1:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            # Attempt to repair truncated JSON (common when LLM hits max_tokens)
            repaired = text.rstrip()
            if repaired.count('"') % 2 == 1:
                repaired += '"'
            open_brackets = repaired.count('[') - repaired.count(']')
            open_braces = repaired.count('{') - repaired.count('}')
            repaired += (']' * max(0, open_brackets)) + ('}' * max(0, open_braces))
            try:
                return json.loads(repaired)
            except Exception:
                raise ValueError(f"Failed to parse LLM response as JSON: {e}\nResponse: {response}")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


class _DellGenAIAuthProvider(httpx.Auth):
    """Authentication provider for Dell Dev GenAI with client-side token refresh."""

    def __init__(self, auth_settings: AuthSettings):
        self.auth_settings = auth_settings
        self._token = None

    def auth_flow(self, request):
        """Implement httpx.Auth auth_flow for client-side token refresh."""
        if self._token is None:
            self._token = self._get_oauth_token()

        # Remove any Authorization header that OpenAI might add
        if 'Authorization' in request.headers:
            del request.headers['Authorization']

        # Add DI-Client-Id header for Dell GenAI authentication
        if self.auth_settings.client_id:
            request.headers['DI-Client-Id'] = self.auth_settings.client_id

        # Add Bearer token
        request.headers['Authorization'] = f'Bearer {self._token}'

        yield request

    def _get_oauth_token(self) -> str:
        """Get OAuth token using client credentials or env fallback."""
        # Try to use aia_auth if available (Dell internal)
        try:
            from aia_auth import auth
            token_response = auth.client_credentials(
                self.auth_settings.client_id,
                self.auth_settings.client_secret,
            )
            return token_response.token
        except Exception as e:
            # Fallback to environment variable for public distribution
            token = os.getenv("GENAI_ACCESS_TOKEN")
            if token:
                return token
            raise RuntimeError(
                f"Failed to get OAuth token: {e}. "
                "The 'aia_auth' package is not installed or failed. "
                "Provide a pre-generated token via the GENAI_ACCESS_TOKEN environment variable "
                "or install the Dell internal 'aia_auth' helper."
            )
