"""
Unit tests for LLM Client.
"""
import os
import pytest
from unittest.mock import Mock, patch, MagicMock
from myslides.llm.llm_client import LLMClient, LLMProvider, AuthSettings


class TestLLMClient:
    """Test cases for LLMClient."""
    
    def test_initialization_openai(self):
        """Test initialization with OpenAI provider."""
        with patch("myslides.llm.llm_client.settings") as mock_settings:
            mock_settings.openai_api_key = "test-key"
            
            client = LLMClient(provider=LLMProvider.OPENAI)
            assert client.provider == LLMProvider.OPENAI
            assert client.api_key == "test-key"
    
    def test_initialization_anthropic(self):
        """Test initialization with Anthropic provider."""
        mock_anthropic_mod = MagicMock()
        with patch.dict("sys.modules", {"anthropic": mock_anthropic_mod}):
            with patch("myslides.llm.llm_client.settings") as mock_settings:
                mock_settings.anthropic_api_key = "test-key"
                client = LLMClient(provider=LLMProvider.ANTHROPIC)
                assert client.provider == LLMProvider.ANTHROPIC
                assert client.api_key == "test-key"
                mock_anthropic_mod.Anthropic.assert_called_once_with(api_key="test-key")
    
    def test_initialization_anthropic_import_error(self):
        """Test initialization fails when anthropic is not installed."""
        with patch.dict("sys.modules", {"anthropic": None}):
            with patch("myslides.llm.llm_client.settings") as mock_settings:
                mock_settings.anthropic_api_key = "test-key"
                with pytest.raises(ImportError, match="Anthropic package not installed"):
                    LLMClient(provider=LLMProvider.ANTHROPIC)
    
    def test_initialization_openai_import_error(self):
        """Test initialization fails when openai is not installed."""
        with patch.dict("sys.modules", {"openai": None}):
            with patch("myslides.llm.llm_client.settings") as mock_settings:
                mock_settings.openai_api_key = "test-key"
                with pytest.raises(ImportError, match="OpenAI package not installed"):
                    LLMClient(provider=LLMProvider.OPENAI)
    
    def test_initialization_custom_api_key(self):
        """Test initialization with custom API key override."""
        with patch("openai.OpenAI"):
            client = LLMClient(provider=LLMProvider.OPENAI, api_key="custom-key")
            assert client.api_key == "custom-key"
    
    def test_initialization_no_api_key(self):
        """Test initialization fails without API key."""
        with patch("myslides.llm.llm_client.settings") as mock_settings:
            mock_settings.openai_api_key = None
            
            with pytest.raises(ValueError, match="API key not provided"):
                LLMClient(provider=LLMProvider.OPENAI)
    
    def test_openai_completion(self):
        """Test OpenAI completion generation."""
        with patch("openai.OpenAI") as mock_openai:
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = "Test response"
            
            mock_client = Mock()
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai.return_value = mock_client
            
            client = LLMClient(provider=LLMProvider.OPENAI, api_key="test-key")
            response = client.generate_completion("Test prompt")
            
            assert response == "Test response"
            mock_client.chat.completions.create.assert_called_once()
    
    def test_anthropic_completion(self):
        """Test Anthropic completion generation."""
        mock_anthropic_mod = MagicMock()
        mock_client = Mock()
        mock_response = Mock()
        mock_response.content = [Mock()]
        mock_response.content[0].text = "Test response"
        mock_client.messages.create.return_value = mock_response
        mock_anthropic_mod.Anthropic.return_value = mock_client
        
        with patch.dict("sys.modules", {"anthropic": mock_anthropic_mod}):
            client = LLMClient(provider=LLMProvider.ANTHROPIC, api_key="test-key")
            response = client.generate_completion("Test prompt", system_prompt="System prompt")
            
            assert response == "Test response"
            mock_client.messages.create.assert_called_once()
            call_kwargs = mock_client.messages.create.call_args[1]
            assert call_kwargs["system"] == "System prompt"
            assert call_kwargs["messages"] == [{"role": "user", "content": "Test prompt"}]
    
    def test_json_completion_openai(self):
        """Test JSON completion with OpenAI."""
        with patch("openai.OpenAI") as mock_openai:
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = '{"key": "value"}'
            
            mock_client = Mock()
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai.return_value = mock_client
            
            client = LLMClient(provider=LLMProvider.OPENAI, api_key="test-key")
            response = client.generate_json_completion("Test prompt")
            
            assert response == {"key": "value"}
    
    def test_json_completion_with_markdown_fences(self):
        """Test JSON completion handles markdown code fences from LLM."""
        with patch("openai.OpenAI") as mock_openai:
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = '```json\n{"key": "value"}\n```'
            
            mock_client = Mock()
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai.return_value = mock_client
            
            client = LLMClient(provider=LLMProvider.OPENAI, api_key="test-key")
            response = client.generate_json_completion("Test prompt")
            
            assert response == {"key": "value"}
    
    def test_json_completion_anthropic(self):
        """Test JSON completion with Anthropic."""
        mock_anthropic_mod = MagicMock()
        mock_client = Mock()
        mock_response = Mock()
        mock_response.content = [Mock()]
        mock_response.content[0].text = '```json\n{"key": "anthropic_val"}\n```'
        mock_client.messages.create.return_value = mock_response
        mock_anthropic_mod.Anthropic.return_value = mock_client
        
        with patch.dict("sys.modules", {"anthropic": mock_anthropic_mod}):
            client = LLMClient(provider=LLMProvider.ANTHROPIC, api_key="test-key")
            response = client.generate_json_completion("Test prompt")
            
            assert response == {"key": "anthropic_val"}
    
    def test_json_completion_invalid_json(self):
        """Test JSON completion with invalid JSON response."""
        with patch("openai.OpenAI") as mock_openai:
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = "Not valid JSON"
            
            mock_client = Mock()
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai.return_value = mock_client
            
            client = LLMClient(provider=LLMProvider.OPENAI, api_key="test-key")
            
            with pytest.raises(ValueError, match="Failed to parse LLM response as JSON"):
                client.generate_json_completion("Test prompt")
    
    def test_completion_with_system_prompt(self):
        """Test completion with system prompt."""
        with patch("openai.OpenAI") as mock_openai:
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = "Test response"
            
            mock_client = Mock()
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai.return_value = mock_client
            
            client = LLMClient(provider=LLMProvider.OPENAI, api_key="test-key")
            response = client.generate_completion(
                "Test prompt",
                system_prompt="System instruction"
            )
            
            assert response == "Test response"
            call_args = mock_client.chat.completions.create.call_args
            messages = call_args[1]["messages"]
            assert messages[0]["role"] == "system"
            assert messages[0]["content"] == "System instruction"
    
    def test_completion_with_temperature(self):
        """Test completion with custom temperature."""
        with patch("openai.OpenAI") as mock_openai:
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = "Test response"
            
            mock_client = Mock()
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai.return_value = mock_client
            
            client = LLMClient(provider=LLMProvider.OPENAI, api_key="test-key")
            response = client.generate_completion("Test prompt", temperature=0.5)
            
            assert response == "Test response"
            call_args = mock_client.chat.completions.create.call_args
            assert call_args[1]["temperature"] == 0.5
    
    def test_completion_with_max_tokens(self):
        """Test completion with custom max_tokens."""
        with patch("openai.OpenAI") as mock_openai:
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = "Test response"

            mock_client = Mock()
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai.return_value = mock_client

            client = LLMClient(provider=LLMProvider.OPENAI, api_key="test-key")
            response = client.generate_completion("Test prompt", max_tokens=500)

            assert response == "Test response"
            call_args = mock_client.chat.completions.create.call_args
            assert call_args[1]["max_tokens"] == 500

    def test_initialization_dell_genai(self):
        """Test initialization with Dell GenAI provider."""
        auth_settings = AuthSettings(
            client_id="test-client-id",
            client_secret="test-secret",
            use_sso=False,
            server_side_token_refresh=False
        )

        with patch("openai.OpenAI"):
            with patch("myslides.llm.llm_client.settings") as mock_settings:
                mock_settings.llm_base_url = "https://test.dell.com/genai/dev/v1"
                mock_settings.llm_model = "gpt-oss-120b"

                client = LLMClient(
                    provider=LLMProvider.DELL_GENAI,
                    auth_settings=auth_settings
                )
                assert client.provider == LLMProvider.DELL_GENAI
                assert client.auth_settings == auth_settings

    def test_initialization_dell_genai_no_auth(self):
        """Test initialization fails without auth settings for Dell GenAI."""
        with patch("myslides.llm.llm_client.settings") as mock_settings:
            mock_settings.llm_client_id = None
            mock_settings.llm_client_secret = None
            mock_settings.llm_base_url = "https://test.dell.com/genai/dev/v1"
            mock_settings.llm_model = "gpt-oss-120b"

            # Clear environment variables to prevent fallback
            env_backup = os.environ.copy()
            os.environ.pop("CLIENT_ID", None)
            os.environ.pop("CLIENT_SECRET", None)

            try:
                with pytest.raises(ValueError, match="Auth settings required"):
                    LLMClient(provider=LLMProvider.DELL_GENAI)
            finally:
                os.environ.update(env_backup)

    def test_dell_genai_completion(self):
        """Test Dell GenAI completion generation."""
        auth_settings = AuthSettings(
            client_id="test-client-id",
            client_secret="test-secret",
            use_sso=False,
            server_side_token_refresh=False
        )

        with patch("openai.OpenAI") as mock_openai:
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = "Dell GenAI response"

            mock_client = Mock()
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai.return_value = mock_client

            with patch("myslides.llm.llm_client.settings") as mock_settings:
                mock_settings.llm_base_url = "https://test.dell.com/genai/dev/v1"
                mock_settings.llm_model = "gpt-oss-120b"

                client = LLMClient(
                    provider=LLMProvider.DELL_GENAI,
                    auth_settings=auth_settings
                )
                response = client.generate_completion("Test prompt")

                assert response == "Dell GenAI response"
                mock_client.chat.completions.create.assert_called_once()
                call_kwargs = mock_client.chat.completions.create.call_args[1]
                assert call_kwargs["model"] == "gpt-oss-120b"

    def test_dell_genai_json_completion(self):
        """Test Dell GenAI JSON completion."""
        auth_settings = AuthSettings(
            client_id="test-client-id",
            client_secret="test-secret",
            use_sso=False,
            server_side_token_refresh=False
        )

        with patch("openai.OpenAI") as mock_openai:
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = '{"key": "dell_value"}'

            mock_client = Mock()
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai.return_value = mock_client

            with patch("myslides.llm.llm_client.settings") as mock_settings:
                mock_settings.llm_base_url = "https://test.dell.com/genai/dev/v1"
                mock_settings.llm_model = "gpt-oss-120b"

                client = LLMClient(
                    provider=LLMProvider.DELL_GENAI,
                    auth_settings=auth_settings
                )
                response = client.generate_json_completion("Test prompt")

                assert response == {"key": "dell_value"}

    def test_context_manager(self):
        """Test LLMClient as context manager with Dell GenAI."""
        auth_settings = AuthSettings(
            client_id="test-client-id",
            client_secret="test-secret",
            use_sso=False,
            server_side_token_refresh=False
        )

        mock_http_client = Mock()

        with patch("openai.OpenAI"):
            with patch("httpx.Client", return_value=mock_http_client):
                with patch("myslides.llm.llm_client.settings") as mock_settings:
                    mock_settings.llm_base_url = "https://test.dell.com/genai/dev/v1"
                    mock_settings.llm_model = "gpt-oss-120b"

                    client = LLMClient(
                        provider=LLMProvider.DELL_GENAI,
                        auth_settings=auth_settings
                    )

                    with client:
                        pass

                    mock_http_client.close.assert_called_once()

    def test_close_method(self):
        """Test close method with Dell GenAI."""
        auth_settings = AuthSettings(
            client_id="test-client-id",
            client_secret="test-secret",
            use_sso=False,
            server_side_token_refresh=False
        )

        mock_http_client = Mock()

        with patch("openai.OpenAI"):
            with patch("httpx.Client", return_value=mock_http_client):
                with patch("myslides.llm.llm_client.settings") as mock_settings:
                    mock_settings.llm_base_url = "https://test.dell.com/genai/dev/v1"
                    mock_settings.llm_model = "gpt-oss-120b"

                    client = LLMClient(
                        provider=LLMProvider.DELL_GENAI,
                        auth_settings=auth_settings
                    )

                    client.close()
                    mock_http_client.close.assert_called_once()
