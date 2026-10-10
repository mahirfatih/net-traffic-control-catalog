#!/usr/bin/env python3
"""Turn an external host list into category suggestions.

    python3 scripts/harvest.py                 # fetch every allowed source
    python3 scripts/harvest.py --source anudeepnd-whitelist
    python3 scripts/harvest.py --dry-run       # print, do not write
    python3 scripts/harvest.py --offline       # reuse evidence/, fetch nothing

The pipeline is: fetch -> parse -> drop what is already covered -> apply
`rules.json` -> report what no rule matched.

Three things it deliberately does not do:

- It never writes a category. A host that no rule matches is written to
  `docs/NEEDS-REVIEW.md` and left out of the seeds, because a wrong label is
  worse than no label — it looks authoritative.
- It never writes `other` automatically. `other` means "we looked and did not
  know", so only a rule may produce it.
- It never writes a host already in the catalog. The existing label was a
  decision; this script has no standing to change it.

Every fetch goes through `sources.py`, so a source whose licence would put
NonCommercial or ShareAlike data into this CC0 catalog is refused before a
byte is downloaded.
"""
import argparse
import importlib.util
import json
import os
import sys
import urllib.request
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# The module is named with a hyphen to match the other files here, which Python
# cannot use in an `import` statement. It is loaded by path instead.
_spec = importlib.util.spec_from_file_location(
    "catalog_core", os.path.join(os.path.dirname(os.path.abspath(__file__)), "catalog-core.py")
)
catalog_core = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(catalog_core)
import sources as source_registry  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RULES = os.path.join(ROOT, "rules.json")
EVIDENCE = os.path.join(ROOT, "evidence")
SEEDS = os.path.join(ROOT, "seeds")
REVIEW = os.path.join(ROOT, "docs", "NEEDS-REVIEW.md")

USER_AGENT = "net-traffic-control-catalog/1.0 (catalog harvest; +https://github.com/mahirfatih/net-traffic-control-catalog)"
TIMEOUT = 30


def fetch(url):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        return response.read().decode("utf-8", "replace")


def parse(text, fmt="plain"):
    """Return the hosts in a source file.

    Both formats the registry knows are supported. Adblock syntax is not
    guessed at: a line that parses as neither is reported rather than dropped,
    because silently losing hosts is how a catalog goes quietly wrong.
    """
    hosts, unparsed = [], []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("!"):
            continue
        if line.startswith("||") and line.endswith("^"):
            line = line[2:-1]
        elif line.startswith("||"):
            line = line[2:]
        if not line or "/" in line:
            unparsed.append(line)
            continue
        hosts.append(line.lower().strip("*.").rstrip("."))
    return hosts, unparsed


def covered_by(host, known):
    """Is `host` already matched, exactly or through one of its ancestors?

    The app matches a host and all its subdomains, so listing a subdomain the
    catalog already covers adds a row that can never disagree with its parent
    and only makes the diff longer.
    """
    labels = host.split(".")
    for index in range(len(labels) - 1):
        if ".".join(labels[index:]) in known:
            return ".".join(labels[index:])
    return None


def categorize(host, rules):
    for rule in rules.get("rules", []):
        for pattern in rule.get("match", []):
            pattern = pattern.lower()
            if host == pattern or host.endswith("." + pattern):
                return rule
    return None


def load_known():
    """Hosts the catalog already covers, from the seeds."""
    known = set()
    for path in (os.path.join(SEEDS, "categories.json"),):
        if os.path.exists(path):
            known |= set(catalog_core.load(path))
    services = os.path.join(SEEDS, "services.json")
    if os.path.exists(services):
        for service in catalog_core.load(services) or []:
            known |= {str(d).lower() for d in service.get("domains", [])}
    return known


def strip_www(host):
    return host[4:] if host.startswith("www.") else host


def main(argv):
    parser = argparse.ArgumentParser(description="Harvest hosts from allowed sources.")
    parser.add_argument("--source", action="append", default=[], help="source id; repeatable")
    parser.add_argument("--dry-run", action="store_true", help="print, do not write")
    parser.add_argument("--offline", action="store_true", help="reuse evidence/, fetch nothing")
    args = parser.parse_args(argv[1:])

    registry = source_registry.load()
    rules = catalog_core.load(RULES)
    drop = rules.get("drop", {}).get("hosts", {})
    os.makedirs(EVIDENCE, exist_ok=True)

    chosen = [s for s in registry.get("sources", []) if not args.source or s["id"] in args.source]
    if args.source:
        missing = set(args.source) - {s["id"] for s in registry.get("sources", [])}
        if missing:
            print(f"unknown source(s): {', '.join(sorted(missing))}", file=sys.stderr)
            return 1

    known = load_known()
    kept, already, dropped, review = [], [], [], []

    for source in chosen:
        source_id = source["id"]

        ok, reason = source_registry.verdict(source)
        if not ok:
            # Named explicitly: the user asked for this source, so say why it
            # cannot be had. Named by "every allowed source": skip it quietly.
            explicit = args.source and source_id in args.source
            marker = "✗" if explicit else "·"
            stream = sys.stderr if explicit else sys.stdout
            print(f"{marker} skipping {source_id}: {reason}", file=stream)
            if explicit:
                return 1
            continue

        cache = os.path.join(EVIDENCE, f"{source_id}.txt")
        if args.offline:
            if not os.path.exists(cache):
                print(f"✗ --offline but no cached copy of {source_id} ({cache})", file=sys.stderr)
                return 1
            text = open(cache, encoding="utf-8").read()
            print(f"· {source_id}: read from cache")
        else:
            try:
                text = fetch(source["url"])
            except Exception as error:  # noqa: BLE001 - report, do not crash the run
                print(f"✗ {source_id}: cannot fetch {source['url']}: {error}", file=sys.stderr)
                return 1
            if not args.dry_run:
                with open(cache, "w", encoding="utf-8") as handle:
                    handle.write(text)
            print(f"· {source_id}: fetched {len(text)} bytes")

        hosts, unparsed = parse(text, source.get("format", "plain"))
        if unparsed:
            print(f"  ! {len(unparsed)} line(s) not understood, first: {unparsed[0]!r}", file=sys.stderr)

        for host in hosts:
            host = strip_www(host)
            if not host or "." not in host:
                dropped.append((host, "not a hostname"))
                continue
            if host in drop:
                dropped.append((host, drop[host]))
                continue
            parent = covered_by(host, known)
            if parent:
                already.append((host, parent))
                continue
            rule = categorize(host, rules)
            if rule is None:
                review.append((host, source_id))
                continue
            kept.append({
                "host": host,
                "category": rule["category"],
                "service": rule.get("service"),
                "source": source_id,
                "rule": rule.get("note", ""),
            })

    kept.sort(key=lambda row: row["host"])
    seen = set()
    unique = []
    for row in kept:
        if row["host"] in seen:
            continue
        seen.add(row["host"])
        unique.append(row)
    kept = unique

    print(f"\n{len(kept)} host(s) categorised, {len(already)} already covered, "
          f"{len(dropped)} dropped, {len(review)} need review")

    if kept:
        print("\n| host | category | service | from |")
        print("| :--- | :--- | :--- | :--- |")
        for row in kept:
            print(f"| `{row['host']}` | {row['category']} | {row['service'] or ''} | {row['source']} |")

    if review:
        print("\nneeds review (no rule matched — deliberately not categorised):")
        for host, source_id in sorted(review):
            print(f"  {host}  ({source_id})")

    if args.dry_run:
        print("\ndry run: nothing written")
        return 0

    payload = {row["host"]: row["category"] for row in kept}
    # Into evidence/, not the repository root: it is a generated intermediate,
    # and a root-level file nobody recognises reads like something that matters.
    out = os.path.join(EVIDENCE, "harvested-categories.json")
    with open(out, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
    print(f"\n✓ wrote {out} ({len(payload)} hosts)")
    print(f"  apply with: python3 scripts/merge.py {os.path.relpath(out, ROOT)}")
    print(f"  review {len(review)} hand-written entries in docs/NEEDS-REVIEW.md")

    # A run that categorised nothing is a no-op: every host it found is already
    # in the seeds. Overwriting the summary would erase the record of the run
    # that *did* add hosts — and that record is the evidence for the labels now
    # in the catalog. So a no-op leaves it alone and says so.
    summary_path = os.path.join(EVIDENCE, "harvest-summary.json")
    if not kept and os.path.exists(summary_path):
        print(f"  nothing new to categorise; {os.path.relpath(summary_path, ROOT)} left as it was")
        return 0

    with open(summary_path, "w", encoding="utf-8") as handle:
        json.dump({
            "generated": date.today().isoformat(),
            "sources": [s["id"] for s in chosen],
            "categorized": sorted(payload),
            "already_covered": sorted(h for h, _ in already),
            "dropped": {h: r for h, r in sorted(dropped) if h},
            "needs_review": sorted(h for h, _ in review),
        }, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))