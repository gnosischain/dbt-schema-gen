from pathlib import Path
from typing import Iterable


def find_models_root(path: Path) -> Path:
    """
    Return the absolute **models/** folder for this run.

    * If <path>/models exists → user gave project root.
    * Else climb upwards until you hit a directory literally named 'models'.
    """
    p = path.resolve()
    if (p / "models").is_dir():
        return p / "models"

    for parent in [p, *p.parents]:
        if parent.name == "models":
            return parent

    raise FileNotFoundError("Could not locate a 'models/' folder.")


def sql_files(scan_root: Path, selected: set[str] | None) -> Iterable[Path]:
    """Yield *.sql files under *scan_root* honouring `selected` filter."""
    for p in scan_root.rglob("*.sql"):
        if p.name.startswith("_") or p.name.endswith("_tmp.sql"):
            continue
        if selected is None or p.stem in selected:
            yield p
