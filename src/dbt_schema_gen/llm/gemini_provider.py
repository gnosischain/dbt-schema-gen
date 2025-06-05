
"""
Gemini (Google Generative AI) connector
--------------------------------------

Environment variables
---------------------
GEMINI_API_KEY        – **required** (aka GOOGLE_API_KEY)
GEMINI_MODEL          – optional, default: "gemini-1.5-flash"
GEMINI_TEMPERATURE    – optional, default: 0.3
"""

from __future__ import annotations

import google.generativeai as genai

from ..config import getenv
from .base import LLMProvider

_SYSTEM_RULES = (
    "You are a meticulous analytics engineer. "
    "Return ONLY valid YAML; no comments or markdown."
)


class GeminiProvider(LLMProvider):
    def __init__(self, *, model: str | None = None, temperature: float | None = None):
        api_key = getenv("GEMINI_API_KEY", required=True)     
        genai.configure(api_key=api_key)

        self.model_name   = model or getenv("GEMINI_MODEL", "gemini-1.5-flash")
        self.temperature  = float(temperature or getenv("GEMINI_TEMPERATURE", 0.3))
        self._model       = genai.GenerativeModel(self.model_name)

    # ------------------------------------------------------------------ #
    def generate(self, prompt: str) -> str:
        """
        Merge system rules + user prompt into **one** user message.
        The SDK then returns `GenerativeModelResponse`; `.text` holds the answer.
        """
        full_prompt = f"{_SYSTEM_RULES}\n\n{prompt}"
        response = self._model.generate_content(
            full_prompt,
            generation_config={
                "temperature": self.temperature,
                "max_output_tokens": 4096,
            },
        )
        return response.text.strip()
