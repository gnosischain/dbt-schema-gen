"""
Very light Anthropic wrapper.  Requires anthropic>=0.25.

Set:
    ANTHROPIC_API_KEY
    ANTHROPIC_MODEL         – default: claude-3-opus-20240229
    ANTHROPIC_TEMPERATURE   – default: 0.3
"""

from __future__ import annotations

import anthropic

from ..config import getenv
from .base import LLMProvider


class AnthropicProvider(LLMProvider):
    def __init__(self, *, model: str | None = None, temperature: float | None = None):
        self.client = anthropic.Anthropic(api_key=getenv("ANTHROPIC_API_KEY", required=True))
        self.model = model or getenv("ANTHROPIC_MODEL", "claude-3-opus-20240229")
        self.temperature = float(temperature or getenv("ANTHROPIC_TEMPERATURE", 0.3))

    # ---------------------------------------------------------------------

    def generate(self, prompt: str) -> str:
        msg = self.client.messages.create(
            model=self.model,
            max_tokens=4_096,
            temperature=self.temperature,
            system=(
                "You are a meticulous analytics engineer. "
                "Return ONLY valid YAML; no comments or markdown."
            ),
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text.strip()
