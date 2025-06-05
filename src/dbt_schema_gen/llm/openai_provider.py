"""
OpenAI implementation (works with openai>=1.x).
Set environment variables:

    OPENAI_API_KEY       – required
    OPENAI_MODEL         – default: gpt-4o-mini
    OPENAI_TEMPERATURE   – default: 0.3  (float)
"""

from __future__ import annotations

import openai

from ..config import getenv
from .base import LLMProvider


class OpenaiProvider(LLMProvider):
    def __init__(self, *, model: str | None = None, temperature: float | None = None):
        api_key = getenv("OPENAI_API_KEY", required=True)
        self.client = openai.OpenAI(api_key=api_key)

        self.model = model or getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.temperature = float(temperature or getenv("OPENAI_TEMPERATURE", 0.3))

    # ---------------------------------------------------------------------

    def generate(self, prompt: str) -> str:
        """One-shot ChatCompletion call – returns the assistant content."""
        response = self.client.chat.completions.create(
            model=self.model,
            temperature=self.temperature,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a meticulous analytics engineer. "
                        "Return ONLY valid YAML; no comments or markdown."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
        )
        return response.choices[0].message.content.strip()
