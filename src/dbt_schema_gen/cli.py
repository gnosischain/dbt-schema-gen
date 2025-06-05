"""
Command-line entry point.
Run `dbt-schema-gen --help` for options.
"""

from __future__ import annotations

import sys
from pathlib import Path

import click
import yaml

from .config import get_provider_class
from .extractor import (
    extract_columns_from_sql,
    get_metadata_from_path,
)
from .renderer import build_prompt


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.argument(
    "project_path",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    default=".",
)
def cli(project_path: Path):
    """
    Generate dbt `schema.yml` files for every model in *PROJECT_PATH*.

    The tool walks all `*.sql` under `PROJECT_PATH/models/**`.
    """
    provider_cls = get_provider_class()
    llm = provider_cls()

    sql_files = list(project_path.joinpath("models").rglob("*.sql"))
    if not sql_files:
        click.echo("No .sql files found under models/. Nothing to do.", err=True)
        sys.exit(1)

    for sql_file in sql_files:
        # Skip temporary or disabled models
        if sql_file.name.startswith("_") or sql_file.name.endswith("_tmp.sql"):
            continue

        metadata = get_metadata_from_path(sql_file)
        sector = metadata["sector"] or "unknown"

        # Try models/<sector>/{sector}_sources.yml first, fall back to any *_sources.yml in same dir
        sector_sources_path = (
            project_path
            / "models"
            / sector
            / f"{sector}_sources.yml"
        )
        if not sector_sources_path.exists():
            # Fallback: first *_sources.yml in same directory
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
        schema_text = llm.generate(prompt)

        # Validate YAML before writing (optional but nice)
        try:
            yaml.safe_load(schema_text)
        except yaml.YAMLError as exc:
            click.echo(
                f"⚠️  LLM returned invalid YAML for {sql_file} – skipping.\n{exc}",
                err=True,
            )
            continue

        out_path = sql_file.parent / "schema.yml"
        out_path.write_text(schema_text, encoding="utf-8")
        click.echo(f"✅  wrote {out_path.relative_to(project_path)}")

    click.echo("All done! 🎉")
