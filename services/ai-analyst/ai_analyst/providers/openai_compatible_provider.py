"""OpenAI-compatible implementation of AIProvider.

Supports Groq, OpenRouter, DeepSeek, OpenAI, Ollama, Together, and any
OpenAI-compatible completions endpoint.
"""
from __future__ import annotations

import httpx

from ai_analyst.provider import AIProvider, AIProviderError


class OpenAICompatibleProvider(AIProvider):
    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str = "https://api.openai.com/v1/chat/completions",
    ):
        if not api_key and "localhost" not in base_url and "127.0.0.1" not in base_url:
            raise ValueError("AI_API_KEY is required")
        if not model:
            raise ValueError("AI_MODEL is required")
        self._api_key = api_key
        self._model = model
        self._base_url = base_url

    async def complete(self, *, system: str, user: str) -> str:
        headers = {
            "Content-Type": "application/json",
        }
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        }
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(self._base_url, json=payload, headers=headers)
                if resp.status_code != 200:
                    raise AIProviderError(f"AI API error ({resp.status_code}): {resp.text}")
                data = resp.json()
                choices = data.get("choices", [])
                if not choices:
                    raise AIProviderError("API returned no completion choices")
                message = choices[0].get("message", {})
                content = message.get("content", "")
                if not content:
                    raise AIProviderError("API response message content was empty")
                return content
        except Exception as exc:
            if isinstance(exc, AIProviderError):
                raise
            raise AIProviderError(f"AI request failed: {exc}") from exc
