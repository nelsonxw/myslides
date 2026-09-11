"""
Dell Dev GenAI Gateway client implementing LLMProvider.
"""
from __future__ import annotations

import os
import uuid
from typing import Any
import httpx
from openai import OpenAI

from myslides.config import settings
from myslides.llm.provider import LLMProvider, extract_json

try:
    from aia_auth import auth as aia_auth  # type: ignore
except ImportError:
    aia_auth = None


class DellAuthHttpx(httpx.Auth):
    """Client-side token injection for Dell GenAI gateway."""

    def __init__(self, client_id: str, client_secret: str, use_sso: bool = False):
        self.client_id = client_id
        self.client_secret = client_secret
        self.use_sso = use_sso
        self._token: str | None = None

    def _get_token(self) -> str:
        if aia_auth is not None:
            token_response = aia_auth.client_credentials(self.client_id, self.client_secret)
            return token_response.token
        env_token = os.getenv("GENAI_ACCESS_TOKEN")
        if env_token:
            return env_token
        raise RuntimeError("No aia_auth package or GENAI_ACCESS_TOKEN provided for Dell GenAI gateway.")

    def auth_flow(self, request: httpx.Request):
        if self._token is None:
            self._token = self._get_token()
        if "Authorization" in request.headers:
            del request.headers["Authorization"]
        if self.client_id:
            request.headers["DI-Client-Id"] = self.client_id
        request.headers["Authorization"] = f"Bearer {self._token}"
        yield request


class DellGatewayProvider:
    """Dell GenAI implementation of LLMProvider."""

    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
    ):
        self.client_id = client_id or settings.client_id
        self.client_secret = client_secret or settings.client_secret
        self.base_url = base_url or settings.llm_base_url
        self.model = model or settings.llm_model

        headers = {
            "x-correlation-id": str(uuid.uuid4()),
        }
        if self.client_id:
            headers["DI-Client-Id"] = self.client_id

        auth = DellAuthHttpx(self.client_id, self.client_secret, settings.use_sso)
        self.http_client = httpx.Client(auth=auth, verify=False, timeout=60.0)
        self.client = OpenAI(
            base_url=self.base_url,
            http_client=self.http_client,
            api_key="not-empty",
            default_headers=headers,
        )

    def complete(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        model = kwargs.pop("model", self.model)
        resp = self.client.chat.completions.create(
            model=model,
            messages=messages,  # type: ignore
            **kwargs,
        )
        return resp.choices[0].message.content or ""

    def complete_json(self, messages: list[dict[str, str]], **kwargs: Any) -> dict[str, Any]:
        raw = self.complete(messages, **kwargs)
        try:
            return extract_json(raw)
        except Exception:
            # Retry once asking strictly for valid JSON
            retry_msgs = list(messages) + [
                {"role": "assistant", "content": raw},
                {"role": "user", "content": "Your previous response was not valid JSON. Please reply with ONLY the JSON object, no commentary, no markdown."},
            ]
            raw2 = self.complete(retry_msgs, **kwargs)
            return extract_json(raw2)

    def close(self) -> None:
        if self.http_client:
            self.http_client.close()


class MockLLMProvider:
    """Deterministic mock provider for offline tests and development."""

    def __init__(self, canned_responses: dict[str, Any] | None = None):
        self.canned_responses = canned_responses or {}
        self.call_history: list[list[dict[str, str]]] = []

    def complete(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        self.call_history.append(messages)
        last_msg = messages[-1]["content"] if messages else ""
        for key, val in self.canned_responses.items():
            if key in last_msg:
                return val if isinstance(val, str) else str(val)
        return '{"archetype": "kpi_summary", "purpose": "demo", "title": "Mock Title", "subtitle": "Mock Subtitle", "shapes": []}'

    def complete_json(self, messages: list[dict[str, str]], **kwargs: Any) -> dict[str, Any]:
        text = self.complete(messages, **kwargs)
        return extract_json(text)
