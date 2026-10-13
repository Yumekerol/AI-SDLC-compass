"""
Ollama LLM Provider Implementation

Connects to local Ollama instance (default: http://localhost:11434).
Zero cost, runs locally, no API keys or cloud accounts required.
"""

from __future__ import annotations

import json
import logging
import re
from typing import TypeVar

import httpx
from pydantic import BaseModel

from ..config import settings
from .base_provider import BaseLLMProvider

logger = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)


def extract_json_from_text(text: str) -> dict:
    """Extract and parse first valid JSON block from LLM output."""
    # Try direct parse
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass

    # Try markdown json block
    match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # Try curly brackets span
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not extract valid JSON from LLM output: {text[:200]}...")


class OllamaProvider(BaseLLMProvider):
    """Local Ollama provider using HTTP API."""

    def __init__(
        self,
        host: str | None = None,
        model: str | None = None,
    ):
        self.host = (host or settings.ollama_host).rstrip("/")
        self.model = model or settings.llm_model

    async def generate_text(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.2,
    ) -> str:
        url = f"{self.host}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": system_prompt,
            "stream": False,
            "options": {"temperature": temperature},
        }

        async with httpx.AsyncClient(timeout=90.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data.get("response", "")

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
            f"You MUST respond ONLY with a valid JSON object conforming to this schema:\n"
            f"{schema_json}\n"
            f"Do not include any explanation or markdown formatting outside the JSON."
        )

        url = f"{self.host}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": full_system,
            "format": "json",
            "stream": False,
            "options": {"temperature": temperature},
        }

        async with httpx.AsyncClient(timeout=90.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            raw_text = data.get("response", "")

        parsed_json = extract_json_from_text(raw_text)
        return response_schema.model_validate(parsed_json)
