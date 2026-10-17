#!/usr/bin/env python3
"""Name the source hosts that no rule matched — the review backlog.

    python3 scripts/sources/pending.py            # write evidence/pending-source-hosts.json
    python3 scripts/sources/pending.py --check     # verify it is current, write nothing

`harvest.py` reports the hosts a rule could not match, but only to stdout for the
run that just happened — nothing persists them. A source that contributed
nothing *this* run leaves no trace of the hosts it offered, and the catalog then
looks as if every candidate host was either imported or dismissed, when in fact
thousands were never decided.

This script recomputes the whole backlog offline, from the committed source
caches, applying the same steps `harvest.py` does — parse, strip `www`, drop
`drop.hosts`, drop what the catalog already covers, apply `rules.json`. What is
left is the set of open questions, recorded so the count is on the record rather
than invisible.

The output carries no timestamp: the same inputs must render the same bytes.
"""
import argparse
import importlib.util
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SOURCES = os.path.join(ROOT, "sources.json")
RULES = os.path.join(ROOT, "rules.json")
EVIDENCE = os.path.join(ROOT, "evidence")
OUT = os.path.join(EVIDENCE, "pending-source-hosts.json")


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


harvest = _load("harvest", os.path.join(ROOT, "scripts", "sources", "harvest.py"))


def load_json(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def review_mentions():
    """`[(host, source id), ...]` for every source host no rule matched.

    Same steps and same order as `harvest.py`, read from the committed caches so
    the result does not depend on the network. A host offered by two sources
    appears once per source, exactly as `harvest.py` counts it; the unique-host
    count is derived from the same list.
    """
    registry = load_json(SOURCES)
    rules = load_json(RULES)
    drop = rules.get("drop", {}).get("hosts", {})
    known = harvest.load_known()

    mentions = []
    for source in registry.get("sources", []):
        if not source.get("harvest", True):
            continue
        cache = os.path.join(EVIDENCE, f"{source['id']}.txt")
        if not os.path.exists(cache):
            continue
        with open(cache, encoding="utf-8") as handle:
            text = handle.read()
        hosts, _ = harvest.parse(text, source.get("format", "plain"))
        for host in hosts:
            host = harvest.strip_www(str(host).lower())
            if not host or "." not in host:
                continue
            if host in drop:
                continue
            if harvest.covered_by(host, known):
                continue
            if harvest.categorize(host, rules):
                continue
            mentions.append((host, source["id"]))
    mentions = sorted(set(mentions))
    return mentions


def build():
    mentions = review_mentions()
    return {
        "mentions": len(mentions),
        "unique_hosts": len({host for host, _ in mentions}),
        "hosts": [{"host": host, "source": source} for host, source in mentions],
    }


def dump(document):
    return json.dumps(document, ensure_ascii=False, indent=2) + "\n"


def main(argv):
    parser = argparse.ArgumentParser(
        description="Name the source hosts no rule matched, offline."
    )
    parser.add_argument("--check", action="store_true", help="verify the file is current; write nothing")
    args = parser.parse_args(argv[1:])

    document = build()
    rendered = dump(document)

    if args.check:
        if not os.path.exists(OUT):
            print(f"✗ {OUT} is missing; run scripts/sources/pending.py", file=sys.stderr)
            return 1
        if open(OUT, encoding="utf-8").read() != rendered:
            print("✗ evidence/pending-source-hosts.json is stale; run scripts/sources/pending.py",
                  file=sys.stderr)
            return 1
        print(
            f"✓ pending-source-hosts.json is current "
            f"({document['unique_hosts']} host(s) across {document['mentions']} mention(s) need review)"
        )
        return 0

    os.makedirs(EVIDENCE, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as handle:
        handle.write(rendered)
    print(
        f"wrote evidence/pending-source-hosts.json: "
        f"{document['unique_hosts']} host(s) across {document['mentions']} mention(s) need review"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
