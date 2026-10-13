"""
LLM Provider Factory & Package Initialization
"""

from __future__ import annotations

import logging

from ..config import Settings, settings
from .anthropic_provider import AnthropicProvider
from .base_provider import BaseLLMProvider
from .google_provider import GoogleProvider
from .mock_provider import MockLLMProvider
from .ollama_provider import OllamaProvider
from .openai_provider import OpenAIProvider

logger = logging.getLogger(__name__)


def get_llm_provider(custom_settings: Settings | None = None) -> BaseLLMProvider:
    """
    Factory to retrieve configured LLM provider.
    Defaults to Ollama; if Ollama is not configured or fails, falls back gracefully.
    """
    cfg = custom_settings or settings
    provider_type = cfg.llm_provider.lower() if isinstance(cfg.llm_provider, str) else cfg.llm_provider.value

    if provider_type == "openai" and cfg.openai_api_key:
        return OpenAIProvider(api_key=cfg.openai_api_key, model=cfg.openai_model)
    elif provider_type == "anthropic" and cfg.anthropic_api_key:
        return AnthropicProvider(api_key=cfg.anthropic_api_key, model=cfg.anthropic_model)
    elif provider_type == "google" and cfg.google_api_key:
        return GoogleProvider(api_key=cfg.google_api_key, model=cfg.google_model)
    elif provider_type == "ollama":
        return OllamaProvider(host=cfg.ollama_host, model=cfg.llm_model)

    # Fallback or default
    return MockLLMProvider()


__all__ = [
    "BaseLLMProvider",
    "OllamaProvider",
    "OpenAIProvider",
    "AnthropicProvider",
    "GoogleProvider",
    "MockLLMProvider",
    "get_llm_provider",
]
