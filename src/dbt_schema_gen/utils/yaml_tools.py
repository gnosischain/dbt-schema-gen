from __future__ import annotations

import re
from textwrap import dedent
from collections import OrderedDict
from pathlib import Path
from typing import Any

import yaml

__all__ = ["dump_yaml", "sanitize_yaml"]

_FENCE = re.compile(r"^\s*```(?:yaml)?\s*|\s*```$", re.MULTILINE)
_NEED_QUOTE = re.compile(r"(\s*description:\s*)([^\"'][^#]*?:[^\"'].*)$")


def sanitize_yaml(text: str) -> str:
    """Strip ``` fences and quote colons inside description strings."""
    cleaned = dedent(_FENCE.sub("", text)).strip()
    try:
        yaml.safe_load(cleaned)
        return cleaned
    except yaml.YAMLError:
        pass

    fixed = "\n".join(
        f'{m.group(1)}"{m.group(2).strip()}"' if (m := _NEED_QUOTE.match(line)) else line
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
