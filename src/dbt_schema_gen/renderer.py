"""
Prompt builder and response post-processing.
If you want more advanced formatting, swap in a Jinja template here.
"""

from __future__ import annotations

from textwrap import dedent
from typing import List


def build_prompt(
    *,
    model_name: str,
    sector: str | None,
    sql_content: str,
    columns: List[str],
    sources_yaml: str | None,
) -> str:
    """Return the string sent to the LLM."""
    return dedent(
        f"""
        You are an expert analytics engineer working on a dbt project.

        Please craft a **COMPLETE** dbt `schema.yml` entry for the model `{model_name}`.

        Requirements
        ------------
        • Include `version: 2` at the top.  
        • Fill out a helpful model‐level `description`.  
        • Emit a `columns:` section that lists **every** column with:
          – `name`, `description`, `data_type` (guess if missing), and a `tests:` array
            (start with `not_null`, and add `unique` or other reasonable tests).  
        • Retain tags, refs or any other metadata you deem useful.  
        • Output **YAML only** – no prose explanations or Markdown fences.

        Context
        -------
        ### Raw model SQL
        {sql_content}

        ### Columns parsed from the SELECT clause
        {", ".join(columns) or "*(parser did not find columns – infer from SQL)*"}

        ### Sector-level sources YAML ({sector or "unknown"}_sources.yml)
        {sources_yaml or "*no sources file found*"}
        """
    ).strip()
