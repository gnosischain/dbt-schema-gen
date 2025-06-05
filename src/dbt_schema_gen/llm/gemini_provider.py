"""
Gemini (Google Generative AI) connector with rate-limit retry.

Environment:
  GEMINI_API_KEY         – required
  GEMINI_MODEL           – default: gemini-1.5-pro-latest
  GEMINI_TEMPERATURE     – default: 0.3
  GEMINI_MAX_RETRIES     – default: 5
"""

from __future__ import annotations

import re
import google.generativeai as genai
from google.api_core import exceptions as gexc  # type: ignore

from ..config import getenv
from ..utils import retry_on_rate_limit
from .base import LLMProvider

_SYSTEM_PROMPT = (
    "You are a meticulous analytics engineer. "
    "Return ONLY valid YAML; no comments or markdown."
)


def _gemini_delay(exc: Exception, attempt: int) -> float:
    """Use retry_delay hint if present, else exponential."""
    m = re.search(r"retry_delay\s*{\s*seconds:\s*(\d+)", str(exc))
    return int(m.group(1)) if m else 2**attempt


class GeminiProvider(LLMProvider):
    def __init__(self, *, model: str | None = None, temperature: float | None = None):
        genai.configure(api_key=getenv("GEMINI_API_KEY", required=True))
        self.model_name = model or getenv("GEMINI_MODEL", "gemini-1.5-flash")
        self.temperature = float(temperature or getenv("GEMINI_TEMPERATURE", 0.3))
        self._model = genai.GenerativeModel(self.model_name)

    # raw call
    def _raw_generate(self, prompt: str) -> str:
        resp = self._model.generate_content(
            prompt,
            generation_config={"temperature": self.temperature, "max_output_tokens": 4096},
        )
        return resp.text.strip()

    # public API
    @retry_on_rate_limit(
        errors=(gexc.ResourceExhausted,),
        max_retries_env="GEMINI_MAX_RETRIES",
        default_max_retries=1,        # one extra try is enough for free tier
        get_delay=_gemini_delay,
    )
    def generate(self, prompt: str) -> str:  # type: ignore[override]
        return self._raw_generate(f"{_SYSTEM_PROMPT}\n\n{prompt}")
