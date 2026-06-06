#!/usr/bin/env python3
"""Validate a YAML file against a DataCore catalog schema.

The schema is auto-detected from the file's location under examples/:
  - examples/domains/  -> domain.schema.json
  - examples/products/ -> product.schema.json
  - examples/          -> dataset.schema.json

You can override detection with --type {dataset,domain,product,column}.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

SCHEMA_DIR = Path(__file__).resolve().parent.parent / "schema"

SCHEMA_FILES = {
    "dataset": "dataset.schema.json",
    "domain": "domain.schema.json",
    "product": "product.schema.json",
    "column": "column.schema.json",
}


def detect_type(yaml_path: Path) -> str:
    """Detect schema type from the file's parent directory name."""
    parts = {p.name for p in yaml_path.resolve().parents}
    if "domains" in parts:
        return "domain"
    if "products" in parts:
        return "product"
    if "columns" in parts:
        return "column"
    return "dataset"


def load_schema(schema_type: str) -> dict:
    schema_file = SCHEMA_FILES.get(schema_type)
    if not schema_file:
        raise ValueError(f"Unknown schema type: {schema_type}")
    with (SCHEMA_DIR / schema_file).open() as f:
        return json.load(f)


def validate(yaml_path: Path, schema_type: str | None = None) -> int:
    if schema_type is None:
        schema_type = detect_type(yaml_path)

    with yaml_path.open() as f:
        data = yaml.safe_load(f)

    schema = load_schema(schema_type)
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(data), key=lambda e: list(e.path))

    if not errors:
        print(f"OK    [{schema_type}] {yaml_path}")
        return 0

    print(f"FAIL  [{schema_type}] {yaml_path}")
    for err in errors:
        loc = ".".join(str(p) for p in err.absolute_path) or "(root)"
        print(f"  - {loc}: {err.message}")
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", help="YAML file(s) to validate")
    parser.add_argument(
        "--type",
        choices=sorted(SCHEMA_FILES.keys()),
        default=None,
        help="Override schema detection; pick one of dataset/domain/product/column",
    )
    args = parser.parse_args()

    rc = 0
    for arg in args.paths:
        rc |= validate(Path(arg), schema_type=args.type)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
