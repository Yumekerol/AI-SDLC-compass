"""
Anthropic Claude LLM Provider Implementation
"""

from __future__ import annotations

import json
import logging
from typing import TypeVar

import httpx
from pydantic import BaseModel

from ..config import settings
from .base_provider import BaseLLMProvider
from .ollama_provider import extract_json_from_text

logger = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude API provider."""

    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key or settings.anthropic_api_key
        self.model = model or settings.anthropic_model
        self.base_url = "https://api.anthropic.com/v1"

    async def generate_text(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.2,
    ) -> str:
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        payload = {
            "model": self.model,
            "max_tokens": 4096,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
        }
        if system_prompt:
            payload["system"] = system_prompt

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(f"{self.base_url}/messages", headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["content"][0]["text"]

    async def generate_structured(
        self,
        prompt: str,
        response_schema: type[T],
        system_prompt: str = "",
        temperature: float = 0.2,
    ) -> T:
        schema_json = json.dumps(response_schema.model_json_schema(), indent=2)
        full_system = (
            f"{system_prompt}\n\n"
            f"You MUST respond ONLY with a valid JSON object matching this schema:\n{schema_json}"
        )
        text = await self.generate_text(prompt, system_prompt=full_system, temperature=temperature)
        parsed = extract_json_from_text(text)
        return response_schema.model_validate(parsed)
