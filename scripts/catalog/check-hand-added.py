#!/usr/bin/env python3
"""Check `seeds/hand-added.json` — door 3's per-host who/when/why.

    python3 scripts/catalog/check-hand-added.py

Every host a person added by hand should say who added it, when, and why; this
file is that record, and a record missing any of the three is exactly the gap it
exists to close. The rules live in `catalog-core.validate_hand_added` so the same
contract holds whether this script, the build, or the tests ask the question.
Exits non-zero on any problem, so `check-docs-fresh.mjs` and `test/test.sh` can
run it directly.
"""
import json
import os
import sys
import importlib.util

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HAND_ADDED = os.path.join(ROOT, "seeds", "hand-added.json")
CATEGORIES = os.path.join(ROOT, "seeds", "categories.json")

_spec = importlib.util.spec_from_file_location(
    "catalog_core", os.path.join(ROOT, "scripts", "catalog", "catalog-core.py")
)
catalog_core = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(catalog_core)


def main():
    try:
        with open(HAND_ADDED, encoding="utf-8") as handle:
            doc = json.load(handle)
    except (OSError, ValueError) as error:
        print(f"✗ cannot read {HAND_ADDED}: {error}", file=sys.stderr)
        return 1

    try:
        with open(CATEGORIES, encoding="utf-8") as handle:
            hosts = set(json.load(handle))
    except (OSError, ValueError) as error:
        print(f"✗ cannot read {CATEGORIES}: {error}", file=sys.stderr)
        return 1

    problems = catalog_core.validate_hand_added(doc, hosts)
    if problems:
        for problem in problems:
            print(f"✗ {problem}", file=sys.stderr)
        print(f"\n{len(problems)} problem(s) in {HAND_ADDED}", file=sys.stderr)
        return 1

    count = len(doc.get("added", {}))
    print(f"✓ {HAND_ADDED}: {count} hand-added host(s), each with by/at/reason")
    return 0


if __name__ == "__main__":
    sys.exit(main())
