"""
Helpers for normalising / stripping tests in LLM-generated YAML.
"""

from __future__ import annotations

from collections import OrderedDict
from typing import Any, Dict, List

__all__ = ["canonise_model"]


def _as_list(v: Any) -> list:
    return v if isinstance(v, list) else [v]


_ALIAS_MAP: dict[str, tuple[str, callable[[Any], dict]]] = {
    # equality → accepted_values
    "equal": ("accepted_values", lambda v: {"values": _as_list(v)}),
    "equals": ("accepted_values", lambda v: {"values": _as_list(v)}),
    # positive numbers
    "check_positive": ("dbt_utils.expect_column_values_to_be_positive", lambda v: {}),
    "expect_positive": ("dbt_utils.expect_column_values_to_be_positive", lambda v: {}),
    # between variations
    "check_between": (
        "dbt_utils.expect_column_values_to_be_between",
        lambda v: {"min_value": v[0] if isinstance(v, list) else v.get("min"),
                   "max_value": v[1] if isinstance(v, list) else v.get("max")},
    ),
    "expect_between": (
        "dbt_utils.expect_column_values_to_be_between",
        lambda v: {"min_value": v.get("min"), "max_value": v.get("max")},
    ),
    "between": (
        "dbt_utils.accepted_range",
        lambda v: {"min_value": v.get("from"), "max_value": v.get("to")},
    ),
    # regex
    "regex_match": ("dbt_utils.expect_column_to_match_regex",
                    lambda v: {"regex": v if isinstance(v, str) else v.get("pattern")}),
    "match_regex": ("dbt_utils.expect_column_to_match_regex",
                    lambda v: {"regex": v}),
}

_UNWANTED = {"version", "schema_version", "model"}
_KEY_ORDER = ["name", "description", "columns", "tags",
              "refs", "tests", "config"]


def _fix_tests(tests: list[Any]) -> list[Any]:
    """Rewrite LLM aliases to canonical dbt/dbt_utils tests."""
    fixed = []
    for t in tests:
        if isinstance(t, dict) and len(t) == 1:
            alias, val = next(iter(t.items()))
            canon = _ALIAS_MAP.get(alias.lower())
            if canon:
                name, transform = canon
                fixed.append({name: transform(val)})
                continue
        fixed.append(t)
    return fixed


def canonise_model(raw: Dict[str, Any],
                   fallback_name: str,
                   *,
                   strip_tests: bool = False) -> Dict[str, Any]:
    """
    * inject missing `name`
    * normalise refs & tests
    * optionally remove all tests
    * order keys
    """
    m = dict(raw)
    m["name"] = m.get("name") or fallback_name

    # single ref → list
    if "ref" in m:
        m["refs"] = m.get("refs", []) + [m.pop("ref")]
    if isinstance(m.get("refs"), str):
        m["refs"] = [m["refs"]]

    if strip_tests:
        m.pop("tests", None)
        for col in m.get("columns", []):
            col.pop("tests", None)
    else:
        # normalise tests
        if isinstance(m.get("tests"), list):
            m["tests"] = _fix_tests(m["tests"])
        for col in m.get("columns", []):
            if isinstance(col, dict) and isinstance(col.get("tests"), list):
                col["tests"] = _fix_tests(col["tests"])

    # drop unwanted keys
    for k in list(m):
        if k in _UNWANTED:
            m.pop(k)

    # canonical order
    ordered = OrderedDict()
    for k in _KEY_ORDER:
        if k in m:
            ordered[k] = m.pop(k)
    ordered.update(m)
    return ordered
