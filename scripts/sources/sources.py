#!/usr/bin/env python3
"""The source registry: load `sources.json` and decide what may be read.

Every external list this catalog has ever drawn on is recorded in
`sources.json` with its licence and an `allowed` verdict. The gate lives here
so that a rule is not a thing a contributor has to remember: `harvest.py`
refuses to download a source whose licence would put non-commercial or
share-alike data into a CC0 catalog that ships inside a commercial app.

    python3 scripts/sources/sources.py               # list every source and its verdict
    python3 scripts/sources/sources.py --allowed     # only the ones that may be fetched
    python3 scripts/sources/sources.py --check       # validate the registry itself

The `--check` mode is what CI runs. It is deliberately cheap and offline: a
typo in the registry is a build failure, not a bad download.
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT = os.path.join(ROOT, "config/sources.json")

# Licences that must never reach the shipped catalog, with the reason stated
# once so a contributor sees *why* rather than just a refusal.
#
# These are keyed on the *data* licence only. A proprietary API is a separate
# question — terms differ per provider, and some permit exactly the evidence-
# gathering this repository does — so those records carry their own `reason`
# and their own `allowed` verdict, and no blanket rule is applied here.
BLOCKING = {
    "CC-BY-NC-SA-4.0": "NonCommercial and ShareAlike: a commercial app may not use it, "
                       "and the derivative would stop being CC0.",
    "CC-BY-NC-4.0": "NonCommercial: a commercial app may not use it.",
    "CC-BY-SA-4.0": "ShareAlike: the derivative would inherit the term and stop being CC0.",
}


def load(path=DEFAULT):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def verdict(source):
    """Return `(allowed, reason)` for a source record.

    `allowed` in the registry is a *claim*; this is the check. A record that
    claims `allowed: true` for a blocking licence is an error, not a warning —
    that is exactly the mistake the gate exists to catch.
    """
    licence = str(source.get("license", "")).strip()
    blocked = BLOCKING.get(licence)
    claimed = bool(source.get("allowed"))

    if blocked and claimed:
        return False, f"registry claims allowed but {licence} is blocked: {blocked}"
    if blocked:
        return False, str(source.get("reason") or blocked)
    if not claimed:
        return False, str(source.get("reason") or "marked allowed: false with no reason given")
    return True, ""


def select(registry, only_allowed=False):
    out = []
    for source in registry.get("sources", []):
        ok, reason = verdict(source)
        if only_allowed and not ok:
            continue
        out.append((source, ok, reason))
    return out


def problems(registry):
    """Everything wrong with the registry itself, as a list of strings."""
    found = []
    sources = registry.get("sources")
    if not isinstance(sources, list) or not sources:
        return ["sources is not a non-empty array"]

    seen = set()
    for index, source in enumerate(sources):
        label = source.get("id") or f"sources[{index}]"
        for field in ("id", "name", "url", "license"):
            if not str(source.get(field, "")).strip():
                found.append(f"{label} is missing {field}")
        if source.get("id") in seen:
            found.append(f"duplicate source id {source.get('id')!r}")
        seen.add(source.get("id"))
        if str(source.get("url", "")).startswith("http") and not str(source.get("url")).startswith("https://"):
            found.append(f"{label} url is not https")
        ok, reason = verdict(source)
        if not ok and not reason.strip():
            found.append(f"{label} is not allowed and gives no reason")
    return found


def main(argv):
    path = DEFAULT
    if len(argv) > 1 and not argv[1].startswith("--"):
        path = argv[1]
    only_allowed = "--allowed" in argv

    try:
        registry = load(path)
    except (OSError, ValueError) as error:
        print(f"cannot read {path}: {error}", file=sys.stderr)
        return 1

    if "--check" in argv:
        found = problems(registry)
        if found:
            for problem in found:
                print(f"✗ {problem}", file=sys.stderr)
            print(f"\n{len(found)} problem(s) in {path}", file=sys.stderr)
            return 1
        total = len(registry.get("sources", []))
        allowed = len(select(registry, only_allowed=True))
        print(f"✓ {path}: {total} sources, {allowed} allowed, {total - allowed} blocked")
        return 0

    rows = select(registry, only_allowed=only_allowed)
    if not rows:
        print("no sources matched")
        return 0
    for source, ok, reason in rows:
        mark = "allow" if ok else "BLOCK"
        line = f"{mark:5} {source.get('id', '?'):24} {source.get('license', '?'):16} {source.get('name', '')}"
        print(line)
        if not ok and reason:
            print(f"      {reason}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))