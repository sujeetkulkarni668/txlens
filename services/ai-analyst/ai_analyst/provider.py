"""Provider-agnostic LLM interface (product spec section 15 / requirement
5: "Create a provider abstraction so the LLM provider can be changed
through configuration").

Nothing outside this module and app/core/config.py should know which LLM
vendor is in use.
"""
from __future__ import annotations

from abc import ABC, abstractmethod


class AIProviderError(Exception):
    """Raised for transport/auth/rate-limit failures talking to the LLM
    provider — distinct from AIOutputError (a bad response body), so
    callers can tell "couldn't reach the model" apart from "model
    responded but not usefully"."""


class AIProvider(ABC):
    @abstractmethod
    async def complete(self, *, system: str, user: str) -> str:
        """Send a system+user prompt, return the raw text completion.
        Must raise AIProviderError on transport/auth failures — never
        return an empty string or fabricate a response."""
