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
from collections import defaultdict, OrderedDict
from pathlib import Path
from typing import Dict, List, Any

import click
import yaml

from .config import get_provider_class
from .extractor import extract_columns_from_sql, get_metadata_from_path
from .renderer import build_prompt

# ─────────────────────────── YAML pretty dumper ────────────────────────────
class _PrettyDumper(yaml.SafeDumper):
    """Block scalars + nice list indent."""

    # handle OrderedDict via existing mapping representer
    pass


_PrettyDumper.add_representer(OrderedDict, yaml.SafeDumper.represent_dict)


def _dump_yaml(obj: dict, fh) -> None:
    yaml.dump(
        obj,
        fh,
        Dumper=_PrettyDumper,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
        width=10_000,  # disable wrapping
    )


# ─────────────────────── LLM reply sanitiser ───────────────────────────────
_FENCE = re.compile(r"^\s*```(?:yaml)?\s*|\s*```$", re.MULTILINE)
_NEEDS_QUOTE = re.compile(r"(\s*description:\s*)([^\"'][^#]*?:[^\"'].*)$")


def _sanitize_yaml(raw: str) -> str:
    """Remove fences & quote colons inside descriptions."""
    cleaned = dedent(_FENCE.sub("", raw)).strip()
    try:
        yaml.safe_load(cleaned)
        return cleaned
    except yaml.YAMLError:
        pass
    return "\n".join(
        f'{m.group(1)}"{m.group(2).strip()}"' if (m := _NEEDS_QUOTE.match(l)) else l
        for l in cleaned.splitlines()
    )


# ───────────────────── Model entry post-processing ─────────────────────────
_UNWANTED = {"version", "schema_version", "model"}
_KEY_ORDER = ["name", "description", "columns", "tags", "refs", "tests", "config"]


def _fix_tests(tests: list[Any]) -> list[Any]:
    """
    Normalise test syntax emitted by the LLM so dbt will accept it.

    • {equal: value: "..."}   ->   {accepted_values: {values: ["..."]}}
    • {equal: "..."}          ->   same rewrite
    • All other tests pass through unchanged.
    """
    fixed = []
    for t in tests:
        if isinstance(t, dict) and len(t) == 1:
            key, val = next(iter(t.items()))

            # -- handle "equal" ------------------------------------------------
            if key == "equal":
                if isinstance(val, str):           # scalar form
                    val = {"value": val}
                # val is now a mapping {"value": "..."} (from LLM or above)
                fixed.append({"accepted_values": {"values": [val["value"]]}})
                continue

        # default: leave untouched
        fixed.append(t)

    return fixed


def _canonise(entry: Dict[str, Any], fallback: str) -> Dict[str, Any]:
    """Ensure required keys, canonical order, and clean tests."""
    entry = dict(entry)  # shallow copy
    entry["name"] = entry.get("name") or fallback

    # singular ref → list
    if "ref" in entry:
        entry["refs"] = entry.get("refs", []) + [entry.pop("ref")]
    if isinstance(entry.get("refs"), str):
        entry["refs"] = [entry["refs"]]

    # column-level tests
    for col in entry.get("columns", []):
        if isinstance(col, dict) and isinstance(col.get("tests"), list):
            col["tests"] = _fix_tests(col["tests"])

    # model-level tests
    if isinstance(entry.get("tests"), list):
        entry["tests"] = _fix_tests(entry["tests"])

    # drop unwanted keys
    for k in list(entry):
        if k in _UNWANTED:
            entry.pop(k)

    # reorder keys
    ordered = OrderedDict()
    for k in _KEY_ORDER:
        if k in entry:
            ordered[k] = entry.pop(k)
    ordered.update(entry)  # add any leftovers
    return ordered


def _add_unique(acc: List[Dict[str, Any]], model: Dict[str, Any]) -> None:
    if model["name"] not in {m["name"] for m in acc}:
        acc.append(model)


# ────────────────────────────── CLI ▶ main ────────────────────────────────
@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.argument(
    "project_path",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    default=".",
)
def cli(project_path: Path) -> None:
    """Generate / refresh schema.yml files under *models/**/*.sql*."""
    llm = get_provider_class()()

    sql_files = list(project_path.joinpath("models").rglob("*.sql"))
    if not sql_files:
        click.echo("No .sql files found under models/", err=True)
        sys.exit(1)

    models_by_dir: Dict[Path, List[Dict[str, Any]]] = defaultdict(list)

    for sql_path in sorted(sql_files):
        if sql_path.name.startswith("_") or sql_path.name.endswith("_tmp.sql"):
            continue

        click.echo(f"↗️  {sql_path.relative_to(project_path)}")

        sector = get_metadata_from_path(sql_path)["sector"] or "unknown"
        src_path = project_path / "models" / sector / f"{sector}_sources.yml"
        if not src_path.exists():
            cand = list(sql_path.parent.glob("*_sources.yml"))
            src_path = cand[0] if cand else None

        prompt = build_prompt(
            model_name=sql_path.stem,
            sector=sector,
            sql_content=sql_path.read_text(),
            columns=extract_columns_from_sql(sql_path),
            sources_yaml=src_path.read_text() if src_path else "",
        )

        try:
            reply = llm.generate(prompt)
            parsed = yaml.safe_load(_sanitize_yaml(reply))
        except Exception as exc:
            click.echo(f"⚠️  skipping {sql_path.name}: {exc}", err=True)
            continue

        # always iterate over a list of model dicts
        model_dicts = parsed.get("models") if isinstance(parsed, dict) and "models" in parsed else [parsed]
        for m in model_dicts:
            _add_unique(models_by_dir[sql_path.parent], _canonise(m, sql_path.stem))

    # write one schema.yml per directory
    for directory, models in models_by_dir.items():
        with (directory / "schema.yml").open("w", encoding="utf-8") as fh:
            _dump_yaml({"version": 2, "models": models}, fh)
        click.echo(f"✅  wrote {directory.relative_to(project_path)}/schema.yml")

    click.echo("All done! 🎉")


if __name__ == "__main__":
    cli()
