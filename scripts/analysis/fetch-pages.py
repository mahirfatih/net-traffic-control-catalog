"""Fetch homepage text for every host in the catalog.

Extracts <title>, meta description/keywords, headings (h1-h6), and body
text. Title + meta + headings are placed first because they carry the
strongest category signal (a page's own description of what it is).
Body text follows as supporting evidence.

Results are cached under ``.pages/<host>.txt`` so re-runs cost nothing.

The default fetch is `curl`. A JS-heavy page therefore arrives as a shell with
no prose — which is why `gaming`, `cdn` and `software` are measured on a fifth
to a third of their hosts. `--render-thin N` re-fetches a host whose plain-HTML
text came back under `N` characters through the **same browser harness the live
sweep uses** (`agent-browser` with Lightpanda, `--engine lightpanda`): a real
render turns the shell into title + body text. It is opt-in because it needs the
browser and is far slower than `curl`, and it stays out of `test/test.sh` for
the same reason the sweeps do.

Usage:
    python3 fetch-pages.py [--workers 12]
    python3 fetch-pages.py --render-thin 100          # browser fallback
    python3 fetch-pages.py --self-test
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
PAGES = Path(__file__).resolve().parent / ".pages"
CATALOG = ROOT / "catalog.json"

USER_AGENT = "net-traffic-control-catalog/1.0 (+https://github.com/mahirfatih/net-traffic-control-catalog)"

# The browser harness, identical to the one in sweep-live.py. Fetching a second
# time with the tools the live sweep already trusts keeps one engine's
# behaviour as the single thing to reason about.
ENGINE = "lightpanda"
AGENT_BROWSER = "agent-browser"

# What a render yields: the page's own metadata plus the text a person would
# read. `innerText` (not `textContent`) so hidden template markup does not leak
# in as prose. Assembled in the same order extract_text() uses.
RENDER_JS = (
    "(function(){"
    "function meta(n){var m=document.querySelector('meta[name=\"'+n+'\"]');"
    "return m?(m.getAttribute('content')||''):'';}"
    "var hs=Array.prototype.map.call(document.querySelectorAll('h1,h2,h3,h4,h5,h6'),"
    "function(h){return h.textContent||'';});"
    "var b=document.body?(document.body.innerText||''):'';"
    "return JSON.stringify({title:document.title||'',desc:meta('description'),"
    "kw:meta('keywords'),headings:hs,body:b});})()"
)

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


def text_from_render(payload: dict) -> str:
    """Assemble a render payload into the shape `extract_text` returns.

    Pure, so it is the part `--self-test` can check without a browser: the
    ordering (title, meta, headings, body) has to match the curl path exactly,
    or a host measured through the browser would feed the classifier a
    differently-shaped page than one measured through `curl`.
    """
    if not isinstance(payload, dict):
        return ""
    parts = [str(payload.get("title") or ""), str(payload.get("desc") or ""),
             str(payload.get("kw") or "")]
    parts.extend(str(h) for h in (payload.get("headings") or []) if h)
    parts.append(str(payload.get("body") or ""))
    return _WS.sub(" ", " ".join(p for p in parts if p)).strip()


def parse_browser_batch(stdout: str) -> dict | None:
    """The eval payload in the stdout of `agent-browser batch --bail --json`.

    The batch ends with an `eval` entry whose `result.result` is our JSON
    string. Anything else — a partial array after `--bail`, a navigation error —
    returns None, so a failed render writes nothing rather than garbage.
    """
    try:
        entries = json.loads(stdout)
    except (ValueError, TypeError):
        return None
    if not isinstance(entries, list):
        return None
    for entry in entries:
        command = entry.get("command") or []
        if command and command[0] == "eval" and entry.get("success"):
            raw = (entry.get("result") or {}).get("result")
            if isinstance(raw, str):
                try:
                    return json.loads(raw)
                except ValueError:
                    return None
    return None


def render_with_browser(host: str, args) -> str:
    """Render `host` with agent-browser + Lightpanda; return page text or "".

    The same batch `sweep-live.py` runs, but the eval returns the whole rendered
    document instead of a 1,500-character sample. A host the engine cannot reach
    returns "" — a render failure is not news about the host, so the caller
    keeps whatever `curl` found.
    """
    commands = [["open", f"https://{host}/"], ["eval", RENDER_JS]]
    argv = [args.agent_browser, "--engine", ENGINE]
    if args.lightpanda:
        argv += ["--executable-path", args.lightpanda]
    if args.user_agent:
        argv += ["--user-agent", args.user_agent]
    argv += ["batch", "--bail", "--json"]
    env = dict(os.environ)
    env["AGENT_BROWSER_DEFAULT_TIMEOUT"] = str(args.timeout_ms)
    try:
        proc = subprocess.run(
            argv, input=json.dumps(commands), capture_output=True, text=True,
            timeout=args.timeout_ms / 1000.0 + args.grace_seconds, env=env,
        )
    except (subprocess.TimeoutExpired, OSError, subprocess.SubprocessError):
        return ""
    payload = parse_browser_batch(proc.stdout or "")
    return text_from_render(payload) if payload else ""


def fetch(host: str, retry_below: int = 0, render_below: int = 0, args=None) -> tuple[str, int, float, str]:
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
        if render_below and args is not None and len(text) < render_below:
            # Plain HTML came back too thin — a JS shell, most likely. Render it
            # with the browser the live sweep already uses. Keep whichever text
            # is longer, so a render the engine dropped cannot shrink a page
            # curl already read.
            rendered = render_with_browser(host, args)
            if len(rendered) > len(text):
                text = rendered
        if out.exists() and not text and out.stat().st_size > 0:
            # A re-fetch that comes back empty must not overwrite a page that had
            # text: the cached copy is what the audit reads, and one transient
            # failure is not news about the host.
            return host, out.stat().st_size, time.time() - t0, ""
        out.write_text(text, encoding="utf-8")
        return host, len(text), time.time() - t0, "" if text else "empty"
    except Exception as exc:
        return host, 0, time.time() - t0, str(exc)[:60]


def self_test() -> int:
    """Check the pure parts without a network, then report the engine.

    The parsing and assembly are what a broken render would silently corrupt,
    so they are asserted here. The engine check is informational: a checkout
    that never renders must still pass.
    """
    payload = {
        "title": "Example Bank",
        "desc": "Online banking",
        "kw": "bank, loans",
        "headings": ["Welcome", "Cards"],
        "body": "Log in to your account",
    }
    text = text_from_render(payload)
    assert text.startswith("Example Bank Online banking bank, loans Welcome Cards"), text
    assert text.endswith("Log in to your account"), text
    assert text_from_render(None) == "", "a missing payload must assemble to nothing"

    batch = json.dumps([
        {"command": ["open"], "success": True, "result": {"title": "x"}},
        {"command": ["eval"], "success": True, "result": {"result": json.dumps(payload)}},
    ])
    assert parse_browser_batch(batch) == payload, "the eval payload must round-trip"
    assert parse_browser_batch("not json") is None, "garbage must not parse"
    assert parse_browser_batch(json.dumps([{"command": ["open"], "success": False}])) is None
    print("✓ render parsing and text assembly")

    try:
        proc = subprocess.run([AGENT_BROWSER, "--version"], capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.SubprocessError):
        print(f"· {AGENT_BROWSER} not found — --render-thin would need it (skipped)")
        return 0
    version = (proc.stdout or proc.stderr or "").strip().splitlines()
    print(f"· {AGENT_BROWSER}: {version[0] if version else 'present'}")
    print(f"· engine: {ENGINE}")
    return 0


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
    ap.add_argument(
        "--render-thin",
        type=int,
        default=0,
        metavar="N",
        help="re-fetch hosts whose plain-HTML text is under N characters through "
             "the browser harness (agent-browser + lightpanda), then keep the longer text",
    )
    ap.add_argument("--agent-browser", default=AGENT_BROWSER)
    ap.add_argument("--lightpanda", default="", help="path to the lightpanda binary")
    ap.add_argument("--user-agent", default=USER_AGENT)
    ap.add_argument("--timeout-ms", type=int, default=20000)
    ap.add_argument("--grace-seconds", type=float, default=8.0)
    ap.add_argument("--self-test", action="store_true", help="check the pure parts and the engine, then exit")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    hosts = sorted(catalog["categories"])
    PAGES.mkdir(exist_ok=True)

    retry_below = max(args.retry_thin, args.render_thin, 1 if args.retry_empty else 0)

    t0 = time.time()
    done = empty = cached = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as ex:
        futures = [ex.submit(fetch, h, retry_below, args.render_thin, args) for h in hosts]
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
    if args.render_thin:
        scope += f" (rendering below {args.render_thin} char)"
    print(f"\n{done} host  |  {cached} ok  |  {empty} empty  |  {el:.0f}s{scope}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
