"""Test Dell Dev GenAI LLM connection."""
import sys
import os
import io
from pathlib import Path

# Set UTF-8 encoding for stdout
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from myslides.config import settings
from myslides.llm.llm_client import LLMClient, LLMProvider

def test_dell_genai():
    """Test Dell GenAI connection with a simple prompt."""
    print("Testing Dell Dev GenAI connection...")
    print(f"CLIENT_ID: {settings.llm_client_id}")
    print(f"CLIENT_SECRET: {settings.llm_client_secret[:10] if settings.llm_client_secret else None}...")

    try:
        # Initialize client (auto-detects Dell GenAI with loaded settings)
        client = LLMClient()
        print(f"Provider detected: {client.provider}")

        # Test a simple completion
        print("\nSending test prompt...")
        response = client.generate_completion(
            "Say 'Hello from Dell GenAI' in one sentence.",
            temperature=0.3,
            max_tokens=50
        )

        print(f"\nResponse: {response}")
        print("\nDell GenAI connection successful!")
        return True

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_dell_genai()
    sys.exit(0 if success else 1)
