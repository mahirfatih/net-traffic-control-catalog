#!/usr/bin/env python3
"""Check for redundant subdomains, tenant-suffix misuse and category distribution.

    python3 scripts/catalog/check-overlaps.py

- Warns about subdomains that have the exact same category as their ancestor
  (since prefix matching already covers them).
- Reports deliberate category overrides (subdomain with a different category than ancestor).
- Prints category distribution statistics.
- **Fails** on the two rules docs/FORMAT.md states and nothing else enforced:
  a bare multi-tenant suffix listed without a reasoned exception
  (``seeds/public-suffix-exceptions.json``), and a domain claimed by two
  services. Both swallow or mislabel every tenant/claimant beneath them, which
  is exactly what the longest-suffix rule cannot recover from.
"""
import json
import os
import sys
import importlib.util
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CATEGORIES_PATH = os.path.join(ROOT, "seeds", "categories.json")
SERVICES_PATH = os.path.join(ROOT, "seeds", "services.json")
EXCEPTIONS_PATH = os.path.join(ROOT, "seeds", "public-suffix-exceptions.json")
RULES = os.path.join(ROOT, "rules.json")

# A bare multi-tenant suffix swallows every tenant beneath it — `github.io`
# also covers `someone.github.io`. Listing one is therefore a deliberate choice,
# not a default, and each such listing must carry a reason in
# seeds/public-suffix-exceptions.json. This is the list the check is built
# against; add a suffix here when it is recognised as multi-tenant.
MULTI_TENANT_SUFFIXES = (
    "co.uk", "github.io", "gitlab.io", "bitbucket.io", "blogspot.com",
    "wordpress.com", "tumblr.com", "wixsite.com", "notion.site",
    "amazonaws.com", "cloudfront.net", "azurewebsites.net", "appspot.com",
    "firebaseapp.com", "web.app", "herokuapp.com", "netlify.app", "vercel.app",
    "pages.dev", "onrender.com", "fly.dev", "glitch.me", "surge.sh",
    "readthedocs.io", "sourceforge.net",
)

_overrides_spec = importlib.util.spec_from_file_location(
    "overrides", os.path.join(ROOT, "scripts", "catalog", "overrides.py")
)
overrides_module = importlib.util.module_from_spec(_overrides_spec)
_overrides_spec.loader.exec_module(overrides_module)


def load_suffix_exceptions(path=EXCEPTIONS_PATH):
    """The ``host -> reason`` map of allowed multi-tenant suffix listings.

    A key beginning with ``_`` is a comment. An entry with an empty reason is
    treated as absent, so the reason cannot be skipped by adding a bare key.
    """
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as handle:
        doc = json.load(handle)
    return {h: v for h, v in doc.items() if not h.startswith("_")}


def suffix_conflicts(categories, services, exceptions, suffixes=MULTI_TENANT_SUFFIXES):
    """Multi-tenant suffixes that are listed without a reasoned exception.

    Returns ``(unexcused, stale, used)``: the listings with no reason, the
    exception entries that no longer match anything, and every suffix actually
    used. Pure, so the self-test can exercise it without the real catalog.
    """
    used = {h for h in categories if h in suffixes}
    for service in services:
        for domain in service.get("domains", ()):
            if domain in suffixes:
                used.add(domain)
    unexcused = sorted(h for h in used if not str(exceptions.get(h) or "").strip())
    stale = sorted(h for h in exceptions if h not in used)
    return unexcused, stale, sorted(used)


def service_conflicts(services):
    """``(clashes, duplicate_keys)`` for the services document.

    ``clashes`` maps a domain claimed by more than one service to those keys;
    ``duplicate_keys`` lists a service key that appears twice.
    """
    domain_to_keys = defaultdict(list)
    for service in services:
        for domain in service.get("domains", ()):
            domain_to_keys[domain].append(service.get("key", ""))
    clashes = {d: sorted(ks) for d, ks in sorted(domain_to_keys.items()) if len(ks) > 1}
    counts = Counter(s.get("key", "") for s in services)
    duplicate_keys = sorted(k for k, n in counts.items() if n > 1)
    return clashes, duplicate_keys


def main():
    if not os.path.exists(CATEGORIES_PATH):
        print(f"✗ error: {CATEGORIES_PATH} not found", file=sys.stderr)
        return 1

    with open(CATEGORIES_PATH, encoding="utf-8") as f:
        categories = json.load(f)
    with open(SERVICES_PATH, encoding="utf-8") as f:
        services = json.load(f)

    try:
        manual = overrides_module.overrides(overrides_module.load_rules(RULES))
    except (OSError, ValueError):
        manual = {}

    exceptions = load_suffix_exceptions()
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

    print(f"\n--- Manual Overrides in rules.json ({len(manual)}) ---")
    if manual:
        for h, (cat, _reason) in sorted(manual.items()):
            print(f"  {h} -> {cat}")
    else:
        print("  None found.")

    print(f"\n--- Redundant Subdomains with Same Category ({len(redundant)}) ---")
    if redundant:
        for h, parent, cat in redundant[:20]:
            print(f"  {h} -> covered by parent {parent} ({cat})")
        if len(redundant) > 20:
            print(f"  ... and {len(redundant) - 20} more.")
    else:
        print("  None found.")

    problems = 0

    unexcused, stale, used = suffix_conflicts(categories, services, exceptions)
    print(f"\n--- Multi-tenant suffixes listed ({len(used)}) ---")
    for h in used:
        reason = str(exceptions.get(h) or "").strip()
        print(f"  {h} [{'✓ ' + reason if reason else '✗ no reason'}]")
    if unexcused:
        problems += len(unexcused)
        print(f"  ✗ {len(unexcused)} listing(s) without an exception+reason in "
              f"{os.path.relpath(EXCEPTIONS_PATH, ROOT)}")
    if stale:
        print(f"  · {len(stale)} stale exception entry(ies): {', '.join(stale)}")

    clashes, duplicate_keys = service_conflicts(services)
    print(f"\n--- Service-domain clashes ({len(clashes)}) ---")
    for domain, keys in clashes.items():
        problems += 1
        print(f"  ✗ {domain} claimed by {', '.join(keys)}")
    if duplicate_keys:
        problems += len(duplicate_keys)
        for key in duplicate_keys:
            print(f"  ✗ duplicate service key: {key}")
    if not clashes and not duplicate_keys:
        print("  None found.")

    if problems:
        print(f"\n✗ {problems} problem(s) — see docs/FORMAT.md, 'Matching'.")
        return 1

    print(f"\n✓ Overlap and distribution check completed successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
