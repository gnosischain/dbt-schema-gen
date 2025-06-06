"""
Very light Anthropic wrapper.  Requires anthropic>=0.25.

Set:
    ANTHROPIC_API_KEY
    ANTHROPIC_MODEL         – default: claude-3-opus-20240229
    ANTHROPIC_TEMPERATURE   – default: 0.3
"""

from __future__ import annotations

import anthropic
from anthropic import RateLimitError

from ..config import getenv
from ..utils.rate_limiter import retry_on_rate_limit
from .base import LLMProvider

_SYSTEM = "You are a meticulous analytics engineer. Return ONLY valid YAML; no comments or markdown."


class AnthropicProvider(LLMProvider):
    def __init__(self, *, model: str | None = None, temperature: float | None = None):
        self.client = anthropic.Anthropic(api_key=getenv("ANTHROPIC_API_KEY", required=True))
        self.model = model or getenv("ANTHROPIC_MODEL", "claude-3-sonnet-20240229")
        self.temperature = float(temperature or getenv("ANTHROPIC_TEMPERATURE", 0.3))

    def _raw_generate(self, prompt: str) -> str:
        msg = self.client.messages.create(
            model=self.model,
            temperature=self.temperature,
            system=_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4096,
        )
        return msg.content[0].text.strip()

    @retry_on_rate_limit(
        errors=(RateLimitError,),
        max_retries_env="ANTHROPIC_MAX_RETRIES",
        default_max_retries=3,
    )
    def generate(self, prompt: str) -> str:  # type: ignore[override]
        return self._raw_generate(prompt)
