"""Google Gemini implementation of AIProvider using standard HTTP REST."""
from __future__ import annotations

import httpx

from ai_analyst.provider import AIProvider, AIProviderError


class GeminiProvider(AIProvider):
    def __init__(self, api_key: str, model: str = "gemini-1.5-flash"):
        if not api_key:
            raise ValueError("AI_API_KEY is required for the gemini provider")
        self._api_key = api_key
        self._model = model or "gemini-1.5-flash"

    async def complete(self, *, system: str, user: str) -> str:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self._model}:generateContent?key={self._api_key}"
        payload = {
            "system_instruction": {
                "parts": [{"text": system}]
            },
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": user}]
                }
            ],
            "generationConfig": {
                "temperature": 0.1,
                "responseMimeType": "application/json"
            }
        }
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code != 200:
                    raise AIProviderError(f"Gemini API error ({resp.status_code}): {resp.text}")
                data = resp.json()
                candidates = data.get("candidates", [])
                if not candidates:
                    raise AIProviderError("Gemini returned no response candidates")
                parts = candidates[0].get("content", {}).get("parts", [])
                if not parts:
                    raise AIProviderError("Gemini returned empty parts")
                return parts[0].get("text", "")
        except Exception as exc:
            if isinstance(exc, AIProviderError):
                raise
            raise AIProviderError(f"Gemini request failed: {exc}") from exc
