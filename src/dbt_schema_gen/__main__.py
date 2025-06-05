"""Allow `python -m dbt_schema_gen`."""
from .cli import cli

if __name__ == "__main__":  # pragma: no cover
    cli()
