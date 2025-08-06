from __future__ import annotations

import re
from textwrap import dedent
from collections import OrderedDict
from pathlib import Path
from typing import Any

import yaml

__all__ = ["dump_yaml", "sanitize_yaml", "normalize_schema_yaml"]

_FENCE = re.compile(r"^\s*```(?:yaml)?\s*|\s*```$", re.MULTILINE)
_NEED_QUOTE = re.compile(r"(\s*description:\s*)([^\"'][^#]*?:[^\"'].*)$")


def _squash_description(s: str) -> str:
    """Collapse internal newlines/blank lines; trim; single space between tokens."""
    s = (s or "").strip()
    # remove accidental blank lines / extra spaces
    s = re.sub(r"\s*\n\s*", " ", s)
    s = re.sub(r"\s{2,}", " ", s)
    return s


def _dedupe_tests(tests: list[Any] | None) -> list[Any]:
    """Remove duplicate tests (by macro key). Keeps first occurrence."""
    if not tests:
        return []
    out: list[Any] = []
    seen: set[str] = set()
    for t in tests:
        if isinstance(t, str):
            key = t
        elif isinstance(t, dict) and len(t) == 1:
            key = next(iter(t))
        else:
            key = yaml.safe_dump(t, sort_keys=True)
        if key not in seen:
            seen.add(key)
            out.append(t)
    return out


def _dedupe_columns(cols: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """Keep only the first definition for each column name; clean descriptions & tests."""
    if not cols:
        return []
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for col in cols:
        name = (col or {}).get("name")
        if not name:
            continue
        if name in seen:
            # skip duplicates silently
            continue
        seen.add(name)

        col = dict(col)

        # Clean description
        if isinstance(col.get("description"), str):
            col["description"] = _squash_description(col["description"])

        # Clean/dedupe tests
        if isinstance(col.get("tests"), list):
            col["tests"] = _dedupe_tests(col["tests"])
            if not col["tests"]:
                col.pop("tests", None)

        out.append(col)
    return out


def normalize_schema_yaml(text: str) -> str:
    """
    Parse YAML text, fix common LLM issues, and dump back to YAML:
      - collapse description whitespace (model + columns)
      - dedupe columns within a model (keep first)
      - dedupe tests per column and at model level
      - ensure a blank line between models (cosmetic)
    Returns the normalized YAML string. If parsing fails, returns input text.
    """
    try:
        doc = yaml.safe_load(text)
    except Exception:
        return text

    if not isinstance(doc, dict) or "models" not in doc:
        return text

    models = []
    for m in doc.get("models", []):
        if not isinstance(m, dict):
            continue
        mm = dict(m)

        # description cleanup
        if isinstance(mm.get("description"), str):
            mm["description"] = _squash_description(mm["description"])

        # model-level tests (rare): dedupe
        if isinstance(mm.get("tests"), list):
            mm["tests"] = _dedupe_tests(mm["tests"])
            if not mm["tests"]:
                mm.pop("tests", None)

        # columns
        mm["columns"] = _dedupe_columns(mm.get("columns", []))

        models.append(mm)

    out_obj = {"version": doc.get("version", 2), "models": models}
    out = yaml.safe_dump(out_obj, sort_keys=False, allow_unicode=True, width=100000)

    # Cosmetic: ensure a blank line before each new model entry
    out = re.sub(r"\n(\s*)- name:", r"\n\n\1- name:", out, count=0)

    # Cosmetic: remove accidental blank line after 'version'
    out = re.sub(r"^(version:\s*2)\n+", r"\1\n", out, flags=re.M)

    return out


def sanitize_yaml(text: str) -> str:
    """
    Strip ``` fences and quote colons inside description strings.
    If YAML still fails to parse, try quoting suspicious descriptions.
    """
    cleaned = dedent(_FENCE.sub("", text)).strip()
    try:
        yaml.safe_load(cleaned)
        return cleaned
    except yaml.YAMLError:
        pass

    fixed = "\n".join(
        f'{m.group(1)}"{_squash_description(m.group(2))}"'
        if (m := _NEED_QUOTE.match(line))
        else line
        for line in cleaned.splitlines()
    )
    return fixed


def dump_yaml(obj: dict[str, Any], path_or_handle: Path | Any) -> None:
    """Pretty-dump YAML with block scalars and indented lists."""
    class _Pretty(yaml.SafeDumper):
        pass

    _Pretty.add_representer(OrderedDict, yaml.SafeDumper.represent_dict)

    if isinstance(path_or_handle, (str, Path)):
        with Path(path_or_handle).open("w", encoding="utf-8") as fh:
            yaml.dump(
                obj, fh, Dumper=_Pretty, sort_keys=False, allow_unicode=True,
                default_flow_style=False, width=10_000
            )
    else:  # already a file handle
        yaml.dump(
            obj, path_or_handle, Dumper=_Pretty, sort_keys=False,
            allow_unicode=True, default_flow_style=False, width=10_000
        )
