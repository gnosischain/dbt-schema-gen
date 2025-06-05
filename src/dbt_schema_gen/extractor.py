"""
Utility functions to pull metadata out of dbt SQL models.
Mostly carried over from the original script but split into a module.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Dict, List

import sqlparse

# --- regex patterns -------------------------------------------------------

COMMENT_DESCRIPTION_PATTERN = re.compile(
    r"--\s*@column\s+(?P<col_name>\w+)\s*:\s*(?P<description>.*)$",
    re.IGNORECASE,
)
JINJA_COMMENT_DESCRIPTION_PATTERN = re.compile(
    r"{#\s*@column\s+(?P<col_name>\w+)\s*:\s*(?P<description>.*?)#}",
    re.IGNORECASE | re.DOTALL,
)
REF_PATTERN = re.compile(r"ref\(['\"]([^'\"]+)['\"]\)")


# --- helpers --------------------------------------------------------------

def extract_column_comments(sql_file_path: Path) -> Dict[str, str]:
    """Return ``{column: description}`` discovered from ``-- @column ...``."""
    text = sql_file_path.read_text()
    matches = COMMENT_DESCRIPTION_PATTERN.findall(text) + JINJA_COMMENT_DESCRIPTION_PATTERN.findall(text)
    return {col.strip(): desc.strip() for col, desc in matches}


def extract_references(sql_file_path: Path) -> List[str]:
    """Return list of dbt ``ref()`` targets."""
    return REF_PATTERN.findall(sql_file_path.read_text())


def split_on_top_level_comma(expr: str) -> List[str]:
    """Split a SQL expression on *top-level* commas."""
    out, buf, depth = [], [], 0
    for ch in expr:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        elif ch == "," and depth == 0:
            out.append("".join(buf).strip())
            buf = []
            continue
        buf.append(ch)
    if buf:
        out.append("".join(buf).strip())
    return out


def extract_columns_from_sql(sql_file_path: Path) -> List[str]:
    """Very lightweight select-list parser – good enough for prompts."""
    sql = sql_file_path.read_text()
    columns: set[str] = set()

    for statement in sqlparse.parse(sql):
        for token in statement.tokens:
            if token.ttype is sqlparse.tokens.DML and token.value.upper() == "SELECT":
                match = re.search(r"SELECT\s+(.*?)\s+FROM", str(statement), re.I | re.S)
                if match:
                    for col_expr in split_on_top_level_comma(match.group(1)):
                        col_expr = col_expr.strip()
                        alias = re.search(r"\s+AS\s+([`\"\[\]\w]+)$", col_expr, re.I)
                        name = alias.group(1) if alias else re.split(r"[\s\.]+", col_expr)[-1]
                        name = name.strip(' "\'`[]()')
                        if name and not name.startswith("("):
                            columns.add(name)
    return sorted(columns)


def get_metadata_from_path(path: Path) -> dict:
    """
    Infer sector & tag list from *models/**/* path.

    ``models/execution/some_subfolder/my_model.sql`` →
        ``sector='execution'``, ``tags=['execution','some_subfolder']``
    """
    try:
        idx = path.parts.index("models")
    except ValueError:  # path not under /models – fall back
        idx = 0

    sector = path.parts[idx + 1] if idx + 1 < len(path.parts) else None
    tags = ([sector] if sector else []) + [
        p for p in path.parts[idx + 2 :] if not p.endswith(".sql")
    ]
    return {"sector": sector, "tags": tags}
