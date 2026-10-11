#!/usr/bin/env python3
"""Check for redundant subdomains and analyze category distribution/overrides.

    python3 scripts/catalog/check-overlaps.py

- Warns about subdomains that have the exact same category as their ancestor
  (since prefix matching already covers them).
- Reports deliberate category overrides (subdomain with a different category than ancestor).
- Prints category distribution statistics.
"""
import json
import os
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CATEGORIES_PATH = os.path.join(ROOT, "seeds", "categories.json")


def main():
    if not os.path.exists(CATEGORIES_PATH):
        print(f"✗ error: {CATEGORIES_PATH} not found", file=sys.stderr)
        return 1

    with open(CATEGORIES_PATH, encoding="utf-8") as f:
        categories = json.load(f)

    hosts = sorted(categories.keys())

    redundant = []
    overrides = []

    for h in hosts:
        parts = h.split(".")
        for idx in range(1, len(parts)):
            parent = ".".join(parts[idx:])
            if parent in categories:
                if categories[parent] == categories[h]:
                    redundant.append((h, parent, categories[h]))
                else:
                    overrides.append((h, categories[h], parent, categories[parent]))
                break

    # Category distribution
    counts = Counter(categories.values())

    print(f"=== Catalog Overlap & Distribution Report ===")
    print(f"Total domains: {len(hosts)}")
    print(f"Total categories: {len(counts)}")
    print(f"\n--- Category Distribution ---")
    for cat, cnt in counts.most_common():
        print(f"  {cat}: {cnt}")

    print(f"\n--- Deliberate Overrides ({len(overrides)}) ---")
    for h, c_child, parent, c_parent in overrides:
        print(f"  {h} ({c_child}) overrides parent {parent} ({c_parent})")

    print(f"\n--- Redundant Subdomains with Same Category ({len(redundant)}) ---")
    if redundant:
        for h, parent, cat in redundant[:20]:
            print(f"  {h} -> covered by parent {parent} ({cat})")
        if len(redundant) > 20:
            print(f"  ... and {len(redundant) - 20} more.")
    else:
        print("  None found.")

    print(f"\n✓ Overlap and distribution check completed successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
