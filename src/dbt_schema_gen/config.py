"""
Simple .env-driven configuration helper
--------------------------------------

* `LLM_PROVIDER`  – `openai` (default) | `anthropic` | ...
* `OPENAI_API_KEY`, `OPENAI_MODEL`, `OPENAI_TEMPERATURE`
* `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL`, `ANTHROPIC_TEMPERATURE`
"""

import os
from importlib import import_module
from pathlib import Path

from dotenv import load_dotenv

# Load .env from the project root (does nothing if file absent)
load_dotenv(Path.cwd() / ".env")


def getenv(key: str, default=None, *, required: bool = False):
    """Wrapper that can mark a variable as required."""
    value = os.getenv(key, default)
    if required and value is None:
        raise EnvironmentError(f"Environment variable {key} is required but not set.")
    return value


def get_provider_class():
    """Dynamically import the active provider based on LLM_PROVIDER."""
    provider = getenv("LLM_PROVIDER", "openai").lower()
    module_name = f"dbt_schema_gen.llm.{provider}_provider"
    try:
        module = import_module(module_name)
    except ModuleNotFoundError as exc:
        raise ImportError(
            f"No provider named '{provider}'. "
            "Check LLM_PROVIDER or add your own module in dbt_schema_gen.llm.*"
        ) from exc
    class_name = f"{provider.capitalize()}Provider"
    return getattr(module, class_name)
