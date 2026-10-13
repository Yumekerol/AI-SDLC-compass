"""
Google Gemini LLM Provider Implementation
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


class GoogleProvider(BaseLLMProvider):
    """Google Gemini API provider via REST API."""

    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key or settings.google_api_key
        self.model = model or settings.google_model
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"

    async def generate_text(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.2,
    ) -> str:
        url = f"{self.base_url}/models/{self.model}:generateContent?key={self.api_key}"
        contents = []
        if system_prompt:
            contents.append({"role": "user", "parts": [{"text": f"SYSTEM INSTRUCTION: {system_prompt}"}]})
        contents.append({"role": "user", "parts": [{"text": prompt}]})

        payload = {
            "contents": contents,
            "generationConfig": {"temperature": temperature},
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]

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
