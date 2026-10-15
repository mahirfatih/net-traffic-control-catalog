"""Fetch homepage text for every host in the catalog.

Extracts <title>, meta description/keywords, headings (h1-h6), and body
text. Title + meta + headings are placed first because they carry the
strongest category signal (a page's own description of what it is).
Body text follows as supporting evidence.

Results are cached under ``.pages/<host>.txt`` so re-runs cost nothing.

Usage:
    python3 fetch-pages.py [--workers 12] [--timeout 12]
"""
from __future__ import annotations

import argparse
import concurrent.futures
import html
import json
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
PAGES = Path(__file__).resolve().parent / ".pages"
CATALOG = ROOT / "catalog.json"

USER_AGENT = "net-traffic-control-catalog/1.0 (+https://github.com/mahirfatih/net-traffic-control-catalog)"

_SCRIPT_STYLE = re.compile(r"(?is)<(script|style).*?</\1>")
_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")
_TITLE = re.compile(r"(?is)<title[^>]*>(.*?)</title>")
_META_DESC = re.compile(
    r'(?is)<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']*)["\']'
)
_META_KW = re.compile(
    r'(?is)<meta[^>]+name=["\']keywords["\'][^>]+content=["\']([^"\']*)["\']'
)
_HEADINGS = re.compile(r"(?is)<h[1-6][^>]*>(.*?)</h[1-6]>")


def _strip_tags(s: str) -> str:
    """Remove tags and collapse whitespace."""
    return _WS.sub(" ", html.unescape(_TAG.sub(" ", s))).strip()


def extract_text(raw: str) -> str:
    """Extract page text with title/meta/headings first, body last.

    Order: title -> meta description -> meta keywords -> headings -> body.
    This mirrors the reference repo's insight that a page's own metadata
    and structure are stronger category signals than body copy.
    """
    # Title
    title_match = _TITLE.search(raw)
    title = _strip_tags(title_match.group(1)) if title_match else ""

    # Meta description and keywords
    desc_match = _META_DESC.search(raw)
    desc = html.unescape(desc_match.group(1)).strip() if desc_match else ""
    kw_match = _META_KW.search(raw)
    kw = html.unescape(kw_match.group(1)).strip() if kw_match else ""

    # Headings
    headings = [_strip_tags(h) for h in _HEADINGS.findall(raw)]
    headings = [h for h in headings if h]

    # Body: strip script/style, then all tags
    body_raw = _SCRIPT_STYLE.sub(" ", raw)
    body_text = _strip_tags(body_raw)
    # Remove the parts we already extracted from body to avoid duplication
    for part in [title, desc, kw, " ".join(headings)]:
        if part:
            body_text = body_text.replace(part, " ")
    body_text = _WS.sub(" ", body_text).strip()

    # Assemble: title + meta + headings first, body last
    parts = [title, desc, kw]
    parts.extend(headings)
    parts.append(body_text)
    return " ".join(p for p in parts if p)


def fetch_url(url: str) -> bytes:
    proc = subprocess.run(
        [
            "curl", "-sSL", "-m", "12", "--max-filesize", "3000000",
            "-A", USER_AGENT, "-o", "-", url,
        ],
        capture_output=True,
        timeout=18,
    )
    return proc.stdout


def fetch(host: str, retry_below: int = 0) -> tuple[str, int, float, str]:
    """Return (host, text_length, seconds, error_or_empty).

    A host that yields nothing is retried once against `www.`, because an
    apex-only redirect is common enough to be worth the request. Nine categories
    in the audit were unmeasurable partly because the first attempt was the only
    attempt: an empty file was written and then treated as final forever.

    `retry_below` is the cached-size floor below which a host is fetched again:
    0 keeps every cached page (the default), 1 retries only the empty ones, and
    100 retries everything too short for the audit to use. The last is not the
    same as the first two — 459 catalog hosts have a cached page of 1-99
    characters that no flag ever looked at again, and a fresh fetch found usable
    text for 405 of them.

    What this cannot fix is a host that never answers. Measured on the nine
    categories the audit could not measure, 54 of 65 empty fetches failed with
    no HTTP response at all — `akamai.net`, `akadns.net` and friends are edge
    CDNs whose apex does not serve a page. Those need a different signal, not a
    different fetch.
    """
    out = PAGES / f"{host}.txt"
    if out.exists() and out.stat().st_size >= retry_below:
        return host, out.stat().st_size, 0.0, ""

    t0 = time.time()
    try:
        text = extract_text(fetch_url(f"https://{host}/").decode("utf-8", "replace"))
        if not text and not host.startswith("www."):
            text = extract_text(fetch_url(f"https://www.{host}/").decode("utf-8", "replace"))
        if out.exists() and not text and out.stat().st_size > 0:
            # A re-fetch that comes back empty must not overwrite a page that had
            # text: the cached copy is what the audit reads, and one transient
            # failure is not news about the host.
            return host, out.stat().st_size, time.time() - t0, ""
        out.write_text(text, encoding="utf-8")
        return host, len(text), time.time() - t0, "" if text else "empty"
    except Exception as exc:
        return host, 0, time.time() - t0, str(exc)[:60]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument(
        "--retry-empty",
        action="store_true",
        help="re-fetch hosts whose cached page is empty, trying www. as well",
    )
    ap.add_argument(
        "--retry-thin",
        type=int,
        default=0,
        metavar="N",
        help="also re-fetch hosts whose cached page has fewer than N characters "
             "(the audit's floor is 100; implies --retry-empty)",
    )
    args = ap.parse_args()

    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    hosts = sorted(catalog["categories"])
    PAGES.mkdir(exist_ok=True)

    retry_below = max(args.retry_thin, 1 if args.retry_empty else 0)

    t0 = time.time()
    done = empty = cached = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as ex:
        futures = [ex.submit(fetch, h, retry_below) for h in hosts]
        for future in concurrent.futures.as_completed(futures):
            host, n, _, err = future.result()
            done += 1
            if n == 0:
                empty += 1
            elif err == "":
                cached += 1
            if done % 100 == 0:
                el = time.time() - t0
                print(f"  {done}/{len(hosts)}  {el:.0f}s", flush=True)

    el = time.time() - t0
    scope = ""
    if retry_below:
        scope = f" (retrying below {retry_below} char)"
    print(f"\n{done} host  |  {cached} ok  |  {empty} empty  |  {el:.0f}s{scope}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
