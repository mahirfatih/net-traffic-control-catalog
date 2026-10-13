#!/usr/bin/env python3
"""Human category overrides: the layer that beats rules and sources.

    python3 scripts/catalog/overrides.py list
    python3 scripts/catalog/overrides.py set example.com shopping --reason "sells goods"
    python3 scripts/catalog/overrides.py remove example.com
    python3 scripts/catalog/overrides.py --check

`rules.json` → `override` is the single place a category can be decided by hand
for one host. The precedence is fixed and written down so a source refresh can
never quietly undo a review:

    override  >  rules  >  harvested source

`generate.py` applies overrides last, `merge.py` refuses to overwrite an
overridden host, and the audits treat overrides as deliberate.
"""
import argparse
import importlib.util
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RULES = os.path.join(ROOT, "rules.json")

_spec = importlib.util.spec_from_file_location(
    "catalog_core", os.path.join(ROOT, "scripts", "catalog", "catalog-core.py")
)
catalog_core = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(catalog_core)


def load_rules(path=RULES):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def overrides(document):
    """Return `{host: (category, reason)}` from a loaded `rules.json`."""
    raw = (document.get("drop") or {}).get("override") or {}
    out = {}
    for host, value in raw.items():
        if isinstance(value, dict):
            out[host.strip().lower()] = (
                str(value.get("category", "")).strip().lower(),
                str(value.get("reason", "")).strip(),
            )
        else:
            # Tolerate a shorthand `{host: category}` but keep the reason empty
            # so `--check` reports it rather than silently accepting it.
            out[host.strip().lower()] = (str(value).strip().lower(), "")
    return out


def apply(categories, document):
    """Return `categories` with overrides applied, and the problems found.

    Applied last, so an override always wins. A problem does not change the
    result here — `--check` is what fails a build — but it is returned so the
    caller can refuse to write a catalog built from a broken override map.
    """
    problems = []
    result = dict(categories)
    for host, (category, reason) in overrides(document).items():
        if catalog_core.host_problems(host):
            problems.append(f"override host {host!r} {catalog_core.host_problems(host)}")
            continue
        if category not in catalog_core.VOCABULARY:
            problems.append(f"override {host!r} has category {category!r} outside the vocabulary")
            continue
        if not reason:
            problems.append(f"override {host!r} has no reason")
        result[host] = category
    return result, problems


def check(document):
    """Every problem with the override map, as a list of strings."""
    problems = []
    raw = (document.get("drop") or {}).get("override")
    if raw is None:
        return problems
    if not isinstance(raw, dict):
        return ["drop.override is not an object"]

    drops = (document.get("drop") or {}).get("hosts") or {}
    for host, value in sorted(raw.items()):
        why = catalog_core.host_problems(host)
        if why:
            problems.append(f"override host {host!r} {why}")
        if host in drops:
            problems.append(f"override {host!r} is also in drop.hosts; a host cannot be both")
        if isinstance(value, dict):
            category = str(value.get("category", "")).strip().lower()
            reason = str(value.get("reason", "")).strip()
        else:
            category = str(value).strip().lower()
            reason = ""
        if category not in catalog_core.VOCABULARY:
            problems.append(f"override {host!r} has category {category!r} outside the vocabulary")
        if not reason:
            problems.append(f"override {host!r} has no reason")
    return problems


def _write(document, path):
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(document, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def main(argv):
    parser = argparse.ArgumentParser(description="Manage category overrides in rules.json.")
    parser.add_argument("--rules", default=RULES, help="path to rules.json")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("list", help="print every override")
    sub.add_parser("check", help="validate the override map")

    setter = sub.add_parser("set", help="add or replace an override")
    setter.add_argument("host")
    setter.add_argument("category")
    setter.add_argument("--reason", required=True)

    remover = sub.add_parser("remove", help="delete an override")
    remover.add_argument("host")

    args = parser.parse_args(argv[1:])
    document = load_rules(args.rules)

    if args.command in (None, "check"):
        problems = check(document)
        if problems:
            for problem in problems:
                print(f"✗ {problem}", file=sys.stderr)
            return 1
        print(f"✓ overrides valid ({len(overrides(document))} entr(ies))")
        return 0

    if args.command == "list":
        for host, (category, reason) in sorted(overrides(document).items()):
            print(f"{host:40} {category:12} {reason}")
        return 0

    mapping = document.setdefault("drop", {}).setdefault("override", {})

    if args.command == "set":
        host = args.host.strip().lower()
        category = args.category.strip().lower()
        mapping[host] = {"category": category, "reason": args.reason.strip()}
    elif args.command == "remove":
        host = args.host.strip().lower()
        if host not in mapping:
            print(f"✗ no override for {host!r}", file=sys.stderr)
            return 1
        del mapping[host]

    document["drop"]["override"] = {host: mapping[host] for host in sorted(mapping)}

    problems = check(document)
    if problems:
        for problem in problems:
            print(f"✗ {problem}", file=sys.stderr)
        print("refusing to write", file=sys.stderr)
        return 1

    _write(document, args.rules)
    print(f"✓ wrote {os.path.relpath(args.rules, ROOT)}: {len(overrides(document))} override(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
