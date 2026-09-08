"""Selects a concrete AIProvider from configuration (AI_PROVIDER /
AI_API_KEY / AI_MODEL) — the one place a new vendor gets registered.
"""
from __future__ import annotations

from ai_analyst.provider import AIProvider


def get_ai_provider(*, provider_name: str, api_key: str, model: str) -> AIProvider:
    if provider_name == "anthropic":
        from ai_analyst.providers.anthropic_provider import AnthropicProvider

        return AnthropicProvider(api_key=api_key, model=model)

    raise ValueError(
        f"unsupported AI_PROVIDER '{provider_name}' — only 'anthropic' is implemented. "
        "Add a new ai_analyst/providers/<name>_provider.py implementing AIProvider and "
        "register it here to support another vendor."
    )
