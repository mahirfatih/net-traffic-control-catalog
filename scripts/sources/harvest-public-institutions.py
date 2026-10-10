#!/usr/bin/env python3
"""Harvest Turkish public institution domains into the category seeds.

    python3 scripts/sources/harvest-public-institutions.py --check
    python3 scripts/sources/harvest-public-institutions.py --write

The script fetches reviewable public directory pages and extracts only the
closed public/education suffixes this catalog already treats as strong evidence:

- `*.bel.tr` -> `government`
- `*.gov.tr` -> `government`
- `*.edu.tr` -> `education`

Existing labels win. Known non-government/non-education overrides stay exactly
where a human put them, and known parked names are skipped so the iOS exclusion
guard does not have to rediscover the same failure.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SEED = ROOT / "seeds" / "categories.json"
BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0 Safari/537.36"
)


@dataclass(frozen=True)
class Source:
    id: str
    url: str
    suffixes: tuple[str, ...]
    encoding: str = "utf-8"
    strict_accept: bool = True


SOURCES = [
    Source(
        id="tbb-provincial-municipalities",
        url="https://www.tbb.gov.tr/tr/il-belediyeleri",
        suffixes=("bel.tr",),
    ),
    Source(
        id="tbb-metropolitan-municipalities",
        url="https://www.tbb.gov.tr/tr/buyuksehir-belediyeleri",
        suffixes=("bel.tr",),
    ),
    Source(
        id="esehir-e-devlet",
        url="https://www.e-sehir.com/e-devlet/",
        suffixes=("gov.tr", "edu.tr"),
        encoding="iso-8859-9",
        strict_accept=False,
    ),
    Source(
        id="esehir-public-institutions",
        url="https://www.e-sehir.com/e-devlet/bakanliklar-kamu-kurumlari.php",
        suffixes=("gov.tr", "edu.tr"),
        encoding="iso-8859-9",
        strict_accept=False,
    ),
    Source(
        id="agcevre-ministry-addresses",
        url="https://www.agcevre.com.tr/tr/bakanlik-web-sitesi-adresleri",
        suffixes=("gov.tr", "edu.tr"),
    ),
    Source(
        id="ccift-turkey-institutions",
        url="https://www.ccift.com/tr/dernegimiz/tuerkiyedeki-belli-basli-kurumlar-ve-web-siteleri.html",
        suffixes=("gov.tr", "edu.tr"),
    ),
    Source(
        id="yok-public-universities",
        url="https://www.yok.gov.tr/tr/university?type=1",
        suffixes=("edu.tr",),
    ),
]


# These hosts use a government suffix but are intentionally cataloged by what
# users understand them as. Never let a bulk harvest flatten them.
OVERRIDES = {
    "meb.gov.tr": "education",
    "osym.gov.tr": "education",
    "saglik.gov.tr": "health",
    "tcmb.gov.tr": "finance",
    "tdk.gov.tr": "encyclopedia",
}


# iOS ReferenceData/excluded.csv records why these should not be vendored as
# catalog rows even though suffix rules still classify them at runtime.
EXCLUDED = {
    "bddk.gov.tr",
    "emekli.gov.tr",
    "muzekart.gov.tr",
    "sgb.gov.tr",
    "ticaret.gov.tr",
}


def normalize(host: str) -> str | None:
    host = host.lower().strip().strip(".")
    while host.startswith("www."):
        host = host[4:]
    if re.fullmatch(r"[a-z0-9][a-z0-9.-]*[a-z0-9]\.(?:bel|gov|edu)\.tr", host):
        return host
    return None


def category_for(host: str) -> str:
    return "education" if host.endswith(".edu.tr") else "government"


def fetch(source: Source) -> str:
    headers = {"User-Agent": BROWSER_UA}
    if source.strict_accept:
        headers.update(
            {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "tr,en;q=0.8",
            }
        )
    request = urllib.request.Request(
        source.url,
        headers=headers,
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read().decode(source.encoding, "ignore")


def extract_hosts(text: str, suffixes: Iterable[str]) -> set[str]:
    text = html.unescape(text)
    suffix_pattern = "|".join(re.escape(suffix) for suffix in suffixes)
    pattern = re.compile(rf"([A-Za-z0-9.-]+\.(?:{suffix_pattern}))\b", re.IGNORECASE)
    hosts = set()
    for match in pattern.findall(text):
        host = normalize(match)
        if host:
            hosts.add(host)
    return hosts


def load_seed(path: Path) -> dict[str, str]:
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must be a JSON object")
    return data


def write_seed(path: Path, data: dict[str, str]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(dict(sorted(data.items())), handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="fetch and report; do not write seeds")
    mode.add_argument("--write", action="store_true", help="merge new hosts into seeds/categories.json")
    parser.add_argument("--seed", default=str(DEFAULT_SEED), help="category seed path")
    args = parser.parse_args(argv[1:])

    seed_path = Path(args.seed)
    categories = load_seed(seed_path)
    discovered: dict[str, set[str]] = {}
    for source in SOURCES:
        try:
            text = fetch(source)
        except OSError as error:
            print(f"✗ cannot fetch {source.id} ({source.url}): {error}", file=sys.stderr)
            return 2
        hosts = extract_hosts(text, source.suffixes)
        discovered[source.id] = hosts

    all_hosts = sorted(set().union(*discovered.values()))
    added: list[str] = []
    duplicates: list[str] = []
    excluded: list[str] = []
    overrides: dict[str, str] = {}
    conflicts: dict[str, str] = {}

    for host in all_hosts:
        target = category_for(host)
        existing = categories.get(host)
        if host in EXCLUDED:
            excluded.append(host)
            continue
        if existing == target:
            duplicates.append(host)
            continue
        if existing:
            if OVERRIDES.get(host) == existing:
                overrides[host] = existing
                continue
            conflicts[host] = existing
            continue
        categories[host] = target
        added.append(host)

    for source_id, hosts in discovered.items():
        print(f"{source_id}: {len(hosts)} host(s)")
    print(
        f"total={len(all_hosts)} added={len(added)} duplicate={len(duplicates)} "
        f"override={len(overrides)} excluded={len(excluded)} conflict={len(conflicts)}"
    )

    if added:
        print("\nAdded:")
        for host in added:
            print(f"  {host}: {category_for(host)}")
    if overrides:
        print("\nKept overrides:")
        for host, category in sorted(overrides.items()):
            print(f"  {host}: {category}")
    if excluded:
        print("\nSkipped excluded:")
        for host in sorted(excluded):
            print(f"  {host}")
    if conflicts:
        print("\nConflicts:", file=sys.stderr)
        for host, category in sorted(conflicts.items()):
            print(f"  {host}: existing {category}, harvested {category_for(host)}", file=sys.stderr)
        return 1

    if args.write:
        write_seed(seed_path, categories)
        print(f"\nwrote {seed_path}")
    elif added:
        print("\n--check found hosts that are not in the seed; run again with --write")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
