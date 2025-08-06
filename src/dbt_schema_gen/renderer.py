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

        Produce a COMPLETE dbt schema.yml entry for the model `{model_name}`.

        Hard requirements
        -----------------
        • Output YAML ONLY — no prose, no Markdown fences, no comments.
        • Must start with `version: 2`.
        • Top-level key MUST be `models:` with a single list item for this model.
        • The model item MUST include:
          - name: {model_name}
          - description: (helpful, business-facing; use a folded block scalar `>`; no blank lines)
          - config: (include `access: public`; may include `tags` and `materialized` if clearly inferable)
          - meta: (include `owner`, `authoritative: false`, `generated_by: "schema-writer"`;
                   add `inference_notes` only if something was inferred)
          - columns: (list EVERY column that appears in the SELECT, in exact order; do not invent columns)
        • Do NOT include example blocks or placeholders. Emit only the final YAML.

        Columns — required keys per column
        ----------------------------------
        For each column under `columns:` output:
          - name
          - description (concise; note units/range if numeric; use a single line or folded scalar `>` without blank lines)
          - data_type (infer if missing; prefer warehouse-native types consistent with the sources)
          - tests (YAML list) — MINIMIZE tests:
              · Only add `not_null` for keys and timestamps that are obviously non-null.
              · Only add `unique` for an obvious single-column primary key.
              · If uncertain, OMIT tests for that column entirely.

        Tests — allowed forms (strict)
        ------------------------------
        • Put tests ONLY under the column’s `tests:` list (correct indentation).
        • Allowed simple tests: `not_null`, `unique`.
        • Relationships test is allowed ONLY when clearly inferable AND must be nested exactly as:
            tests:
              - relationships:
                  to: ref('target_model')            # OR: source('source_name','table_name')
                  field: target_pk
          (The value of `to` MUST be a single scalar string using ref()/source(); never `to: source:`.)
        • Composite uniqueness goes at the MODEL level (not per column) ONLY when clearly inferable:
            tests:
              - dbt_utils.unique_combination_of_columns:
                  combination_of_columns: ["col_a","col_b"]
                  severity: error
        • Do not repeat the same test for a column. A column may have at most one `not_null` and at most one `unique`.

        Inference heuristics
        --------------------
        • Columns source of truth (in order of precedence):
          1) “Columns parsed from the SELECT clause” → use exactly these names and this order.
          2) If empty, parse from the SQL and infer carefully.
        • Primary key:
          - If a single obvious key exists (e.g., `*_id`, `transaction_hash`), add `unique` + `not_null`.
          - If a multi-column natural key is obvious (e.g., `block_number` + `log_index`), add the model-level
            `dbt_utils.unique_combination_of_columns`. If not obvious, skip.
        • Foreign keys / relationships:
          - Only add a `relationships` test if the SQL references `ref()`/`source()` AND the FK is clear by name.
          - Otherwise omit it.
        • Data types:
          - Prefer `UInt64`, `Float64`, `String`, `DateTime` / `DateTime64(0, 'UTC')`, `JSON` consistent with provided sources YAML.
          - Hashes/addresses → `String`. Amounts in wei/gwei → `UInt64` or `String` if overflow risk.
        • Enums:
          - Only add `accepted_values` when explicit values are evident; otherwise omit.
        • Timestamps:
          - `*_timestamp`, `created_at`, `updated_at` → `DateTime` or `DateTime64(0, 'UTC')`.
        • Quoting:
          - If a name is a reserved keyword or contains hyphens/spaces, add `quote: true` at the model level.

        Final output validation (self-check before you answer)
        ------------------------------------------------------
        • Ensure the YAML parses and contains exactly: `version: 2` and one `models:` entry.
        • Ensure there are NO duplicate column names.
        • Ensure no column has duplicate test macros (e.g., two `not_null`).
        • Ensure any `relationships.to` is a scalar `ref('...')` or `source('...','...')`, never a nested map.
        • Ensure descriptions use folded scalars `>` where multiline and contain no empty lines.
        • Do not include empty strings or trailing blank lines in any scalar.

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
