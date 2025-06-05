"""
OpenAI implementation (works with openai>=1.x).
Set environment variables:

    OPENAI_API_KEY       – required
    OPENAI_MODEL         – default: gpt-4o-mini
    OPENAI_TEMPERATURE   – default: 0.3  (float)
"""

from __future__ import annotations

import openai
from openai import RateLimitError

from ..config import getenv
from ..utils import retry_on_rate_limit
from .base import LLMProvider

_SYSTEM = "You are a meticulous analytics engineer. Return ONLY valid YAML; no comments or markdown."


class OpenaiProvider(LLMProvider):
    def __init__(self, *, model: str | None = None, temperature: float | None = None):
        self.client = openai.OpenAI(api_key=getenv("OPENAI_API_KEY", required=True))
        self.model = model or getenv("OPENAI_MODEL", "gpt-3.5-turbo-0125")
        self.temperature = float(temperature or getenv("OPENAI_TEMPERATURE", 0.3))

    def _raw_generate(self, prompt: str) -> str:
        resp = self.client.chat.completions.create(
            model=self.model,
            temperature=self.temperature,
            messages=[{"role": "system", "content": _SYSTEM}, {"role": "user", "content": prompt}],
        )
        return resp.choices[0].message.content.strip()

    @retry_on_rate_limit(
        errors=(RateLimitError,),
        max_retries_env="OPENAI_MAX_RETRIES",
        default_max_retries=3,
    )
    def generate(self, prompt: str) -> str:  # type: ignore[override]
        return self._raw_generate(prompt)
