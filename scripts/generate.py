#!/usr/bin/env python3
"""Build `catalog.json` from seed files.

    python3 scripts/generate.py \
        --categories seeds/categories.json \
        --services   seeds/services.json \
        --out        catalog.json

- `--categories` is a JSON object `{ "host": "category" }`.
- `--services`   is a JSON array `[ { "key", "name", "domains": [...] } ]`.

The seeds are the source of truth; `catalog.json` is the build output. Output is
deterministic (hosts sorted, services sorted by key, fixed indent) so diffs stay
reviewable. Everything is validated **before** writing: a bad seed writes nothing,
so there is never a half-written catalog.
"""
import argparse
import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import catalog_lib  # noqa: E402


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--categories", required=True, help="JSON {host: category}")
    parser.add_argument("--services", required=True, help="JSON [{key,name,domains}]")
    parser.add_argument("--out", default="catalog.json", help="output path")
    args = parser.parse_args(argv[1:])

    try:
        categories = catalog_lib.load(args.categories)
        services = catalog_lib.load(args.services)
    except (OSError, ValueError) as error:
        print(f"✗ cannot read a seed: {error}", file=sys.stderr)
        return 1
    if not isinstance(categories, dict):
        print("✗ --categories must be an object {host: category}", file=sys.stderr)
        return 1
    if not isinstance(services, list):
        print("✗ --services must be an array", file=sys.stderr)
        return 1

    document = catalog_lib.normalize({
        "version": 1,
        "generated": datetime.date.today().isoformat(),
        "categories": categories,
        "services": services,
    })

    problems = catalog_lib.validate(document)
    if problems:
        for problem in problems:
            print(f"✗ {problem}", file=sys.stderr)
        print("\nrefusing to write; fix the seeds first", file=sys.stderr)
        return 1

    catalog_lib.write(document, args.out)
    print(
        f"✓ wrote {args.out}: {len(document['categories'])} categories, "
        f"{len(document['services'])} services"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
