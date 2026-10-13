"""
LLM Provider Abstraction Layer

Defines the abstract interface for all LLM providers (Ollama, OpenAI, Anthropic, Google).
Enforces structured outputs via Pydantic schema validation.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class BaseLLMProvider(ABC):
    """Abstract interface for LLM backends."""

    @abstractmethod
    async def generate_text(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.2,
    ) -> str:
        """Generate unstructured text response."""
        pass

    @abstractmethod
    async def generate_structured(
        self,
        prompt: str,
        response_schema: type[T],
        system_prompt: str = "",
        temperature: float = 0.2,
    ) -> T:
        """
        Generate structured response validated against a Pydantic model schema.
        Handles JSON parsing, schema conformance, and retries if needed.
        """
        pass
