#!/usr/bin/env python3
"""Where every catalog host came from — and which ones came from nowhere.

    python3 scripts/catalog/seeds-provenance.py            # write evidence/seeds-only.json
    python3 scripts/catalog/seeds-provenance.py --check     # verify it is current, write nothing

A host in `catalog.json` is *attributed* when a rule in `rules.json` matches it
or when a source in `sources.json` listed it (or one of its subdomains). What is
left over is not a bug: it is the list that was here before any harvesting — the
hosts a person typed into `seeds/categories.json` by hand. This script names
them so the line "every host comes from a source" can never be believed by
accident.

The output is deliberately free of a timestamp: the same inputs must produce the
same bytes, or `--check` would fail once a day for no reason.
"""
import argparse
import importlib.util
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CATALOG = os.path.join(ROOT, "catalog.json")
RULES = os.path.join(ROOT, "config/rules.json")
SOURCES = os.path.join(ROOT, "config/sources.json")
EVIDENCE = os.path.join(ROOT, "evidence")
OUT = os.path.join(EVIDENCE, "seeds-only.json")
SEEDS = os.path.join(ROOT, "seeds", "categories.json")

# The closed suffixes `harvest-public-institutions.py` is allowed to import.
# A host under one of these reached the catalog through that script, not a
# person's hand.
PUBLIC_SUFFIXES = (".bel.tr", ".gov.tr", ".edu.tr")


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


catalog_core = _load("catalog_core", os.path.join(ROOT, "scripts", "catalog", "catalog-core.py"))
harvest = _load("harvest", os.path.join(ROOT, "scripts", "sources", "harvest.py"))


def load_json(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def ancestors(host):
    """`host` and every suffix that is still a name the app could match."""
    labels = host.split(".")
    for index in range(len(labels) - 1):  # stop before the bare TLD
        yield ".".join(labels[index:])


def strip_www(host):
    return host[4:] if host.startswith("www.") else host


def rule_hosts(rules):
    """Every host a rule in `rules.json` matches, lowercased."""
    out = set()
    for rule in rules.get("rules", []):
        for pattern in rule.get("match", []):
            out.add(str(pattern).lower())
    return out


def source_hosts():
    """Every host the committed source caches contain, parsed as harvest would.

    The `.txt` files under `evidence/` are the raw lists harvest.py fetched, so
    the provenance is read from the same bytes a review would read — not by
    re-downloading anything.
    """
    registry = load_json(SOURCES)
    hosts = set()
    for source in registry.get("sources", []):
        cache = os.path.join(EVIDENCE, f"{source['id']}.txt")
        if not os.path.exists(cache):
            continue
        with open(cache, encoding="utf-8") as handle:
            text = handle.read()
        found, _ = harvest.parse(text, source.get("format", "plain"))
        for host in found:
            host = strip_www(str(host).lower())
            if host and "." in host:
                hosts.add(host)
    return hosts


def classified(catalog_hosts, rule_set, src_set):
    """Split the catalog into rule-attributed, source-attributed, and the rest.

    A host is source-attributed in *either* direction: a source listed it (or an
    ancestor of it), or a source listed one of its subdomains — otherwise a
    parent that a source merely named a child of would look hand-typed.
    """
    src_parents = set()
    for host in src_set:
        src_parents.update(ancestors(host))

    by_rule, by_source, unattributed = [], [], []
    for host in catalog_hosts:
        names = set(ancestors(host))
        if names & rule_set:
            by_rule.append(host)
        elif (names & src_set) or (host in src_parents):
            by_source.append(host)
        else:
            unattributed.append(host)
    return sorted(by_rule), sorted(by_source), sorted(unattributed)


def founding():
    """The first commit that wrote `seeds/categories.json`, and what it held.

    Best-effort: a checkout without git (or without the file's history) reports
    nothing rather than guessing.
    """
    try:
        commit = subprocess.check_output(
            ["git", "log", "--diff-filter=A", "--format=%H", "--", SEEDS],
            cwd=ROOT, stderr=subprocess.DEVNULL, text=True,
        ).split("\n")[0].strip()
        if not commit:
            return None
        date = subprocess.check_output(
            ["git", "show", "-s", "--format=%ad", "--date=short", commit],
            cwd=ROOT, stderr=subprocess.DEVNULL, text=True,
        ).strip()
        blob = subprocess.check_output(
            ["git", "show", f"{commit}:seeds/categories.json"],
            cwd=ROOT, stderr=subprocess.DEVNULL, text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    return {"commit": commit[:7], "date": date, "hosts": sorted(json.loads(blob))}


def build():
    catalog = load_json(CATALOG)["categories"]
    rules = load_json(RULES)
    catalog_hosts = sorted(catalog)

    rule_set = rule_hosts(rules)
    src_set = source_hosts()

    by_rule, by_source, unattributed = classified(catalog_hosts, rule_set, src_set)
    public = [h for h in unattributed if h.endswith(PUBLIC_SUFFIXES)]
    hand = [h for h in unattributed if not h.endswith(PUBLIC_SUFFIXES)]

    found = founding()
    founding_block = None
    if found:
        present = set(catalog_hosts)
        first = set(found["hosts"])
        still = sorted(first & present)
        still_free = [h for h in still if h not in by_rule and h not in by_source]
        founding_block = {
            "commit": found["commit"],
            "date": found["date"],
            "hosts_in_first_commit": len(first),
            "still_in_catalog": len(still),
            "still_hand_entered": len(still_free),
        }

    return {
        "catalog_hosts": len(catalog_hosts),
        "attributed_to_rule": len(by_rule),
        "attributed_to_source": len(by_source),
        "attributed_total": len(by_rule) + len(by_source),
        "unattributed": {
            "total": len(unattributed),
            "public_institution": {"count": len(public), "suffixes": list(PUBLIC_SUFFIXES)},
            "hand_entered": {"count": len(hand), "hosts": hand},
        },
        "founding": founding_block,
    }


def dump(document):
    return json.dumps(document, ensure_ascii=False, indent=2, sort_keys=False) + "\n"


def main(argv):
    parser = argparse.ArgumentParser(description="Name the hosts that came from no rule and no source.")
    parser.add_argument("--check", action="store_true", help="verify the file is current; write nothing")
    args = parser.parse_args(argv[1:])

    document = build()
    rendered = dump(document)

    if args.check:
        if not os.path.exists(OUT):
            print(f"✗ {OUT} is missing; run scripts/catalog/seeds-provenance.py", file=sys.stderr)
            return 1
        current = open(OUT, encoding="utf-8").read()
        if current != rendered:
            print("✗ evidence/seeds-only.json is stale; run scripts/catalog/seeds-provenance.py",
                  file=sys.stderr)
            return 1
        un = document["unattributed"]
        print(f"✓ seeds-only.json is current ({un['total']} unattributed: "
              f"{un['public_institution']['count']} public-institution, "
              f"{un['hand_entered']['count']} hand-entered)")
        return 0

    os.makedirs(EVIDENCE, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as handle:
        handle.write(rendered)
    un = document["unattributed"]
    print(f"wrote evidence/seeds-only.json")
    print(f"  catalog hosts           {document['catalog_hosts']}")
    print(f"  attributed to a rule    {document['attributed_to_rule']}")
    print(f"  attributed to a source  {document['attributed_to_source']}")
    print(f"  unattributed            {un['total']}")
    print(f"    public-institution    {un['public_institution']['count']}")
    print(f"    hand-entered          {un['hand_entered']['count']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
