"""Anthropic implementation of AIProvider.

NOT executed in the environment that generated this repo — no network
access and the `anthropic` package isn't installed here. Syntax-checked
only (see docs/roadmap.md / README limitations). Validate for real once
AI_API_KEY is set in your environment.
"""
from __future__ import annotations

from ai_analyst.provider import AIProvider, AIProviderError


class AnthropicProvider(AIProvider):
    def __init__(self, api_key: str, model: str):
        if not api_key:
            raise ValueError("AI_API_KEY is required for the anthropic provider")
        if not model:
            raise ValueError("AI_MODEL is required for the anthropic provider")
        # Imported lazily so importing this module doesn't require the
        # `anthropic` package unless the provider is actually used.
        import anthropic

        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self._model = model

    async def complete(self, *, system: str, user: str) -> str:
        try:
            response = await self._client.messages.create(
                model=self._model,
                max_tokens=1500,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
        except Exception as exc:  # noqa: BLE001 — wrap any SDK/transport error uniformly
            raise AIProviderError(f"Anthropic API call failed: {exc}") from exc

        text_blocks = [block.text for block in response.content if getattr(block, "type", None) == "text"]
        if not text_blocks:
            raise AIProviderError("Anthropic response contained no text content")
        return "".join(text_blocks)
