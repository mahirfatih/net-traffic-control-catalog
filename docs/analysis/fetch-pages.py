"""Fetch homepage text for every host in the catalog.

Results are cached under ``pages/<host>.txt`` so re-runs cost nothing.

Usage:
    python3 fetch-pages.py [--workers 12] [--timeout 12]
"""
from __future__ import annotations

import argparse
import concurrent.futures
import html
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
PAGES = Path(__file__).resolve().parent / "pages"
CATALOG = ROOT / "catalog.json"

USER_AGENT = "net-traffic-control-catalog/1.0 (+https://github.com/mahirfatih/net-traffic-control-catalog)"

_SCRIPT_STYLE = re.compile(r"(?is)<(script|style).*?</\1>")
_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")


def clean_text(raw: str) -> str:
    """Strip tags and collapse whitespace to plain text."""
    text = _SCRIPT_STYLE.sub(" ", raw)
    text = _TAG.sub(" ", text)
    return _WS.sub(" ", html.unescape(text)).strip()


def fetch(host: str) -> tuple[str, int, float, str]:
    """Return (host, text_length, seconds, error_or_empty)."""
    out = PAGES / f"{host}.txt"
    if out.exists():
        return host, out.stat().st_size, 0.0, ""

    t0 = time.time()
    try:
        proc = subprocess.run(
            [
                "curl", "-sSL", "-m", "12", "--max-filesize", "3000000",
                "-A", USER_AGENT, "-o", "-", f"https://{host}/",
            ],
            capture_output=True,
            timeout=18,
        )
        text = clean_text(proc.stdout.decode("utf-8", "replace"))
        out.write_text(text, encoding="utf-8")
        return host, len(text), time.time() - t0, "" if text else "empty"
    except Exception as exc:
        return host, 0, time.time() - t0, str(exc)[:60]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=12)
    args = ap.parse_args()

    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    hosts = sorted(catalog["categories"])
    PAGES.mkdir(exist_ok=True)

    t0 = time.time()
    done = empty = cached = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as ex:
        for host, n, _, err in ex.map(fetch, hosts):
            done += 1
            if n == 0:
                empty += 1
            elif err == "":
                cached += 1
            if done % 100 == 0:
                el = time.time() - t0
                print(f"  {done}/{len(hosts)}  {el:.0f}s", flush=True)

    el = time.time() - t0
    print(f"\n{done} host  |  {cached} ok  |  {empty} empty  |  {el:.0f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
