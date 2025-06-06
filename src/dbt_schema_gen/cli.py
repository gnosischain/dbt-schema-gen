"""
dbt-schema-gen CLI
------------------

* Runs from project root **or** any folder beneath `models/`.
* Skips LLM + file-touch when columns unchanged (unless -o / --overwrite).
* Flags:
    -m / --models     comma-sep names to process
    -o / --overwrite  always regenerate
    --skip-tests      strip every tests: block
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List, Any

import click
import yaml

from .config import get_provider_class
from .extractor import extract_columns_from_sql, get_metadata_from_path
from .renderer import build_prompt
from .utils import pathing, yaml_tools, tests


# ───────────────────────── CLI ────────────────────────────────────────
@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option(
    "-m",
    "--models",
    multiple=True,
    help="Only process these model names (repeatable or comma-separated).",
)
@click.option(
    "-o",
    "--overwrite",
    is_flag=True,
    default=False,
    help="Force overwrite even if existing columns are unchanged.",
)
@click.option(
    "--skip-tests",
    is_flag=True,
    default=False,
    help="Remove all tests blocks from generated YAML.",
)
@click.argument(
    "path",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    default=".",
)
def cli(path: Path, models: tuple[str], overwrite: bool, skip_tests: bool) -> None:
    selected = {m.strip() for chunk in models for m in chunk.split(",")} if models else None

    models_root = pathing.find_models_root(path)
    project_root = models_root.parent

    scan_root = path.resolve() if path.resolve().is_relative_to(models_root) else models_root

    sql_paths = list(pathing.sql_files(scan_root, selected))
    if not sql_paths:
        click.echo("No matching *.sql files found.", err=True)
        sys.exit(1)

    llm = get_provider_class()()
    updates: Dict[Path, List[Dict[str, Any]]] = {}

    for sql in sorted(sql_paths):
        folder = sql.parent
        schema_path = folder / "schema.yml"
        if schema_path.exists():
            doc = yaml.safe_load(schema_path.read_text())
            existing_by_name = {m["name"]: m for m in doc.get("models", [])}
        else:
            existing_by_name = {}

        inferred_cols = set(extract_columns_from_sql(sql))
        if (
            not overwrite
            and sql.stem in existing_by_name
            and inferred_cols == {c["name"] for c in existing_by_name[sql.stem]["columns"]}
        ):
            click.echo(f"⏭️  {sql.relative_to(project_root)} (columns unchanged)")
            continue

        click.echo(f"↗️  {sql.relative_to(project_root)}")

        sector = get_metadata_from_path(sql)["sector"] or "unknown"
        src = models_root / sector / f"{sector}_sources.yml"
        if not src.exists():
            alts = list(folder.glob("*_sources.yml"))
            src = alts[0] if alts else None

        prompt = build_prompt(
            model_name=sql.stem,
            sector=sector,
            sql_content=sql.read_text(),
            columns=list(inferred_cols),
            sources_yaml=src.read_text() if src else "",
        )

        try:
            parsed = yaml.safe_load(yaml_tools.sanitize_yaml(llm.generate(prompt)))
        except Exception as exc:
            click.echo(f"⚠️  skipping {sql.name}: {exc}", err=True)
            continue

        blocks = parsed["models"] if isinstance(parsed, dict) and "models" in parsed else [parsed]
        canonised = [
            tests.canonise_model(b, sql.stem, strip_tests=skip_tests) for b in blocks
        ]
        updates.setdefault(folder, []).extend(canonised)

    # merge + write
    for folder, new_models in updates.items():
        path_schema = folder / "schema.yml"
        if path_schema.exists():
            doc = yaml.safe_load(path_schema.read_text())
            current = {m["name"]: m for m in doc.get("models", [])}
        else:
            current = {}

        for nm in new_models:
            current[nm["name"]] = nm

        yaml_tools.dump_yaml({"version": 2, "models": list(current.values())}, path_schema)
        click.echo(f"✅  wrote {path_schema.relative_to(project_root)}")

    click.echo("All done! 🎉")


if __name__ == "__main__":
    cli()
