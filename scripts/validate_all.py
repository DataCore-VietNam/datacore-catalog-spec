#!/usr/bin/env python3
"""Validate every *.yaml file under examples/. Used in CI.

Exits non-zero if any file fails validation.
"""

from __future__ import annotations

import sys
from pathlib import Path

from validate import validate

REPO_ROOT = Path(__file__).resolve().parent.parent
EXAMPLES_DIR = REPO_ROOT / "examples"


def main() -> int:
    if not EXAMPLES_DIR.exists():
        print(f"No examples/ directory at {EXAMPLES_DIR}", file=sys.stderr)
        return 1

    yaml_files = sorted(EXAMPLES_DIR.rglob("*.yaml")) + sorted(EXAMPLES_DIR.rglob("*.yml"))
    if not yaml_files:
        print("No YAML files found under examples/", file=sys.stderr)
        return 1

    rc = 0
    failed = 0
    for path in yaml_files:
        result = validate(path)
        rc |= result
        if result != 0:
            failed += 1

    total = len(yaml_files)
    passed = total - failed
    print()
    print(f"Validated {total} file(s): {passed} passed, {failed} failed")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
