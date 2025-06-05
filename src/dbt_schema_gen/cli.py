"""
Command-line entry point for dbt-schema-gen.

Usage:
    dbt-schema-gen /path/to/dbt/project

The script walks every `*.sql` under `models/**` and writes exactly one
`schema.yml` per directory, containing *all* models in that directory.
"""
from __future__ import annotations

import sys
import re
from textwrap import dedent
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Any

import click
import yaml

from .config import get_provider_class
from .extractor import extract_columns_from_sql, get_metadata_from_path
from .renderer import build_prompt

# ─────────────────────────────────────────────────────────────────────────────
# helper utilities
# ─────────────────────────────────────────────────────────────────────────────
def _sanitize_yaml(raw: str) -> str:
    """
    Clean the raw LLM reply so PyYAML can parse it.

    1. Remove ```yaml / ``` fences if present.
    2. Dedent so YAML starts at column-0.
    3. If YAML still fails to load, quote colon-containing `description:` lines.
    """
    # 1) strip code fences
    fenced = re.sub(r"^\s*```(?:yaml)?\s*|\s*```$", "", raw, flags=re.MULTILINE)
    cleaned = dedent(fenced).strip()

    # 2) quick parse test
    try:
        yaml.safe_load(cleaned)
        return cleaned
    except yaml.YAMLError:
        pass

    # 3) quote suspicious description lines
    def _quote_colon(line: str) -> str:
        m = re.match(r"(\s*description:\s*)([^\"'][^#]*?:[^\"'].*)$", line)
        if m:
            return f'{m.group(1)}"{m.group(2).strip()}"'
        return line

    fixed = "\n".join(_quote_colon(l) for l in cleaned.splitlines())
    return fixed


def _ensure_unique(existing: List[Dict[str, Any]], new: Dict[str, Any]) -> None:
    """Append *new* model entry only if its name is not already present."""
    names = {m.get("name") for m in existing}
    if new.get("name") not in names:
        existing.append(new)


# ─────────────────────────────────────────────────────────────────────────────
# main Click CLI
# ─────────────────────────────────────────────────────────────────────────────
@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.argument(
    "project_path",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    default=".",
)
def cli(project_path: Path) -> None:
    """
    Generate dbt `schema.yml` files for every model in *PROJECT_PATH*.

    Exactly one `schema.yml` is produced per directory; existing files are
    overwritten.
    """
    provider_cls = get_provider_class()
    llm = provider_cls()

    sql_files = list(project_path.joinpath("models").rglob("*.sql"))
    if not sql_files:
        click.echo("No .sql files found under models/. Nothing to do.", err=True)
        sys.exit(1)

    # collect model entries keyed by their parent directory
    models_by_dir: Dict[Path, List[Dict[str, Any]]] = defaultdict(list)

    for sql_file in sorted(sql_files):
        # skip disabled or temp models
        if sql_file.name.startswith("_") or sql_file.name.endswith("_tmp.sql"):
            continue

        rel = sql_file.relative_to(project_path)
        click.echo(f"↗️  generating schema for {rel}")

        # ── gather context ────────────────────────────────────────────────
        metadata = get_metadata_from_path(sql_file)
        sector = metadata["sector"] or "unknown"

        sector_sources_path = (
            project_path / "models" / sector / f"{sector}_sources.yml"
        )
        if not sector_sources_path.exists():
            # fallback: any *_sources.yml in same dir
            candidates = list(sql_file.parent.glob("*_sources.yml"))
            sector_sources_path = candidates[0] if candidates else None

        sources_yaml = sector_sources_path.read_text() if sector_sources_path else ""

        sql_content = sql_file.read_text()
        columns = extract_columns_from_sql(sql_file)

        prompt = build_prompt(
            model_name=sql_file.stem,
            sector=sector,
            sql_content=sql_content,
            columns=columns,
            sources_yaml=sources_yaml,
        )

        # ── call the LLM and parse YAML ───────────────────────────────────
        try:
            raw_reply   = llm.generate(prompt)
            schema_text = _sanitize_yaml(raw_reply)
            schema_obj  = yaml.safe_load(schema_text)
        except Exception as exc:
            click.echo(f"⚠️  skipping {sql_file.name}: {exc}", err=True)
            continue

        # accept either full document or a single-model dict
        if isinstance(schema_obj, dict) and "models" in schema_obj:
            for entry in schema_obj["models"]:
                _ensure_unique(models_by_dir[sql_file.parent], entry)
        else:
            _ensure_unique(models_by_dir[sql_file.parent], schema_obj)

    # ── write one schema.yml per directory ────────────────────────────────
    for directory, models in models_by_dir.items():
        out_path = directory / "schema.yml"
        out_doc  = {"version": 2, "models": models}

        with out_path.open("w", encoding="utf-8") as fh:
            yaml.dump(out_doc, fh, sort_keys=False, allow_unicode=True)

        click.echo(f"✅  wrote {out_path.relative_to(project_path)}")

    click.echo("All done! 🎉")


if __name__ == "__main__":  # pragma: no cover
    cli()
