#!/usr/bin/env python3
"""Build `catalog.json` from seed files.

    python3 scripts/catalog/generate.py \
        --categories seeds/categories.json \
        --services   seeds/services.json \
        --out        catalog.json

Add `--check` to answer "is the committed file current?" without writing:
the seeds are rebuilt and compared to the file by content, ignoring only the
`generated` date stamp (which is today's date whenever the file is rebuilt).

- `--categories` is a JSON object `{ "host": "category" }`.
- `--services`   is a JSON array `[ { "key", "name", "domains": [...] } ]`.

The seeds are the source of truth; `catalog.json` is the build output. Output is
deterministic (hosts sorted, services sorted by key, fixed indent) so diffs stay
reviewable. Everything is validated **before** writing: a bad seed writes nothing,
so there is never a half-written catalog.
"""
import argparse
import datetime
import importlib.util
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# The module is named with a hyphen to match the other files here, which Python
# cannot use in an `import` statement. It is loaded by path instead.
_spec = importlib.util.spec_from_file_location(
    "catalog_core", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "catalog", "catalog-core.py")
)
catalog_core = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(catalog_core)

_overrides_spec = importlib.util.spec_from_file_location(
    "overrides", os.path.join(os.path.dirname(os.path.abspath(__file__)), "overrides.py")
)
overrides_module = importlib.util.module_from_spec(_overrides_spec)
_overrides_spec.loader.exec_module(overrides_module)

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RULES = os.path.join(ROOT, "rules.json")


def _structure(document):
    """The catalog without its date stamp, for content comparison.

    `generated` is today's date whenever the file is rebuilt, so comparing it
    would make the check fail every day for a reason that is not a change. Every
    other field must match exactly; that is what "the committed file is current"
    means.
    """
    return {key: value for key, value in document.items() if key != "generated"}


def _describe_differences(expected, committed):
    """Human-readable reasons the seeds and the committed file disagree."""
    problems = []
    exp = expected.get("categories") or {}
    act = committed.get("categories") or {}
    added = sorted(set(act) - set(exp))
    removed = sorted(set(exp) - set(act))
    relabelled = sorted(h for h in set(exp) & set(act) if exp[h] != act[h])
    if added:
        problems.append(f"{len(added)} host(s) are in the file but not in the seeds: " + ", ".join(added[:5]))
    if removed:
        problems.append(f"{len(removed)} host(s) are in the seeds but missing from the file: " + ", ".join(removed[:5]))
    if relabelled:
        problems.append(
            f"{len(relabelled)} host(s) are labelled differently: "
            + ", ".join(f"{h} ({exp[h]} → {act[h]})" for h in relabelled[:5])
        )
    if (expected.get("services") or []) != (committed.get("services") or []):
        problems.append("the services differ (a service, its key, or its domains changed)")
    return problems


def check_current(document, path):
    """Compare a freshly built document with the committed one; write nothing."""
    try:
        committed = catalog_core.load(path)
    except (OSError, ValueError) as error:
        print(f"✗ {path} is missing or unreadable: {error}", file=sys.stderr)
        print("  run generate.py to write it.", file=sys.stderr)
        return 1
    if _structure(document) == _structure(committed):
        print(
            f"✓ {path} is current ({len(document['categories'])} categories, "
            f"{len(document['services'])} services)"
        )
        return 0
    for problem in _describe_differences(document, committed):
        print(f"✗ {problem}", file=sys.stderr)
    print(f"\n{path} is stale — rerun generate.py with the same seeds and commit it", file=sys.stderr)
    return 1


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--categories", required=True, help="JSON {host: category}")
    parser.add_argument("--services", required=True, help="JSON [{key,name,domains}]")
    parser.add_argument("--out", default="catalog.json", help="output path")
    parser.add_argument("--rules", default=RULES, help="rules.json holding overrides")
    parser.add_argument(
        "--check", action="store_true",
        help="verify the output file is current; write nothing",
    )
    args = parser.parse_args(argv[1:])

    try:
        categories = catalog_core.load(args.categories)
        services = catalog_core.load(args.services)
    except (OSError, ValueError) as error:
        print(f"✗ cannot read a seed: {error}", file=sys.stderr)
        return 1
    if not isinstance(categories, dict):
        print("✗ --categories must be an object {host: category}", file=sys.stderr)
        return 1
    if not isinstance(services, list):
        print("✗ --services must be an array", file=sys.stderr)
        return 1

    try:
        rules = overrides_module.load_rules(args.rules)
    except (OSError, ValueError) as error:
        print(f"✗ cannot read rules: {error}", file=sys.stderr)
        return 1

    override_problems = overrides_module.check(rules)
    if override_problems:
        for problem in override_problems:
            print(f"✗ {problem}", file=sys.stderr)
        print("\nrefusing to write; fix rules.json drop.override first", file=sys.stderr)
        return 1

    categories, apply_problems = overrides_module.apply(categories, rules)
    if apply_problems:
        for problem in apply_problems:
            print(f"✗ {problem}", file=sys.stderr)
        print("\nrefusing to write; fix rules.json drop.override first", file=sys.stderr)
        return 1

    today = datetime.date.today()
    generated_unix = int(time.mktime(today.timetuple()))
    document = catalog_core.normalize({
        "version": 3,
        "generated": today.isoformat(),
        "generated_unix": generated_unix,
        "categories": categories,
        "services": services,
        "format_version": 3,
        "manifest_version": 2,
        "manifest_file": "manifest.json",
    })

    problems = catalog_core.validate(document)
    if problems:
        for problem in problems:
            print(f"✗ {problem}", file=sys.stderr)
        print("\nrefusing to write; fix the seeds first", file=sys.stderr)
        return 1

    if args.check:
        return check_current(document, args.out)

    catalog_core.write(document, args.out)
    print(
        f"✓ wrote {args.out}: {len(document['categories'])} categories, "
        f"{len(document['services'])} services"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
