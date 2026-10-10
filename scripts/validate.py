#!/usr/bin/env python3
"""Validate `catalog.json` (or a path given as the first argument).

    python3 scripts/validate.py
    python3 scripts/validate.py other.json

Checks the format and the category vocabulary and prints a summary. Exits
non-zero on any problem, so it works in CI or a pre-commit hook.
"""
import os
import importlib.util
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# The module is named with a hyphen to match the other files here, which Python
# cannot use in an `import` statement. It is loaded by path instead.
_spec = importlib.util.spec_from_file_location(
    "catalog_core", os.path.join(os.path.dirname(os.path.abspath(__file__)), "catalog-core.py")
)
catalog_core = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(catalog_core)

DEFAULT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "catalog.json"
)


def main(argv):
    path = argv[1] if len(argv) > 1 else DEFAULT
    try:
        doc = catalog_core.load(path)
    except (OSError, ValueError) as error:
        print(f"✗ cannot read {path}: {error}", file=sys.stderr)
        return 1

    problems = catalog_core.validate(doc)
    if problems:
        for problem in problems:
            print(f"✗ {problem}", file=sys.stderr)
        print(f"\n{len(problems)} problem(s) in {path}", file=sys.stderr)
        return 1

    print(
        f"✓ {path}: {len(doc.get('categories', {}))} categories, "
        f"{len(doc.get('services', []))} services"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
