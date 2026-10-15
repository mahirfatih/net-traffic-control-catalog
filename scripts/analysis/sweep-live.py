#!/usr/bin/env python3
"""Visit every catalog host with a real browser — evidence, never a guess.

    python3 scripts/analysis/sweep-live.py --self-test
    python3 scripts/analysis/sweep-live.py --round 1 [--limit 75] [--aggressive]
    python3 scripts/analysis/sweep-live.py --round 2 [--aggressive]
    python3 scripts/analysis/sweep-live.py --summary [--aggressive]
    python3 scripts/analysis/sweep-live.py --apply      # only after you read --summary

The DNS sweep (`scripts/catalog/probe-dead.py`) answers "does the name exist?".
This answers a different question about the same host: **does it still serve a
page?** A name can resolve and still return nothing — a parked domain, a dead
CDN apex, a host whose owner let the site lapse. That is the "empty domain"
this sweep is for.

It drives a real browser through `agent-browser
<https://github.com/vercel-labs/agent-browser>`_ with Lightpanda as the engine
(`--engine lightpanda`, <https://lightpanda.io>), because a fetch that does not
run JavaScript sees an empty shell where a modern page lives. Lightpanda is
headless-only and has no rendering pipeline, so screenshots are placeholders
and very heavy single-page apps may render blank — that limitation is recorded
in the evidence as `empty`, never as a silent success.

Nothing here edits catalog data. The output is evidence plus a *proposal* (the
hosts both rounds agree serve nothing), and a person decides what to do with
it. This script needs the network and a browser, so it is deliberately not part
of `test/test.sh`; the decision logic it shares with the suite is tested there,
offline.

Trust is the whole design. A long sweep is more likely to lose its engine
(Lightpanda dies, a CDP call hangs) than to meet thousands of truly dead hosts,
and a poisoned run would hand a person a list of live sites to delete. So a
failure is never believed on its own: before a host is recorded as unresponsive
the harness re-proves itself with a canary, and if the canary fails the host is
filed as `harness-error`, which is never a removal candidate.
"""

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timezone
import importlib.util
import json
import os
import queue
import shutil
import subprocess
import sys
import threading
import time
import urllib.parse


ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CATEGORIES = os.path.join(ROOT, "seeds", "categories.json")
RULES = os.path.join(ROOT, "rules.json")
EVIDENCE = os.path.join(ROOT, "evidence")
STATE = os.path.join(EVIDENCE, "live-sweep.json")
MARKDOWN = os.path.join(EVIDENCE, "live-sweep.md")
DEAD_STATE = os.path.join(EVIDENCE, "dead-domain-sweep.json")

ENGINE = "lightpanda"
AGENT_BROWSER = "agent-browser"
USER_AGENT = (
    "net-traffic-control-catalog/1.0 "
    "(+https://github.com/mahirfatih/net-traffic-control-catalog)"
)
SAVE_EVERY = 200

# One host, one browser call. `requests --clear` first so a *previous* page's
# network log cannot be mistaken for this one's (a failed navigation leaves the
# old document loaded), then the navigation, then the read, then the log.
EVAL_JS = (
    "(function(){var b=document.body;"
    "var t=b?(b.innerText||b.textContent||''):'';"
    "return JSON.stringify({t:(document.title||'').slice(0,300),"
    "u:location.href,n:t.length,h:t.slice(0,1500)});})()"
)

# Outcomes, best (most alive) to worst. `host_decision` keeps the most alive
# result any attempt produced, so one transient failure cannot outvote a page
# that did load. `harness-error` is last: a real host signal always beats the
# engine's own confusion.
OUTCOME_RANK = {
    "content": 0,
    "blocked": 1,
    "parked": 2,
    "empty": 3,
    "no-http": 4,
    "tls-error": 5,
    "error": 6,
    "dns-error": 7,
    "timeout": 8,
    "harness-error": 9,
}
DECISION_NAMES = {
    "content": "ok",
    "blocked": "blocked",
    "parked": "parked",
    "empty": "empty",
    "no-http": "no-http",
    "tls-error": "tls-error",
    "error": "error",
    "dns-error": "dns-error",
    "timeout": "timeout",
    "harness-error": "harness-error",
}
# Everything the report prints, in order.
DECISIONS = (
    "ok",
    "blocked",
    "parked",
    "empty",
    "no-http",
    "dns-error",
    "tls-error",
    "error",
    "timeout",
    "harness-error",
)

# Never a removal candidate: a page that loaded, a page that answered but is
# refusing automated traffic (a live site behind Cloudflare is not empty), and
# the harness losing its footing.
NEVER_CANDIDATE = {"ok", "blocked", "harness-error"}
# The one signal that means "this host serves nothing" without ambiguity: a
# parked page. A parked domain resolves, answers 200, and says the domain is for
# sale — the site is gone and the name is waiting for a new owner, which is
# exactly the recycling risk this exists for. Proposed even in the conservative
# default.
STRONG_CANDIDATE = {"parked"}
# A candidate only under `--aggressive`: a 404/5xx/refused at the root, or a 200
# with no text. Neither is proof the host is empty. `adnxs.com` (an ad network),
# `3dsecure.akbank.com.tr` (a bank's 3-D Secure endpoint) and `api.pluto.tv` all
# answer a browser with nothing and still belong in a DNS-filter catalog, so
# these are proposed only when a person reads the proposal and asks for them.
WEAK_CANDIDATE = {"empty", "no-http"}
# Never proposed automatically, whatever the mode: a certificate failure, a
# timeout, a resolver miss on this network says *this environment could not
# reach the host*, not that the host serves nothing. `youtube-nocookie.com` and
# `jsdelivr.net` land here on a bad afternoon. True name-death is the DNS
# sweep's job (`probe-dead.py`); these are reported for a person, and only a
# deliberate `--include-flaky` turns them into candidates.
FLAKY = {"tls-error", "timeout", "error", "dns-error"}

# Blocked is not empty. These answer a real request and are held back on
# purpose; deleting them would remove live sites from the catalog.
BLOCKED_STATUS = {401, 403, 405, 429, 451}
# Parking language, and nothing but. These phrases almost never appear in
# ordinary prose, which matters: an earlier version of this list also held
# "it works!", "under construction" and "coming soon", and they matched the real
# pages of `duolingo.com`, `gspfinance.com` and `plfsbd.com` — three live hosts
# filed as parked and, in the default mode, proposed for deletion. A marker is
# only worth having if a real page cannot contain it.
PARKING_MARKERS = (
    "domain is for sale",
    "domain for sale",
    "buy this domain",
    "this domain is parked",
    "domain parked",
    "parked by ",
    "parked page",
    "sedoparking",
    "hugedomains",
    "afternic",
    "namecheap parking",
    "godaddy.com/domain",
)
PARKING_HOSTS_NEEDLES = (
    "sedoparking",
    "parkingcrew",
    "above.com",
    "bodis.com",
    "hugedomains",
    "afternic",
    "undeveloped.com",
    "dan.com",
    "parklogic",
    "domainmarket",
)
MIN_CONTENT = 60  # below this, a "page" is an empty shell
# A parked page is short. A long page that merely mentions a parking phrase is
# a real page, so the phrase is only read from the body under this length.
MAX_PARKED_LENGTH = 600

# A canary each session must answer before a *failure* about a host is
# believed. If the canary is down, the failure is ours, not the host's.
CANARY_HOST = "example.com"


def load_json(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def save_state(state, path):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(state, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
    os.replace(tmp, path)


# --------------------------------------------------------------------------- #
# Decision logic — pure, so `test/test.sh` can test it without a network.
# --------------------------------------------------------------------------- #


def classify_attempt(status, text_length, title, final_url, haystack, error):
    """Turn one navigation's raw signals into an `outcome` name.

    `status` is the final Document status (after redirects), or None when the
    navigation produced no response at all. `haystack` is the page text (lower
    cased by the caller) used only to look for parking markers.
    """
    if error:
        return classify_error(error)
    if status is None:
        # A page with a title and text but no logged Document request is odd,
        # but the content is the stronger signal: believe what loaded.
        return "content" if text_length >= MIN_CONTENT else "empty"
    if status in BLOCKED_STATUS:
        return "blocked"
    if 400 <= status < 500:
        # 404 and friends: the server answered, but serves no page here.
        return "no-http"
    if 500 <= status < 600:
        return "no-http"
    if 300 <= status < 400:
        # Redirect that never resolved to a document we could read.
        return "empty" if text_length < MIN_CONTENT else "content"
    # 2xx
    if looks_parked(haystack, title, final_url, text_length):
        return "parked"
    if text_length < MIN_CONTENT:
        return "empty"
    return "content"


def classify_error(error):
    """Map a browser navigation error string to an outcome."""
    low = error.lower().replace("_", " ").replace("::", " ")
    if "resolve" in low or "name not resolved" in low or "unknown host" in low:
        return "dns-error"
    if "verification" in low or "ssl" in low or "tls" in low or "certificate" in low:
        return "tls-error"
    if "timeout" in low or "timed out" in low or "timedout" in low:
        return "timeout"
    # Connection refused / no route / nothing listening on 80/443.
    return "no-http"


def looks_parked(haystack, title, final_url, text_length=0):
    """Is this page a parking notice?

    The title and the final URL are the trustworthy places to look: a page that
    says "domain is for sale" in its title, or lands on `hugedomains.com`, is
    parked whatever its body says. The body is only consulted for a short page,
    because a long one that happens to contain a phrase is a real site.
    """
    head = f"{(title or '').lower()} {(final_url or '').lower()}"
    if any(marker in head for marker in PARKING_MARKERS):
        return True
    if any(needle in (final_url or "").lower() for needle in PARKING_HOSTS_NEEDLES):
        return True
    if text_length <= MAX_PARKED_LENGTH:
        return any(marker in haystack for marker in PARKING_MARKERS)
    return False


def host_decision(outcomes):
    """The most alive outcome across a host's attempts, as a decision name."""
    if not outcomes:
        return "harness-error"
    best = min(outcomes, key=lambda o: OUTCOME_RANK.get(o, 99))
    return DECISION_NAMES.get(best, "error")


def is_candidate(decision, aggressive, include_flaky=False):
    """Is this decision a reason to propose removal?"""
    if decision in NEVER_CANDIDATE:
        return False
    if decision in FLAKY:
        return include_flaky
    if decision in STRONG_CANDIDATE:
        return True
    if decision in WEAK_CANDIDATE:
        return aggressive
    return False


def round_candidates(round_entry, aggressive, include_flaky=False):
    """Hosts in one complete round that are removal candidates."""
    return {
        host
        for host, result in round_entry.get("results", {}).items()
        if is_candidate(result.get("decision"), aggressive, include_flaky)
    }


def build_proposal(state, aggressive, include_flaky=False):
    """Hosts every complete round independently calls removable.

    `None` when fewer than two complete rounds exist — one round is a snapshot,
    and a single engine outage is a snapshot too. A host the harness could not
    speak for (`harness-error`) in any round is dropped from the proposal, not
    guessed at.
    """
    rounds = [
        entry
        for entry in state.get("rounds", [])
        if entry.get("complete") and entry.get("results")
    ]
    rounds.sort(key=lambda e: e.get("round", 0))
    if len(rounds) < 2:
        return None
    agreed = None
    for entry in rounds:
        candidates = round_candidates(entry, aggressive, include_flaky)
        agreed = candidates if agreed is None else (agreed & candidates)
    # Drop any host the harness failed to judge in any round.
    uncertain = {
        host
        for entry in rounds
        for host, result in entry.get("results", {}).items()
        if result.get("decision") == "harness-error"
    }
    return sorted(agreed - uncertain)


def flaky_hosts(state):
    """Hosts an environment failure kept out of the proposal — for the report."""
    out = {}
    for entry in sorted(state.get("rounds", []), key=lambda e: e.get("round", 0)):
        for host, result in entry.get("results", {}).items():
            if result.get("decision") in FLAKY:
                out.setdefault(host, result.get("decision"))
    return out


def dns_cross_check(state, proposal, dead_state_path=DEAD_STATE):
    """Compare the browser proposal with the DNS sweep's evidence, when present.

    Two independent signals about the same host are worth more than either
    alone. `dns_dead` hosts the DNS sweep also called gone strengthen a
    proposal; `conflicts` are hosts the browser could not reach but DNS still
    answers — the case that cost this catalog 181 real banks once, and the one
    a person should look at before applying anything.
    """
    out = {"dns_dead": [], "conflicts": [], "available": False}
    if not os.path.exists(dead_state_path):
        return out
    try:
        dead = load_json(dead_state_path)
    except (OSError, ValueError):
        return out
    out["available"] = True

    def dead_hosts(entry):
        return {
            host
            for host, result in entry.get("results", {}).items()
            if result.get("decision") == "dead"
        }

    rounds = [e for e in dead.get("rounds", []) if e.get("complete") and e.get("results")]
    rounds.sort(key=lambda e: e.get("round", 0))
    if not rounds:
        return out
    dns_dead = set(rounds[0]["results"])
    for entry in rounds[1:]:
        dns_dead &= dead_hosts(entry)
    for entry in rounds:
        dns_dead |= dead_hosts(entry)
    # hosts both DNS rounds agreed are gone AND the browser could not reach
    out["dns_dead"] = sorted(set(proposal) & dns_dead)
    out["conflicts"] = sorted(set(proposal) - dns_dead)
    return out


# --------------------------------------------------------------------------- #
# The browser harness.
# --------------------------------------------------------------------------- #


def _agent_browser_argv(session, url, args):
    argv = [args.agent_browser, "--session", session, "--engine", ENGINE]
    if args.user_agent:
        argv += ["--user-agent", args.user_agent]
    if args.lightpanda:
        argv += ["--executable-path", args.lightpanda]
    return argv


def _run_batch(session, url, args):
    """Run one host's browser work over stdin JSON. Returns the parsed entries."""
    commands = [
        ["network", "requests", "--clear"],
        ["open", f"https://{url}/"],
        ["eval", EVAL_JS],
        ["network", "requests", "--json"],
    ]
    argv = _agent_browser_argv(session, url, args) + ["batch", "--bail", "--json"]
    env = dict(os.environ)
    env["AGENT_BROWSER_DEFAULT_TIMEOUT"] = str(args.timeout_ms)
    proc = subprocess.run(
        argv,
        input=json.dumps(commands),
        capture_output=True,
        text=True,
        timeout=args.timeout_ms / 1000.0 + args.grace_seconds,
        env=env,
    )
    text = (proc.stdout or "").strip()
    if not text:
        return None, (proc.stderr or "empty browser output").strip()[:300]
    try:
        return json.loads(text), None
    except ValueError:
        # --bail can leave a partial array; keep whatever parsed as a list.
        return None, text[:300]


def _entry(entries, name):
    for entry in entries:
        cmd = entry.get("command") or []
        if cmd and cmd[0] == name:
            return entry
    return None


def _requests_result(entries):
    """The `network requests` result that actually carries a request log.

    The batch issues `network requests --clear` first; that entry is also named
    `network`, so the first match is the wrong one. Pick the entry whose result
    holds the log.
    """
    for entry in entries:
        cmd = entry.get("command") or []
        if cmd[:2] == ["network", "requests"]:
            result = entry.get("result")
            if isinstance(result, dict) and isinstance(result.get("requests"), list):
                return result
    return None


def _final_status(net_result):
    requests = (net_result or {}).get("requests") or []
    documents = [r for r in requests if r.get("resourceType") == "Document"]
    if not documents:
        return None
    return documents[-1].get("status")


def probe_host(session, host, args):
    """Visit one host once. Returns a raw attempt dict (no decision yet)."""
    started = time.time()
    marker = f"bad_{int(time.time()*1000)}_{threading.get_ident()}"
    try:
        entries, err = _run_batch(session, host, args)
    except subprocess.TimeoutExpired:
        _reset_session(session, args)
        return _attempt("timeout", None, None, None, 0, time.time() - started,
                        "browser did not answer within the budget", marker)
    except (OSError, subprocess.SubprocessError) as exc:
        _reset_session(session, args)
        return _attempt("harness-error", None, None, None, 0, time.time() - started,
                        f"{type(exc).__name__}: {exc}"[:200], marker)

    if entries is None:
        _reset_session(session, args)
        return _attempt("harness-error", None, None, None, 0, time.time() - started,
                        err or "unparseable browser output", marker)

    open_entry = _entry(entries, "open")
    if open_entry is None or not open_entry.get("success"):
        message = (open_entry or {}).get("error") or "no navigation result"
        return _attempt(classify_error(message), None, None, None, 0,
                        time.time() - started, message[:200], marker)

    open_result = open_entry.get("result") or {}
    final_url = open_result.get("url")
    title = open_result.get("title")
    text_length = 0
    haystack = ""
    eval_entry = _entry(entries, "eval")
    if eval_entry and eval_entry.get("success"):
        payload = _parse_eval(eval_entry.get("result"))
        if payload:
            final_url = payload.get("u") or final_url
            title = payload.get("t") or title
            text_length = int(payload.get("n") or 0)
            haystack = (payload.get("h") or "").lower()
    status = _final_status(_requests_result(entries))
    outcome = classify_attempt(status, text_length, title, final_url, haystack, None)
    return {
        "outcome": outcome,
        "status": status,
        "final_url": final_url,
        "title": (title or "")[:300] or None,
        "text_length": text_length,
        "seconds": round(time.time() - started, 2),
        "error": None,
        "marker": marker,
    }


def _parse_eval(result):
    if not isinstance(result, dict):
        return None
    raw = result.get("result")
    if not isinstance(raw, str):
        return None
    try:
        return json.loads(raw)
    except ValueError:
        return None


def _attempt(outcome, status, final_url, title, text_length, seconds, error, marker):
    return {
        "outcome": outcome,
        "status": status,
        "final_url": final_url,
        "title": title,
        "text_length": text_length,
        "seconds": round(seconds, 2),
        "error": error,
        "marker": marker,
    }


def _reset_session(session, args):
    """Kill a wedged session so the next host starts clean."""
    try:
        subprocess.run(
            [args.agent_browser, "--session", session, "close"],
            capture_output=True, text=True, timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        pass


def canary_ok(session, args):
    """Prove the engine still works before believing a host is unresponsive."""
    spent = args.timeout_ms
    args.timeout_ms = min(spent, 15000)  # a canary must not cost a full budget
    try:
        attempt = probe_host(session, CANARY_HOST, args)
    finally:
        args.timeout_ms = spent
    return attempt["outcome"] == "content"


def probe_with_retries(session, host, args):
    """Probe a host, retry tentatively, and confirm real failures with a canary."""
    attempts = []
    for _ in range(max(1, args.attempts)):
        attempt = probe_host(session, host, args)
        attempts.append(attempt)
        if attempt["outcome"] in ("content", "blocked", "parked", "empty"):
            # A page answered — no need to retry, and no need for a canary.
            break
        time.sleep(args.retry_pause)

    decision = host_decision([a["outcome"] for a in attempts])
    if not is_alive_evidence(decision):
        # We are about to record a host as unresponsive. Make sure the engine
        # is not the thing that is unresponsive.
        if not canary_ok(session, args):
            decision = "harness-error"

    best = min(attempts, key=lambda a: OUTCOME_RANK.get(a["outcome"], 99))
    return {
        "decision": decision,
        "status": best.get("status"),
        "final_url": best.get("final_url"),
        "redirected": _redirected(host, best.get("final_url")),
        "title": best.get("title"),
        "text_length": int(best.get("text_length") or 0),
        "attempts": len(attempts),
        "seconds": round(sum(a["seconds"] for a in attempts), 2),
        "error": best.get("error"),
    }


def is_alive_evidence(decision):
    """True when the decision is a real page, so no canary is needed."""
    return decision in ("ok", "blocked", "parked", "empty")


def _redirected(host, final_url):
    if not final_url:
        return False
    try:
        final_host = urllib.parse.urlsplit(final_url).hostname or ""
    except ValueError:
        return False
    final_host = final_host.lower().lstrip(".")
    host = host.lower().lstrip(".")
    return final_host not in (host,)


# --------------------------------------------------------------------------- #
# Rounds.
# --------------------------------------------------------------------------- #


def environment(args):
    """Record the versions that produced the evidence."""
    versions = {"engine": ENGINE}
    for kind, argv in (("agent_browser", [args.agent_browser, "--version"]),):
        try:
            proc = subprocess.run(argv, capture_output=True, text=True, timeout=15)
            versions[kind] = (proc.stdout or proc.stderr).strip().splitlines()[0]
        except (OSError, subprocess.SubprocessError, IndexError):
            versions[kind] = None
    if args.lightpanda:
        binary = args.lightpanda
    else:
        binary = shutil.which("lightpanda")
    versions["lightpanda_path"] = binary
    if binary:
        try:
            proc = subprocess.run([binary, "version"], capture_output=True, text=True, timeout=15)
            versions["lightpanda"] = (proc.stdout or proc.stderr).strip().splitlines()[0]
        except (OSError, subprocess.SubprocessError, IndexError):
            versions["lightpanda"] = None
    else:
        versions["lightpanda"] = None
    return versions


def self_test(args):
    """Verify the engine and the decision path before a long run."""
    problems = []
    if shutil.which(args.agent_browser) is None and not os.path.exists(args.agent_browser):
        problems.append(f"{args.agent_browser} is not on PATH — install agent-browser")
    if not args.lightpanda and shutil.which("lightpanda") is None:
        problems.append("lightpanda is not on PATH — install it, or pass --lightpanda <path>")
    if args.lightpanda and not os.path.exists(args.lightpanda):
        problems.append(f"--lightpanda {args.lightpanda} does not exist")

    canaries = [
        ("example.com", True, "a page that certainly serves content must be readable"),
    ]
    session = "sweep-selftest"
    for host, expect_content, why in canaries:
        attempt = probe_host(session, host, args)
        if expect_content and attempt["outcome"] != "content":
            problems.append(
                f"{host} came back {attempt['outcome']!r} ({attempt.get('error')}), "
                f"expected content — {why}"
            )
    _reset_session(session, args)
    return problems


def run_round(args, categories, state, round_number):
    hosts = sorted(categories)
    if args.limit:
        hosts = hosts[: args.limit]

    problems = self_test(args)
    if problems:
        print("✗ browser self-test failed — aborting rather than reporting a catalog of guesses:",
              file=sys.stderr)
        for problem in problems:
            print(f"    {problem}", file=sys.stderr)
        return 1
    print(f"✓ browser self-test passed (engine={ENGINE})")

    versions = environment(args)
    print(f"  agent-browser {versions.get('agent_browser')}  ·  "
          f"lightpanda {versions.get('lightpanda')} ({versions.get('lightpanda_path')})")

    print(f"sweeping {len(hosts)} host(s) for round {round_number} "
          f"({args.workers} workers, {args.attempts} attempt(s), "
          f"{'aggressive' if args.aggressive else 'conservative'} mode)")
    started = time.time()

    # Resume: keep whatever a previous, incomplete run of this round already
    # judged. Re-running a host we have an answer for is wasted politeness.
    previous = {}
    for entry in state.get("rounds", []):
        if entry.get("round") == round_number:
            previous = dict(entry.get("results", {}))
    results = dict(previous)
    counts = {}
    for result in results.values():
        counts[result["decision"]] = counts.get(result["decision"], 0) + 1

    pending = [host for host in hosts if host not in results]
    if pending:
        print(f"  {len(results)} already done, {len(pending)} to go")

    sessions = queue.Queue()
    for i in range(max(1, args.workers)):
        sessions.put(f"sweep-{round_number}-{i}")

    lock = threading.Lock()
    done = [0]

    def work(host):
        session = sessions.get()
        try:
            result = probe_with_retries(session, host, args)
            time.sleep(args.delay)
            return result
        finally:
            sessions.put(session)

    try:
        with ThreadPoolExecutor(max_workers=max(1, args.workers)) as executor:
            futures = {executor.submit(work, host): host for host in pending}
            for future in as_completed(futures):
                host = futures[future]
                result = future.result()
                with lock:
                    results[host] = result
                    counts[result["decision"]] = counts.get(result["decision"], 0) + 1
                    done[0] += 1
                    n = done[0]
                if n % SAVE_EVERY == 0:
                    save_round(state, round_number, results, counts, complete=False,
                               elapsed_seconds=time.time() - started, versions=versions,
                               args=args)
                    save_state(state, args.state)
                if n % 100 == 0:
                    print(f"  {n}/{len(pending)}  " +
                          " ".join(f"{k}={counts[k]}" for k in sorted(counts)), flush=True)
    except KeyboardInterrupt:
        print(f"\n! interrupted after {done[0]} host(s); partial progress saved", file=sys.stderr)

    complete = len(results) == len(hosts)
    save_round(state, round_number, results, counts, complete=complete,
               elapsed_seconds=time.time() - started, versions=versions, args=args)
    save_state(state, args.state)

    print(f"\nround {round_number}: " +
          " ".join(f"{k}={counts.get(k, 0)}" for k in DECISIONS))
    print(f"✓ wrote {os.path.relpath(args.state, ROOT)} in {time.time() - started:.0f}s")
    if not complete:
        print(f"! round {round_number} was incomplete; run it again to finish", file=sys.stderr)
        return 1
    return 0


def save_round(state, round_number, results, counts, complete, elapsed_seconds, versions, args):
    entry = {
        "round": round_number,
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "complete": complete,
        "engine": ENGINE,
        "elapsed_seconds": round(elapsed_seconds, 2),
        "counts": counts,
        "results": results,
    }
    state.setdefault("config", {}).update({
        "engine": ENGINE,
        "aggressive": args.aggressive,
        "workers": args.workers,
        "attempts": args.attempts,
        "timeout_ms": args.timeout_ms,
        "user_agent": args.user_agent,
        "versions": versions,
    })
    state["rounds"] = [e for e in state.get("rounds", []) if e.get("round") != round_number] + [entry]
    return entry


# --------------------------------------------------------------------------- #
# Report.
# --------------------------------------------------------------------------- #


def write_markdown(state, categories, proposal, path=MARKDOWN, dead_state_path=DEAD_STATE,
                   aggressive=False, include_flaky=False):
    rounds = {entry["round"]: entry.get("counts", {}) for entry in state.get("rounds", [])}
    versions = (state.get("config", {}) or {}).get("versions", {})
    mode = "conservative (only a parked page is proposed)" if not aggressive else \
        "aggressive (empty and error-only hosts are proposed too)"
    if include_flaky:
        mode += ", including flaky environment failures"
    lines = [
        "# Live sweep",
        "",
        f"Generated: {date.today().isoformat()}",
        "",
        "Every catalog host visited with a real browser — "
        "[agent-browser](https://github.com/vercel-labs/agent-browser) driving "
        "[Lightpanda](https://lightpanda.io) (`--engine lightpanda`). The DNS "
        "sweep asks whether a name exists; this asks whether it still serves a "
        "page. A host is only *removable* when every complete round agrees.",
        "",
        f"- Engine: `{ENGINE}`  ·  agent-browser {versions.get('agent_browser')}  ·  "
        f"lightpanda {versions.get('lightpanda')}",
        f"- Mode: {mode}",
        "",
        "| Round | " + " | ".join(DECISIONS) + " |",
        "| ---: | " + " | ".join("---:" for _ in DECISIONS) + " |",
    ]
    for number in sorted(rounds):
        counts = rounds[number]
        lines.append(f"| {number} | " + " | ".join(str(counts.get(d, 0)) for d in DECISIONS) + " |")

    if proposal is None:
        lines += ["", "Only one complete round so far — a single round is a snapshot.", ""]
        _write(lines, path)
        return

    cross = dns_cross_check(state, proposal, dead_state_path)
    lines += [
        "",
        f"## Proposal — {len(proposal)} host(s) removable in every round",
        "",
        "This is a proposal, not a deletion. Applying it means removing the host "
        "from `seeds/categories.json` and recording why in `rules.json` → "
        "`drop.hosts`, then regenerating the catalog.",
        "",
        "| Category | Host | Decision |",
        "| :--- | :--- | :--- |",
    ]
    decisions = _per_host_decisions(state)
    for host in proposal:
        lines.append(f"| {categories.get(host, '?')} | `{host}` | {decisions.get(host, '?')} |")

    if cross["available"]:
        lines += [
            "",
            "### Cross-checked against the DNS sweep",
            "",
            f"- **{len(cross['dns_dead'])}** proposed host(s) the DNS sweep also called "
            "gone in both rounds — the safest removal.",
            f"- **{len(cross['conflicts'])}** proposed host(s) DNS still answers. These are "
            "the case that once nearly cost this catalog 181 real banks: read them before "
            "applying anything, because a reachable name that serves no page may be a "
            "non-web service (a bank's 3DS endpoint, a mail-only domain) that belongs here.",
            "",
        ]
        if cross["conflicts"]:
            lines.append("| Category | Host | Decision |")
            lines.append("| :--- | :--- | :--- |")
            for host in cross["conflicts"]:
                lines.append(f"| {categories.get(host, '?')} | `{host}` | {decisions.get(host, '?')} |")
            lines.append("")

    flaky = flaky_hosts(state)
    if flaky:
        lines += [
            "",
            f"## Review — {len(flaky)} host(s) this environment could not reach",
            "",
            "A certificate failure, a timeout or a resolver miss says *this "
            "network could not reach the host*, not that the host serves "
            "nothing — `youtube-nocookie.com` and `jsdelivr.net` land here on a "
            "bad afternoon. Kept out of the proposal on purpose. Name-death is "
            "the DNS sweep's job (`probe_dead.py`); run `--include-flaky` only "
            "if you have read these and still want them proposed.",
            "",
            "| Category | Host | Decision |",
            "| :--- | :--- | :--- |",
        ]
        for host in sorted(flaky):
            lines.append(f"| {categories.get(host, '?')} | `{host}` | {flaky[host]} |")
        lines.append("")

    _write(lines, path)


def _per_host_decisions(state):
    out = {}
    for entry in state.get("rounds", []):
        for host, result in entry.get("results", {}).items():
            out.setdefault(host, result.get("decision"))
    return out


def _write(lines, path):
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))


# --------------------------------------------------------------------------- #
# Apply.
# --------------------------------------------------------------------------- #


def apply_proposal(state, categories_path, rules_path, aggressive, dry_run=True,
                   dead_state_path=DEAD_STATE, include_flaky=False):
    """Remove the proposal from the seeds and record why in `drop.hosts`.

    Mirrors `probe-dead.py`: the host leaves `seeds/categories.json` (so
    `generate.py` stops emitting it) and lands in `rules.json` → `drop.hosts`
    with the reason that removed it, which stops `harvest.py` importing it
    again. Idempotent.
    """
    proposal = build_proposal(state, aggressive, include_flaky)
    if proposal is None:
        print("✗ no proposal yet — run --round 1 and --round 2 first", file=sys.stderr)
        return None

    categories = load_json(categories_path)
    rules = load_json(rules_path)
    drops = rules.setdefault("drop", {}).setdefault("hosts", {})

    decisions = _per_host_decisions(state)
    dates = sorted(
        entry["generated"][:10]
        for entry in state.get("rounds", [])
        if entry.get("complete")
    )
    when = " and ".join(sorted(set(dates)))

    removed, already_gone, recorded = [], [], []
    for host in proposal:
        category = categories.get(host)
        # Read the category before deleting the entry: the reason records which
        # category the host was in, and asking after the delete is how a bug
        # wrote "?" for every host it removed once.
        if host in categories:
            del categories[host]
            removed.append(host)
        else:
            already_gone.append(host)
        if category:
            reason = (f"no usable page in {len(dates)} live sweep round(s) "
                      f"({decisions.get(host, '?')}) on {when}; {category}")
        elif host in drops:
            reason = drops[host]
        else:
            reason = (f"no usable page in {len(dates)} live sweep round(s) "
                      f"({decisions.get(host, '?')}) on {when}; not in the seeds")
        drops[host] = reason
        recorded.append(host)

    print(f"proposal: {len(proposal)} host(s) removable in every round")
    print(f"  in the seeds, to remove: {len(removed)}")
    print(f"  already absent from the seeds: {len(already_gone)}")
    print(f"  drop.hosts entries written: {len(recorded)}")

    if dry_run:
        print("\ndry run — nothing written. Re-run with --apply to change the files.")
        return {"removed": removed, "already_gone": already_gone, "proposal": proposal}

    with open(categories_path, "w", encoding="utf-8") as handle:
        json.dump({host: categories[host] for host in sorted(categories)}, handle,
                  ensure_ascii=False, indent=2)
        handle.write("\n")
    rules["drop"]["hosts"] = {host: drops[host] for host in sorted(drops)}
    with open(rules_path, "w", encoding="utf-8") as handle:
        json.dump(rules, handle, ensure_ascii=False, indent=2)
        handle.write("\n")

    print(f"\n✓ {os.path.relpath(categories_path, ROOT)}: {len(categories)} host(s) remain")
    print(f"✓ {os.path.relpath(rules_path, ROOT)}: {len(drops)} drop.hosts entr(ies)")
    print("  now run: scripts/catalog/generate.py && scripts/catalog/build-catalog-docs.py && ./test/test.sh")
    return {"removed": removed, "already_gone": already_gone, "proposal": proposal}


def markdown_path(args):
    if args.state == STATE:
        return MARKDOWN
    return os.path.splitext(args.state)[0] + ".md"


# --------------------------------------------------------------------------- #
# Entry point.
# --------------------------------------------------------------------------- #


def build_parser():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--round", type=int, choices=(1, 2), help="run a sweep round")
    parser.add_argument("--limit", type=int, default=0, help="sweep only the first N hosts; 0 means all")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--attempts", type=int, default=2)
    parser.add_argument("--timeout-ms", type=int, default=20000)
    parser.add_argument("--grace-seconds", type=float, default=8.0,
                        help="extra wall-clock before the subprocess is killed")
    parser.add_argument("--retry-pause", type=float, default=0.5)
    parser.add_argument("--delay", type=float, default=0.15, help="pause between hosts per worker")
    parser.add_argument("--aggressive", action="store_true",
                        help="also propose hosts that answered with no page "
                             "(an empty 200, a 404/5xx, a refusal) — read them first")
    parser.add_argument("--include-flaky", action="store_true",
                        help="also propose hosts this environment could not reach "
                             "(tls-error/timeout/dns-error); read them first")
    parser.add_argument("--agent-browser", default=AGENT_BROWSER)
    parser.add_argument("--lightpanda", default="", help="path to the lightpanda binary")
    parser.add_argument("--user-agent", default=USER_AGENT)
    parser.add_argument("--categories", default=CATEGORIES)
    parser.add_argument("--rules", default=RULES)
    parser.add_argument("--state", default=STATE)
    parser.add_argument("--dead-state", default=DEAD_STATE,
                        help="DNS sweep evidence to cross-check the proposal against")
    parser.add_argument("--summary", action="store_true", help="print counts and the proposal, do not sweep")
    parser.add_argument("--apply", action="store_true",
                        help="remove the proposal from the seeds and record it in drop.hosts")
    parser.add_argument("--self-test", action="store_true", help="check the engine and exit")
    return parser


def main(argv):
    parser = build_parser()
    args = parser.parse_args(argv[1:])

    if args.state != STATE:
        os.makedirs(os.path.dirname(args.state), exist_ok=True)

    if args.self_test:
        problems = self_test(args)
        if problems:
            for problem in problems:
                print(f"✗ {problem}", file=sys.stderr)
            return 1
        print(f"✓ engine={ENGINE} answered the canary")
        return 0

    needs_state = args.round == 2 or args.summary or args.apply
    if needs_state and not os.path.exists(args.state):
        print(f"✗ no sweep state at {os.path.relpath(args.state, ROOT)}; run --round 1 first",
              file=sys.stderr)
        return 1
    if os.path.exists(args.state):
        state = load_json(args.state)
    else:
        state = {"schema": 1, "generated": date.today().isoformat()}

    categories = load_json(args.categories)

    if args.round in (1, 2):
        return run_round(args, categories, state, args.round)

    if args.apply:
        result = apply_proposal(state, args.categories, args.rules, args.aggressive, dry_run=False,
                                include_flaky=args.include_flaky)
        return 0 if result else 1

    if args.summary:
        rounds = {entry["round"]: entry for entry in state.get("rounds", [])}
        if not rounds:
            print("no rounds recorded yet")
            return 1
        for number in sorted(rounds):
            counts = rounds[number].get("counts", {})
            print(f"round {number}: " + " ".join(f"{k}={counts.get(k, 0)}" for k in DECISIONS)
                  + f"  ({'complete' if rounds[number].get('complete') else 'INCOMPLETE'})")
        proposal = build_proposal(state, args.aggressive, args.include_flaky)
        if proposal is None:
            print("\nonly one complete round so far; there is no proposal yet")
            write_markdown(state, categories, None, markdown_path(args),
                           args.dead_state, args.aggressive, args.include_flaky)
            return 0
        write_markdown(state, categories, proposal, markdown_path(args),
                       args.dead_state, args.aggressive, args.include_flaky)
        cross = dns_cross_check(state, proposal, args.dead_state)
        print(f"\nproposal: {len(proposal)} host(s) removable in every round")
        if cross["available"]:
            print(f"  {len(cross['dns_dead'])} also dead in the DNS sweep (safest)")
            print(f"  {len(cross['conflicts'])} DNS still answers — read before applying")
        flaky = flaky_hosts(state)
        if flaky:
            print(f"  {len(flaky)} host(s) unreachable from this environment — review only")
        for host in proposal:
            print(f"  {categories.get(host, '?'):12} {decisions_for(state, host)}  {host}")
        print(f"\n✓ wrote {os.path.relpath(markdown_path(args), ROOT)}")
        return 0

    result = apply_proposal(state, args.categories, args.rules, args.aggressive, dry_run=True,
                            include_flaky=args.include_flaky)
    return 0 if result else 1


def decisions_for(state, host):
    for entry in sorted(state.get("rounds", []), key=lambda e: e.get("round", 0)):
        result = entry.get("results", {}).get(host)
        if result:
            return result.get("decision", "?")
    return "?"


if __name__ == "__main__":
    sys.exit(main(sys.argv))
