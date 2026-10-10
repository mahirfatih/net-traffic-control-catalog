#!/usr/bin/env python3
"""Apply harvested categories to `seeds/categories.json`.

    python3 scripts/sources/merge.py evidence/harvested-categories.json
    python3 scripts/sources/merge.py evidence/harvested-categories.json --dry-run

Two things this will not do, because both would hide a decision:

- **Change an existing label.** A host already in the seeds was labelled by
  somebody on purpose. A disagreement is reported and left for a human; the
  script has no standing to overrule it.
- **Invent a category.** Anything outside the vocabulary stops the run, the
  same way a bad seed stops `generate.py`.

Hosts are added, the file is written back sorted, and the count is printed so
a diff that suddenly drops two hundred rows is noticed immediately.
"""
import argparse
import json
import importlib.util
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# The module is named with a hyphen to match the other files here, which Python
# cannot use in an `import` statement. It is loaded by path instead.
_spec = importlib.util.spec_from_file_location(
    "catalog_core", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "catalog", "catalog-core.py")
)
catalog_core = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(catalog_core)

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SEED = os.path.join(ROOT, "seeds", "categories.json")


def main(argv):
    parser = argparse.ArgumentParser(description="Merge harvested categories into the seeds.")
    parser.add_argument("infile", help="JSON {host: category}, from harvest.py")
    parser.add_argument("--dry-run", action="store_true", help="print, do not write")
    args = parser.parse_args(argv[1:])

    path = args.infile if os.path.isabs(args.infile) else os.path.join(ROOT, args.infile)
    try:
        harvested = catalog_core.load(path)
        seeds = catalog_core.load(SEED)
    except (OSError, ValueError) as error:
        print(f"✗ cannot read: {error}", file=sys.stderr)
        return 1

    if not isinstance(harvested, dict) or not isinstance(seeds, dict):
        print("✗ both files must be JSON objects {host: category}", file=sys.stderr)
        return 1

    unknown = sorted({c for c in harvested.values() if c not in catalog_core.VOCABULARY})
    if unknown:
        print(f"✗ category outside the vocabulary: {', '.join(unknown)}", file=sys.stderr)
        print("  fix rules.json — the app ignores names it does not know, so this would", file=sys.stderr)
        print("  ship a label that silently does nothing on device.", file=sys.stderr)
        return 1

    added, conflicts = {}, []
    for host, category in sorted(harvested.items()):
        host = host.strip().lower()
        if host in seeds:
            if seeds[host] != category:
                conflicts.append((host, seeds[host], category))
            continue
        added[host] = category

    for host, existing, proposed in conflicts:
        print(f"! {host}: seed says {existing!r}, harvest says {proposed!r} — seed kept")

    if not added:
        print("nothing to add")
        return 0

    merged = dict(seeds)
    merged.update(added)
    ordered = {host: merged[host] for host in sorted(merged)}

    print(f"\n{len(added)} host(s) to add, {len(conflicts)} conflict(s), "
          f"{len(seeds)} → {len(ordered)} total")

    if args.dry_run:
        for host in sorted(added):
            print(f"  + {host} → {added[host]}")
        print("\ndry run: nothing written")
        return 0

    # The seed is a bare {host: category} map, not a catalog document, so it is
    # checked directly rather than through `validate()`. Writing goes through
    # `json.dump` for the same reason: `catalog_core.write()` normalises a whole
    # document and would wrap the seed in version/generated/categories keys.
    problems = []
    for host, category in ordered.items():
        if host != host.lower():
            problems.append(f"{host!r} is not lowercase")
        if category not in catalog_core.VOCABULARY:
            problems.append(f"category {category!r} for {host!r} is not in the vocabulary")
        if list(ordered) != sorted(ordered):
            problems.append("hosts are not sorted")
            break
    if not ordered:
        problems.append("refusing to write an empty seed")
    if problems:
        for problem in problems:
            print(f"✗ {problem}", file=sys.stderr)
        print("\nrefusing to write; fix the input first", file=sys.stderr)
        return 1

    with open(SEED, "w", encoding="utf-8") as handle:
        json.dump(ordered, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(f"✓ wrote seeds/categories.json: {len(ordered)} categories")
    print("  next: python3 scripts/catalog/generate.py --categories seeds/categories.json \\")
    print("          --services seeds/services.json --out catalog.json && python3 scripts/catalog/validate.py")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))