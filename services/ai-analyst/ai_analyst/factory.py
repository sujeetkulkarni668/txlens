"""Selects a concrete AIProvider from configuration (AI_PROVIDER /
AI_API_KEY / AI_MODEL) — the one place a new vendor gets registered.
"""
from __future__ import annotations

from ai_analyst.provider import AIProvider


def get_ai_provider(*, provider_name: str, api_key: str, model: str) -> AIProvider:
    name = (provider_name or "anthropic").lower().strip()

    if name == "anthropic":
        from ai_analyst.providers.anthropic_provider import AnthropicProvider

        return AnthropicProvider(api_key=api_key, model=model)

    if name in ("gemini", "google"):
        from ai_analyst.providers.gemini_provider import GeminiProvider

        return GeminiProvider(api_key=api_key, model=model or "gemini-1.5-flash")

    if name == "groq":
        from ai_analyst.providers.openai_compatible_provider import OpenAICompatibleProvider

        return OpenAICompatibleProvider(
            api_key=api_key,
            model=model or "llama-3.3-70b-versatile",
            base_url="https://api.groq.com/openai/v1/chat/completions",
        )

    if name == "openrouter":
        from ai_analyst.providers.openai_compatible_provider import OpenAICompatibleProvider

        return OpenAICompatibleProvider(
            api_key=api_key,
            model=model or "google/gemini-2.0-flash-exp:free",
            base_url="https://openrouter.ai/api/v1/chat/completions",
        )

    if name == "openai":
        from ai_analyst.providers.openai_compatible_provider import OpenAICompatibleProvider

        return OpenAICompatibleProvider(
            api_key=api_key,
            model=model or "gpt-4o-mini",
            base_url="https://api.openai.com/v1/chat/completions",
        )

    if name == "ollama":
        from ai_analyst.providers.openai_compatible_provider import OpenAICompatibleProvider

        return OpenAICompatibleProvider(
            api_key=api_key or "ollama",
            model=model or "llama3",
            base_url="http://localhost:11434/v1/chat/completions",
        )

    raise ValueError(
        f"unsupported AI_PROVIDER '{provider_name}' — supported providers: 'gemini' (free), 'groq' (free), 'openrouter' (free), 'anthropic', 'openai', 'ollama'."
    )

