"""
High-level package import.
Exposes the Click CLI as `dbt-schema-gen` when installed with
`pip install -e .` and the entry-point is configured in pyproject/SETUP.
"""
from .cli import cli

__all__ = ["cli"]
__version__ = "0.1.0"
