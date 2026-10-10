#!/usr/bin/env python3
"""Generate `docs/CATALOG.md` from `catalog.json`.

    python3 scripts/catalog/build-catalog-docs.py

The catalog ships as a binary-ish JSON blob, so a prose summary of it would be
a second copy to keep in step. This writes that copy on purpose, from the same
file the app reads, so the documentation cannot claim a count the shipped data
does not have. Run it after `generate.py` and commit the result.

`docs/NEEDS-REVIEW.md` is written by hand, not by this script — it explains
why a host is unresolved, which needs a person.
"""
import json
import os
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CATALOG = os.path.join(ROOT, "catalog.json")
RULES = os.path.join(ROOT, "rules.json")
OUT = os.path.join(ROOT, "docs", "CATALOG.md")


def other_from_rules():
    """Hosts `rules.json` deliberately files under `other`.

    Read from the rules rather than hardcoded here, so a host cannot drift into
    `other` without the document noticing that it was a decision and not a
    shrug.
    """
    try:
        with open(RULES, encoding="utf-8") as handle:
            rules = json.load(handle)
    except (OSError, ValueError):
        return set()
    return {
        pattern.lower()
        for rule in rules.get("rules", [])
        if rule.get("category") == "other"
        for pattern in rule.get("match", [])
    }

# What a person reads the screen by, not what happens to be common.
ORDER = [
    ("software", "a tool, a platform, a developer utility"),
    ("shopping", "a store, a marketplace, a payment provider"),
    ("video", "streaming, live TV, a broadcaster"),
    ("finance", "banks, cards, trading, markets"),
    ("news", "press, and the reporting it depends on"),
    ("health", "hospitals, pharmacies, health apps"),
    ("ai", "model providers and the products built on them"),
    ("ads", "ad networks, affiliate platforms, retargeting"),
    ("government", "ministries, municipalities, agencies"),
    ("cdn", "delivery networks carrying somebody else's bytes"),
    ("social", "where people talk to each other"),
    ("travel", "airlines, booking, ground transport"),
    ("gaming", "stores, launchers, and the games"),
    ("transport", "shipping, driving, ride and rail"),
    ("encyclopedia", "reference, metadata, documentation"),
    ("education", "schools, universities, courses"),
    ("analytics", "measurement, crash reporting, experimentation"),
    ("search", "search engines and search portals"),
    ("messaging", "chat, mail, messaging"),
    ("email", "mailbox providers"),
    ("telecom", "carriers and network operators"),
    ("other", "deliberately a last resort, not a fallback"),
    ("crash", "crash and error reporting"),
    ("crypto", "exchanges, wallets, chains"),
    ("music", "streaming and audio"),
    ("sports", "leagues, scores, fixtures"),
    ("maps", "map tiles and geocoding"),
]


def main(argv):
    try:
        with open(CATALOG, encoding="utf-8") as handle:
            doc = json.load(handle)
    except (OSError, ValueError) as error:
        print(f"✗ cannot read {CATALOG}: {error}", file=sys.stderr)
        return 1

    categories = doc.get("categories") or {}
    services = doc.get("services") or []
    counts = Counter(categories.values())

    missing = [name for name, _ in ORDER if name not in counts]
    if missing:
        print(f"✗ categories in the catalog but not in ORDER: {', '.join(sorted(missing))}", file=sys.stderr)
        print("  add them, or this document under-reports the shipped data.", file=sys.stderr)
        return 1
    unknown = sorted(set(counts) - {name for name, _ in ORDER})
    if unknown:
        print(f"✗ ORDER lists categories the catalog does not use: {', '.join(unknown)}", file=sys.stderr)
        return 1

    used = [(name, note) for name, note in ORDER if counts[name]]
    total = len(categories)

    lines = []
    add = lines.append
    add("# Catalog")
    add("")
    add("Generated from `catalog.json` by `scripts/catalog/build-catalog-docs.py`. **Do not")
    add("edit by hand** — edit `seeds/` and regenerate, or this file and the shipped")
    add("data will disagree, which is the one thing a data file must never do.")
    add("")
    add("## Totals")
    add("")
    add(f"**{total:,} names** across **{len(used)} categories**, plus **{len(services)} services**.")
    add("")
    add("The app loads `catalog.json` as a Category Data source and matches a host")
    add("whole, so `facebook.com` covers `graph.facebook.com` without listing it.")
    add("")
    add("## By category")
    add("")
    add("| Category | Hosts | What it means |")
    add("| :--- | --: | :--- |")
    for name, note in used:
        add(f"| `{name}` | {counts[name]} | {note} |")
    add("")
    add("### `other` is a decision")
    add("")
    others = sorted(h for h, c in categories.items() if c == "other")
    ruled = other_from_rules()
    shorteners = [h for h in others if h in ruled]
    add(f"{len(others)} host{'s' if len(others) != 1 else ''} sit in `other`: "
        f"{len(shorteners)} URL shorteners and {len(others) - len(shorteners)} curated by hand.")
    add("")
    if shorteners:
        add("The shorteners are " + ", ".join(f"`{h}`" for h in shorteners) + ".")
        add("A shortener is not a thing a person uses on purpose, so there is no honest")
        add("category for it.")
        add("")
    rest = [h for h in others if h not in ruled]
    if rest:
        add("The remainder were labelled `other` by hand — " + ", ".join(f"`{h}`" for h in rest) + ".")
        add("")
    add("`harvest.py` will not write `other` on its own. Only a rule in `rules.json`")
    add("may, because `other` has to be a decision rather than a shrug.")
    add("")
    add("## By service")
    add("")
    add(f"{len(services)} products, one entry each in `seeds/services.json`:")
    add("")
    add("| Service | Domains |")
    add("| :--- | --: |")
    for service in services:
        add(f"| {service.get('name', '?')} (`{service.get('key', '?')}`) | {len(service.get('domains', []))} |")
    add("")
    add("One entry per **product**, not per company — Facebook, Instagram, WhatsApp")
    add("and Threads are separate on purpose, because a DNS filter sees domains, not")
    add("apps, and a product is what a person recognises.")
    add("")
    add("## Where a name came from")
    add("")
    add("| Source | Licence | What it means |")
    add("| :--- | :--- | :--- |")
    add("| the seeds, curated here | CC0 | a person decided this label |")
    add("| `anudeepND` (3 lists) | MIT | hosts commonly caught by overzealous blocklists, used only to *find* hosts that are missing |")
    add("")
    add("Every source, and every source refused, is in [`SOURCES.md`](SOURCES.md).")
    add("External sources propose hosts; **no source assigns a category**. A category")
    add("is either a rule in `rules.json` or a person with a reason.")
    add("")
    add("Hosts still missing a label are in [`NEEDS-REVIEW.md`](NEEDS-REVIEW.md).")

    with open(OUT, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")
    print(f"✓ wrote docs/CATALOG.md: {total} names, {len(used)} categories, {len(services)} services")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))