#!/usr/bin/env python3
"""Verify catalog hosts are still registered to the same owner.

    python3 scripts/catalog/verify-registrations.py --self-test
    python3 scripts/catalog/verify-registrations.py --round 1 [--limit 200] [--traceroute]
    python3 scripts/catalog/verify-registrations.py --round 2        # >= 10 minutes later
    python3 scripts/catalog/verify-registrations.py --summary
    python3 scripts/catalog/verify-registrations.py --apply         # only after reading it

DNS and a live browser can both say a name is "alive" while it has quietly
changed hands: a lapsed domain is re-registered by someone else and inherits
the category the previous owner had. This script checks the *registration*
itself, three ways:

    1. RDAP (RFC 7480-7484) for the domain, via the IANA bootstrap registry
       (RFC 9224) plus a bundled, verified supplement for country-code
       registries IANA omits, plus convention probing as a last resort.
    2. Port-43 WHOIS fallback for registries with no RDAP (DENIC for .de,
       TRABIS for .tr, and anything IANA refers to).
    3. IP RDAP for the host's address block (ARIN/RIPE/...), so the network
       owner is on record alongside the name owner.

A host is only proposed when two independent rounds agree, and traceroute is
run as a reachability diagnostic (bounded, opt-in) rather than as a gate.

The evidence written to `evidence/registration-verify.json` keeps one verdict
per host per round — `{"host": "registered"}` — not the RDAP/WHOIS bodies that
produced it. A verdict is what a review needs; the raw records run to tens of
megabytes across two rounds and say nothing the decision does not. Re-run a
round to see the underlying record for a host again.

Standard library only. It needs the network, so it stays out of test/test.sh;
its parsing/decision tables are checked there offline.
"""

import argparse
import ipaddress
import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CATEGORIES = os.path.join(ROOT, "seeds", "categories.json")
RULES = os.path.join(ROOT, "rules.json")
REFERENCE = os.path.join(ROOT, "reference", "rdap")
EVIDENCE = os.path.join(ROOT, "evidence")
STATE = os.path.join(EVIDENCE, "registration-verify.json")
MARKDOWN = os.path.join(EVIDENCE, "registration-verify.md")

USER_AGENT = "net-traffic-control-catalog/1.0 (registration verify)"
RDAP_TIMEOUT = 8
WHOIS_TIMEOUT = 10
DISCOVER_ENABLED = False
TRACEROUTE_MAX_HOPS = 8
SAVE_EVERY = 100
MIN_GAP_MINUTES = 10
CANARY_HOST = "google.com"
WORKERS = 8


# ---------- reference data ----------

_IANA_DNS = None
_CC_SUPP = None
_UNSUPPORTED = None
_IPV4 = None
_IPV6 = None
_DISCOVERED = {}


def load_reference():
    global _IANA_DNS, _CC_SUPP, _UNSUPPORTED, _IPV4, _IPV6
    if _IANA_DNS is not None:
        return
    with open(os.path.join(REFERENCE, "rdap-dns.json"), encoding="utf-8") as f:
        dns = json.load(f)
    with open(os.path.join(REFERENCE, "rdap-cc.json"), encoding="utf-8") as f:
        cc = json.load(f)
    with open(os.path.join(REFERENCE, "rdap-ipv4.json"), encoding="utf-8") as f:
        v4 = json.load(f)
    with open(os.path.join(REFERENCE, "rdap-ipv6.json"), encoding="utf-8") as f:
        v6 = json.load(f)

    _IANA_DNS = {}
    for entry in dns.get("services", []):
        tlds, urls = entry[0], entry[1]
        for tld in tlds:
            if urls:
                _IANA_DNS[tld.lower()] = urls

    _CC_SUPP = {}
    for tld, url in (cc.get("tlds") or {}).items():
        _CC_SUPP[tld.lower()] = url

    _UNSUPPORTED = {}
    for tld, info in (cc.get("unsupported") or {}).items():
        _UNSUPPORTED[tld.lower()] = info

    def build_ip(table):
        out = []
        for entry in table.get("services", []):
            blocks, urls = entry[0], entry[1]
            if not urls:
                continue
            for cidr in blocks:
                try:
                    net = ipaddress.ip_network(cidr, strict=False)
                except ValueError:
                    continue
                out.append((net, urls))
        return out

    _IPV4 = build_ip(v4)
    _IPV6 = build_ip(v6)


def tld_of(domain):
    domain = domain.strip().strip(".")
    if not domain or "." not in domain:
        return ""
    return domain.rsplit(".", 1)[-1].lower()


DISCOVERY_PATTERNS = [
    "https://rdap.nic.{tld}/",
    "https://rdap.{tld}/",
    "https://rdap.registry.{tld}/",
    "https://whois.nic.{tld}/rdap/",
]
DISCOVERY_SAMPLES = ["nic", "www", ""]
SIBLING_HOSTS = {
    "rdap.verisign.com": "https://tld-rdap.verisign.com/",
    "tld-rdap.verisign.com": "https://rdap.verisign.com/",
}


def rdap_endpoint_for_domain(domain):
    """Return (source, [urls]) or (None, reason)."""
    load_reference()
    tld = tld_of(domain)
    if not tld:
        return ("none", [], "no-tld")
    if tld in _UNSUPPORTED:
        return ("unsupported", [], _UNSUPPORTED[tld].get("reason", "policy"))
    if tld in _IANA_DNS:
        urls = list(_IANA_DNS[tld])
        # sibling fallback
        host = _host_of(urls[0]) if urls else ""
        if host in SIBLING_HOSTS:
            sib = SIBLING_HOSTS[host]
            if sib not in urls:
                urls = urls + [sib]
        return ("iana", urls, None)
    if tld in _CC_SUPP:
        return ("supplement", [_CC_SUPP[tld]], None)
    if tld in _DISCOVERED:
        return ("discovered", [_DISCOVERED[tld]], None)
    return ("discover", [], None)


def _host_of(url):
    try:
        return urllib.parse.urlparse(url).hostname or ""
    except Exception:
        return ""


def rdap_endpoint_for_ip(ip):
    load_reference()
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return None
    table = _IPV4 if addr.version == 4 else _IPV6
    best = None
    for net, urls in table:
        if addr in net:
            if best is None or net.prefixlen > best[0]:
                best = (net.prefixlen, urls)
    if best is None:
        return None
    return best[1]


# ---------- HTTP helpers ----------

def _http_get(url, timeout=RDAP_TIMEOUT, accept="application/rdap+json"):
    req = urllib.request.Request(url, headers={
        "Accept": accept,
        "User-Agent": USER_AGENT,
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read()
            ctype = (resp.headers.get("Content-Type") or "") if resp.headers else ""
            return resp.status, data, resp, ctype
    except urllib.error.HTTPError as e:
        try:
            data = e.read()
        except Exception:
            data = b""
        ctype = (e.headers.get("Content-Type") or "") if e.headers else ""
        return e.code, data, None, ctype
    except Exception as e:
        return None, None, str(e), ""


def _follow_redirects(url, hops=3, visited=None):
    if visited is None:
        visited = set()
    if url in visited:
        return None, None, "redirect-ring"
    visited = visited | {url}
    status, data, resp, ctype = _http_get(url)
    if status is None:
        return None, None, data, ""  # data holds error string
    if status in (301, 302, 303, 307, 308):
        if hops <= 0:
            return status, data, "too-many-redirects", ctype
        loc = None
        if resp is not None:
            loc = resp.headers.get("Location")
        if not loc:
            return status, data, "no-location", ctype
        target = urllib.parse.urljoin(url, loc)
        parsed = urllib.parse.urlparse(target)
        if parsed.scheme != "https" or not parsed.hostname:
            return status, data, "bad-redirect", ctype
        return _follow_redirects(target, hops - 1, visited)
    return status, data, None, ctype


def _rdap_404_is_real(data, ctype):
    """Is this 404 a real RDAP "no such domain", or a broken endpoint?

    RDAP servers answer a missing name with an `application/rdap+json` body
    (Verisign sends an empty one with that type). Some registries instead run a
    web server that returns an HTML error page for *every* lookup — including
    names that are plainly registered — which would otherwise read as
    "available" and get a live host deleted. Only the RDAP media type, or a
    parseable RDAP JSON error body, counts as a genuine negative.
    """
    c = (ctype or "").lower()
    if "rdap+json" in c or "application/json" in c:
        return True
    if data:
        try:
            obj = json.loads(data.decode("utf-8", "replace"))
        except (ValueError, AttributeError):
            return False
        if isinstance(obj, dict) and ("errorCode" in obj or "rdapConformance" in obj):
            return True
    return False


# ---------- RDAP parsing ----------

def _iso_date(text):
    if not text:
        return None
    text = text.strip()
    if text.endswith("Z"):
        text2 = text
    else:
        text2 = text + "Z"
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%d"):
        try:
            if fmt == "%Y-%m-%d":
                return datetime.strptime(text[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
            return datetime.strptime(text2, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    # fallback: fromisoformat
    try:
        d = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        return d
    except ValueError:
        return None


def parse_rdap(data, source_host, is_ip=False):
    try:
        obj = json.loads(data)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(obj, dict):
        return None

    events = {}
    for ev in (obj.get("events") or []):
        if not isinstance(ev, dict):
            continue
        action = ev.get("eventAction")
        date = _iso_date(ev.get("eventDate"))
        if action and date and action not in events:
            events[action] = date

    nameservers = []
    seen_ns = set()
    for ns in (obj.get("nameservers") or []):
        if isinstance(ns, dict):
            name = ns.get("ldhName")
        else:
            name = ns
        if name and name.lower() not in seen_ns:
            seen_ns.add(name.lower())
            nameservers.append(name)

    registrar = None
    for ent in (obj.get("entities") or []):
        if not isinstance(ent, dict):
            continue
        roles = ent.get("roles") or []
        if "registrar" not in roles:
            continue
        # jCard fn
        vcard = ent.get("vcardArray")
        if isinstance(vcard, list) and len(vcard) == 2 and isinstance(vcard[1], list):
            for prop in vcard[1]:
                if isinstance(prop, list) and len(prop) >= 4 and prop[0] == "fn":
                    val = prop[3]
                    if isinstance(val, str) and val.strip():
                        registrar = val.strip()
                        break
        if registrar:
            break
        # fallback: handle
        if not registrar and ent.get("handle"):
            registrar = ent.get("handle")

    status = obj.get("status") or []
    if not isinstance(status, list):
        status = [str(status)]

    dnssec = None
    sdns = obj.get("secureDNS")
    if isinstance(sdns, dict):
        ds = sdns.get("delegationSigned")
        if isinstance(ds, bool):
            dnssec = ds

    network = None
    if is_ip:
        start = obj.get("startAddress")
        end = obj.get("endAddress")
        if start or end:
            rng = start if start == end else f"{start} – {end}"
            network = {
                "range": rng,
                "name": obj.get("name"),
                "type": obj.get("type"),
                "country": obj.get("country"),
            }

    return {
        "source_host": source_host,
        "ldh_name": obj.get("ldhName"),
        "registrar": registrar,
        "created": events.get("registration"),
        "expires": events.get("expiration"),
        "last_changed": events.get("last changed") or events.get("last update of RDAP database"),
        "nameservers": nameservers,
        "status": status,
        "dnssec_signed": dnssec,
        "is_ip": is_ip,
        "network": network,
        "raw_events": {k: v.isoformat() for k, v in events.items()},
    }


def rdap_lookup_domain(name):
    """Return (outcome, record_or_None, detail)."""
    load_reference()
    tld = tld_of(name)
    # try endpoint resolution
    source, urls, reason = rdap_endpoint_for_domain(name)
    if source == "unsupported":
        # try WHOIS later; return unsupported marker
        return ("unsupported", None, {"reason": reason, "tld": tld})
    if source == "discover":
        # probe conventions
        found = _discover(tld, name)
        if found:
            _DISCOVERED[tld] = found
            urls = [found]
            source = "discovered"
        else:
            return ("no-server", None, {"tld": tld})

    # sibling hosts
    all_urls = list(urls)
    if all_urls:
        host = _host_of(all_urls[0])
        if host in SIBLING_HOSTS:
            sib = SIBLING_HOSTS[host]
            if sib not in all_urls:
                all_urls.append(sib)

    # reduction candidates
    candidates = reduction_candidates(name)
    saw_real_404 = False
    hard_error = None
    for base in all_urls:
        for cand in candidates:
            path = "domain/" + urllib.parse.quote(cand, safe="")
            url = base.rstrip("/") + "/" + path
            # ensure trailing slash handling: base already ends with /
            if not base.endswith("/"):
                url = base + "/" + path
            status, data, err, ctype = _follow_redirects(url)
            if status is None:
                hard_error = err
                break
            if status == 404:
                if _rdap_404_is_real(data, ctype):
                    saw_real_404 = True
                    continue
                # a 404 that is not RDAP means this endpoint does not speak
                # RDAP for this name — do not read it as "available"
                hard_error = "not-rdap"
                break
            if 200 <= status < 300:
                rec = parse_rdap(data, _host_of(base) or base, is_ip=False)
                if rec is not None:
                    rec["rdap_source"] = source
                    return ("ok", rec, {"status": status, "source": source})
                hard_error = "malformed"
                break
            # other status: this base cannot answer, but a mirror may
            hard_error = f"http-{status}"
            break
    # A genuine RDAP negative from any mirror is the registry saying the name is
    # not registered, and outranks a sibling mirror's transport error. Only with
    # no such negative do we fall back to "we could not tell".
    if saw_real_404:
        return ("notfound", None, {"candidates": candidates})
    if hard_error:
        # try discovery as fallback before giving up
        if source != "discovered":
            found = _discover(tld, name)
            if found:
                _DISCOVERED[tld] = found
                # one attempt
                url = found.rstrip("/") + "/domain/" + urllib.parse.quote(name, safe="")
                status, data, err, ctype = _follow_redirects(url)
                if status is not None and 200 <= status < 300:
                    rec = parse_rdap(data, _host_of(found), is_ip=False)
                    if rec is not None:
                        rec["rdap_source"] = "discovered"
                        return ("ok", rec, {"status": status, "source": "discovered"})
        return ("unreachable", None, {"error": hard_error})
    return ("unreachable", None, {"error": "unknown"})


def _discover(tld, name):
    if not DISCOVER_ENABLED:
        return None
    if not tld:
        return None
    for pattern in DISCOVERY_PATTERNS:
        base = pattern.replace("{tld}", tld)
        if not base.startswith("https://"):
            continue
        for sample in DISCOVERY_SAMPLES:
            cand = (sample + "." + tld) if sample else tld
            # probe a known sample domain
            probe_name = cand if sample else name
            url = base.rstrip("/") + "/domain/" + urllib.parse.quote(probe_name, safe="")
            status, data, err, ctype = _follow_redirects(url)
            if status is None or not (200 <= status < 300):
                continue
            rec = parse_rdap(data, _host_of(base), is_ip=False)
            if rec is not None and (rec.get("ldh_name") or rec.get("registrar") or rec.get("nameservers")):
                return base
    return None


def reduction_candidates(name):
    cleaned = name.strip().lower().strip(".")
    if not cleaned:
        return [name]
    try:
        ipaddress.ip_address(cleaned)
        return [cleaned]
    except ValueError:
        pass
    labels = [x for x in cleaned.split(".") if x]
    cands = [labels and ".".join(labels) or cleaned]
    while len(labels) > 2 and len(cands) < 5:
        labels.pop(0)
        cands.append(".".join(labels))
    return cands


# ---------- WHOIS ----------

_WHOIS_SERVER_CACHE = {}

def whois_server_for_tld(tld):
    """IANA referral."""
    if not tld:
        return None
    if tld in _WHOIS_SERVER_CACHE:
        return _WHOIS_SERVER_CACHE[tld]
    text = _whois_query("whois.iana.org", tld, timeout=10)
    if not text:
        return None
    for line in text.splitlines():
        low = line.lower().strip()
        if low.startswith("whois:") or low.startswith("whois server:"):
            parts = line.split(":", 1)
            if len(parts) == 2:
                val = parts[1].strip()
                if val:
                    _WHOIS_SERVER_CACHE[tld] = val
                    return val
    _WHOIS_SERVER_CACHE[tld] = None
    return None


def _whois_query(server, query, timeout=WHOIS_TIMEOUT):
    try:
        sock = socket.create_connection((server, 43), timeout=timeout)
        sock.settimeout(timeout)
        sock.sendall((query + "\r\n").encode("utf-8", "replace"))
        data = b""
        while True:
            try:
                chunk = sock.recv(4096)
            except socket.timeout:
                break
            if not chunk:
                break
            data += chunk
        sock.close()
        return data.decode("utf-8", "replace")
    except Exception:
        return None


def whois_lookup(domain):
    tld = tld_of(domain)
    # DENIC special
    if tld == "de":
        text = _whois_query("whois.denic.de", domain)
        if text is None:
            return {"error": "unreachable", "source": "denic"}
        res = {"source": "denic", "raw_excerpt": text[:500]}
        status = None
        changed = None
        for line in text.splitlines():
            low = line.lower().strip()
            if low.startswith("status:"):
                status = line.split(":", 1)[1].strip()
            elif low.startswith("changed:"):
                changed = _iso_date(line.split(":", 1)[1].strip())
        res["status"] = status
        res["changed"] = changed
        if status and status.lower() == "free":
            res["verdict"] = "gone"
        elif status and status.lower() == "connect":
            res["verdict"] = "registered"
        else:
            res["verdict"] = "unknown"
        return res

    if tld == "tr":
        text = _whois_query("whois.trabis.gov.tr", domain)
        if text is None:
            return {"error": "unreachable", "source": "trabis"}
        res = {"source": "trabis", "raw_excerpt": text[:800]}
        status = None
        registrar = None
        for line in text.splitlines():
            low = line.lower().strip()
            if "domain status:" in low:
                status = line.split(":", 1)[1].strip()
            elif "organization name" in low or "registrar" in low:
                if registrar is None and ":" in line:
                    registrar = line.split(":", 1)[1].strip()
        res["status"] = status
        res["registrar"] = registrar
        if status:
            s = status.lower()
            if "active" in s:
                res["verdict"] = "registered"
            elif "frozen" in s or "suspended" in s:
                res["verdict"] = "review"
            else:
                res["verdict"] = "unknown"
        else:
            res["verdict"] = "unknown"
        return res

    # generic: IANA referral
    server = whois_server_for_tld(tld)
    if not server:
        return {"error": "no-server", "source": "iana"}
    text = _whois_query(server, domain)
    if text is None:
        return {"error": "unreachable", "source": server}
    res = {"source": server, "raw_excerpt": text[:800]}
    created = expires = updated = registrar = status = None
    for line in text.splitlines():
        low = line.lower().strip()
        if "creation date" in low or "created:" in low or low.startswith("created "):
            if ":" in line:
                created = _iso_date(line.split(":", 1)[1].strip())
        elif "expiry" in low or "expiration" in low or "expires" in low:
            if ":" in line:
                expires = _iso_date(line.split(":", 1)[1].strip())
        elif "updated" in low or "last updated" in low or "changed" in low:
            if ":" in line:
                updated = _iso_date(line.split(":", 1)[1].strip())
        elif "registrar:" in low:
            registrar = line.split(":", 1)[1].strip() if ":" in line else registrar
        elif "domain status" in low or "status:" in low:
            if status is None and ":" in line:
                status = line.split(":", 1)[1].strip()
    res["created"] = created
    res["expires"] = expires
    res["updated"] = updated
    res["registrar"] = registrar
    res["status"] = status
    if expires is not None and expires < datetime.now(timezone.utc):
        res["verdict"] = "expired"
    elif status and ("pendingdelete" in status.lower().replace(" ", "") or "redemption" in status.lower()):
        res["verdict"] = "gone"
    else:
        res["verdict"] = "registered" if (created or registrar or status) else "unknown"
    return res


# ---------- IP RDAP ----------

def ip_rdap_lookup(ip):
    load_reference()
    urls = rdap_endpoint_for_ip(ip)
    if not urls:
        return {"error": "no-server", "ip": ip}
    base = urls[0]
    url = base.rstrip("/") + "/ip/" + urllib.parse.quote(ip, safe="")
    status, data, err, ctype = _follow_redirects(url)
    if status is None:
        return {"error": f"unreachable: {err}", "ip": ip}
    if status == 404:
        if _rdap_404_is_real(data, ctype):
            return {"error": "notfound", "ip": ip}
        return {"error": "not-rdap", "ip": ip}
    if not (200 <= status < 300):
        return {"error": f"http-{status}", "ip": ip}
    rec = parse_rdap(data, _host_of(base), is_ip=True)
    if rec is None:
        return {"error": "malformed", "ip": ip}
    rec["rdap_source"] = "ip"
    return rec


def resolve_ip(host):
    try:
        infos = socket.getaddrinfo(host, None, socket.AF_INET)
    except socket.gaierror:
        return None
    for info in infos:
        addr = info[4][0]
        if addr:
            return addr
    return None


# ---------- traceroute ----------

def run_traceroute(host, max_hops=TRACEROUTE_MAX_HOPS):
    try:
        proc = subprocess.run(
            ["traceroute", "-m", str(max_hops), "-w", "1", "-q", "1", host],
            capture_output=True, text=True, timeout=max_hops * 3 + 10,
        )
        out = proc.stdout or ""
    except FileNotFoundError:
        return {"error": "traceroute-not-installed"}
    except subprocess.TimeoutExpired:
        return {"error": "timeout"}
    except Exception as e:
        return {"error": str(e)}
    hops = 0
    last_hop = None
    reached = False
    host_ip = None
    try:
        # first line: traceroute to host (IP), ...
        first = out.splitlines()[0] if out.splitlines() else ""
        if "(" in first and ")" in first:
            host_ip = first.split("(")[1].split(")")[0]
    except Exception:
        pass
    for line in out.splitlines()[1:]:
        line = line.strip()
        if not line:
            continue
        # hop line starts with a number
        parts = line.split()
        if not parts or not parts[0].isdigit():
            continue
        hops = int(parts[0])
        # check if any token is the host or its ip
        if host_ip and host_ip in line:
            reached = True
        if host.lower() in line.lower():
            reached = True
        # last hop with a response
        if "*" not in line.split(host, 1)[-1] if False else True:
            last_hop = line
    # reached if last hop line contains host ip
    if not reached and host_ip:
        # check last non-empty hop line
        lines = [l for l in out.splitlines()[1:] if l.strip()]
        if lines:
            reached = host_ip in lines[-1]
    return {"hops": hops, "last_hop": last_hop, "reached": reached, "raw": out[:2000]}


# ---------- decision ----------

def now_utc():
    return datetime.now(timezone.utc)


def decide(result, now=None):
    """Classify a host's registration into gone/expired/registered/... .

    This is the final say, so it is deliberately conservative: a host that still
    resolves in DNS is never called `gone` — the name is in use even when a
    registry's status or a half-working RDAP endpoint suggests otherwise.
    """
    verdict = _decide_core(result, now)
    dns = result.get("dns") or {}
    if verdict in ("gone", "expired") and dns.get("resolves"):
        return "review"
    return verdict


def _decide_core(result, now=None):
    if now is None:
        now = now_utc()
    rdap = result.get("rdap")
    whois = result.get("whois")
    # gone signals from RDAP
    if isinstance(rdap, dict) and "error" not in rdap and rdap.get("rdap_source") != "ip":
        status = [str(s).lower() for s in (rdap.get("status") or [])]
        status_flat = " ".join(status).replace(" ", "")
        # A name being *released* is gone; one that merely is not *working* is
        # still registered to its owner, so it is a review, not a removal.
        if "pendingdelete" in status_flat or "redemptionperiod" in status_flat:
            return "gone"
        if any(k in status_flat for k in ("clienthold", "serverhold", "inactive")):
            return "review"
        expires = rdap.get("expires")
        if isinstance(expires, datetime) and expires < now:
            return "expired"
        created = rdap.get("created")
        if isinstance(created, datetime):
            age_days = (now - created).days
            if 0 <= age_days < 90:
                return "recently_registered"
        if rdap.get("_outcome") == "notfound":
            return "gone"
        if rdap.get("_outcome") == "ok":
            return "registered"
    if isinstance(rdap, dict) and rdap.get("_outcome") == "notfound":
        return "gone"
    # WHOIS
    if isinstance(whois, dict) and "error" not in whois:
        # DENIC
        if whois.get("source") == "denic":
            st = (whois.get("status") or "").lower()
            if st == "free":
                return "gone"
            if st == "connect":
                return "registered"
        # TRABIS
        if whois.get("source") == "trabis":
            st = (whois.get("status") or "").lower()
            if "frozen" in st or "suspended" in st:
                return "review"
            if "active" in st:
                return "registered"
        # generic
        expires = whois.get("expires")
        if isinstance(expires, datetime) and expires < now:
            return "expired"
        st = (whois.get("status") or "")
        if st and ("pendingdelete" in st.lower().replace(" ", "") or "redemption" in st.lower()):
            return "gone"
        if whois.get("created") or whois.get("registrar") or whois.get("status"):
            return "registered"
    # unsupported
    if isinstance(rdap, dict) and rdap.get("_outcome") == "unsupported":
        return "unsupported"
    if isinstance(rdap, str) and rdap == "unsupported":
        return "unsupported"
    # unreachable / unknown
    if isinstance(rdap, dict) and rdap.get("_outcome") in ("unreachable", "no-server"):
        return "unknown"
    if isinstance(rdap, dict) and "error" in rdap and rdap.get("error", "").startswith("unreachable"):
        return "unknown"
    # if rdap is a failure string
    if isinstance(rdap, str):
        if rdap in ("unreachable", "no-server", "unknown"):
            return "unknown"
        if rdap == "unsupported":
            return "unsupported"
    return "unknown"


def host_result_to_decision(r):
    return decide(r)


# ---------- canary ----------

def canary():
    # RDAP google.com must return a record
    outcome, rec, detail = rdap_lookup_domain(CANARY_HOST)
    if outcome != "ok" or not rec:
        return False, f"rdap canary failed: {outcome} {detail}"
    # WHOIS google.com must parse something
    w = whois_lookup(CANARY_HOST)
    if not isinstance(w, dict) or w.get("error"):
        # whois may be unavailable; not fatal for canary? require rdap only
        pass
    # IP RDAP 8.8.8.8
    ipr = ip_rdap_lookup("8.8.8.8")
    if isinstance(ipr, dict) and "error" in ipr and ipr["error"] not in ("", None):
        # ip rdap failure is non-fatal for canary? require it
        return False, f"ip-rdap canary failed: {ipr.get('error')}"
    return True, "ok"


# ---------- round runner ----------

def process_host(host, do_traceroute=False, flagged=False):
    res = {"host": host}
    outcome, rec, detail = rdap_lookup_domain(host)
    if outcome == "ok":
        rdap = rec
        rdap["_outcome"] = "ok"
    else:
        rdap = {"_outcome": outcome, "_detail": detail}
    res["rdap"] = rdap

    # whois: only if rdap didn't give a clean registered record
    rdap_ok = isinstance(rdap, dict) and rdap.get("_outcome") == "ok"
    if rdap_ok:
        res["whois"] = {"skipped": "rdap-ok"}
    else:
        res["whois"] = whois_lookup(host)

    # IP RDAP
    ip = resolve_ip(host)
    if ip:
        res["ip"] = ip
        res["ip_rdap"] = ip_rdap_lookup(ip)
    else:
        res["ip"] = None
        res["ip_rdap"] = {"error": "no-a-record"}

    # A name that answers in DNS is in use, whatever the registry says.
    res["dns"] = {"resolves": ip is not None, "ip": ip}
    res["decision"] = decide(res)

    if do_traceroute and (flagged or do_traceroute == "all"):
        res["traceroute"] = run_traceroute(host)
    else:
        res["traceroute"] = {"skipped": True}

    return res


def run_round(round_no, limit=None, workers=WORKERS, do_traceroute=False, flagged=None):
    flagged = flagged or set()
    cats = json.load(open(CATEGORIES, encoding="utf-8"))
    hosts = sorted(cats.keys())
    if limit:
        hosts = hosts[:limit]

    # canary — retried, so one transient network blip does not void the round
    ok, msg = False, ""
    for attempt in range(3):
        ok, msg = canary()
        if ok:
            break
        if attempt < 2:
            time.sleep(5)
    if not ok:
        print(f"✗ canary failed: {msg}", file=sys.stderr)
        return None

    state = _load_state()
    rounds = state.get("rounds", [])
    # remove existing same round
    rounds = [r for r in rounds if r.get("round") != round_no]
    results = {}
    counts = {}
    started = time.time()
    done = 0

    def _work(host):
        r = process_host(host, do_traceroute=do_traceroute,
                          flagged=(host in flagged))
        return host, r

    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {ex.submit(_work, h): h for h in hosts}
        for fut in as_completed(futures):
            host, r = fut.result()
            results[host] = r
            d = r.get("decision", "unknown")
            counts[d] = counts.get(d, 0) + 1
            done += 1
            if done % SAVE_EVERY == 0 or done == len(hosts):
                # save progress
                _save_round_progress(round_no, results, counts, complete=False)
                print(f"  {done}/{len(hosts)} done", flush=True)

    elapsed = time.time() - started
    round_obj = {
        "round": round_no,
        "complete": True,
        "engine": "rdap+whois",
        "generated": datetime.now(timezone.utc).isoformat(),
        "elapsed_seconds": round(elapsed, 1),
        "counts": counts,
        "results": {h: results[h].get("decision", "unknown") for h in results},
    }
    rounds.append(round_obj)
    state["rounds"] = rounds
    state["categories_count"] = len(cats)
    _write_state(state)
    print(f"✓ round {round_no} complete in {elapsed:.0f}s: {counts}")
    return round_obj


def _load_state():
    if os.path.exists(STATE):
        try:
            with open(STATE, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"rounds": []}


def _save_round_progress(round_no, results, counts, complete):
    state = _load_state()
    rounds = [r for r in state.get("rounds", []) if r.get("round") != round_no]
    round_obj = {
        "round": round_no,
        "complete": complete,
        "engine": "rdap+whois",
        "generated": datetime.now(timezone.utc).isoformat(),
        "counts": dict(counts),
        "results": {h: results[h].get("decision", "unknown") for h in results},
    }
    rounds.append(round_obj)
    state["rounds"] = rounds
    _write_state(state)


def _write_state(state):
    os.makedirs(EVIDENCE, exist_ok=True)
    with open(STATE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
    # markdown summary
    _write_markdown(state)


def _write_markdown(state):
    lines = ["# Registration verification", "", f"Generated: {datetime.now(timezone.utc).isoformat()}", ""]
    for r in state.get("rounds", []):
        lines.append(f"## Round {r.get('round')} ({'complete' if r.get('complete') else 'partial'})")
        lines.append("")
        lines.append(f"Engine: {r.get('engine')}")
        lines.append("")
        lines.append("| decision | count |")
        lines.append("| --- | ---: |")
        for k, v in sorted((r.get("counts") or {}).items()):
            lines.append(f"| {k} | {v} |")
        lines.append("")
    with open(MARKDOWN, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


# ---------- proposal ----------

STRONG_CANDIDATE = {"gone", "expired"}
REVIEW_CANDIDATE = {"recently_registered", "review"}
FLAKY = {"unknown"}
NEVER = {"registered", "unsupported"}


def is_candidate(decision, aggressive=False, include_flaky=False, include_review=False):
    if decision in STRONG_CANDIDATE:
        return True
    if decision in REVIEW_CANDIDATE:
        return include_review
    if decision in {"gone"}:
        return True
    if decision in ("empty", "no-http"):
        return aggressive
    if decision in FLAKY:
        return include_flaky
    return False


def build_proposal(state, aggressive=False, include_flaky=False, include_review=False):
    rounds = [r for r in (state.get("rounds") or []) if r.get("complete") and r.get("results")]
    if len(rounds) < 2:
        return None
    # intersect candidates across rounds; drop any host harness-error/unknown in any round
    cand_sets = []
    all_hosts = set()
    for r in rounds:
        cs = set()
        for host, info in (r.get("results") or {}).items():
            all_hosts.add(host)
            dec = info if isinstance(info, str) else (info.get("decision") if isinstance(info, dict) else None)
            if dec == "harness-error":
                # never propose
                pass
            if is_candidate(dec, aggressive=aggressive, include_flaky=include_flaky, include_review=include_review):
                cs.add(host)
        cand_sets.append(cs)
    if not cand_sets:
        return []
    prop = set.intersection(*cand_sets) if len(cand_sets) > 1 else cand_sets[0]
    # drop hosts that were harness-error/unknown in any round
    for r in rounds:
        for host, info in (r.get("results") or {}).items():
            dec = info if isinstance(info, str) else (info.get("decision") if isinstance(info, dict) else None)
            if dec in ("harness-error", "unknown", "unsupported"):
                prop.discard(host)
    return sorted(prop)


# ---------- apply ----------

def apply_proposal(state, aggressive=False, include_flaky=False, include_review=False):
    proposal = build_proposal(state, aggressive=aggressive, include_flaky=include_flaky, include_review=include_review)
    if proposal is None:
        print("need at least two complete rounds", file=sys.stderr)
        return False
    cats = json.load(open(CATEGORIES, encoding="utf-8"))
    rules = json.load(open(RULES, encoding="utf-8"))
    drops = (rules.setdefault("drop", {}).setdefault("hosts", {}))
    when = datetime.now(timezone.utc).date().isoformat()
    n = 0
    for host in proposal:
        cat = cats.get(host, "?")
        if host in cats:
            del cats[host]
        n += 1
        drops[host] = f"no usable registration in 2 verify rounds ({'gone/expired/recycled'}) on {when}; {cat}"
    # sort
    cats = dict(sorted(cats.items()))
    with open(CATEGORIES, "w", encoding="utf-8") as f:
        json.dump(cats, f, indent=2, ensure_ascii=False)
        f.write("\n")
    with open(RULES, "w", encoding="utf-8") as f:
        json.dump(rules, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"applied: removed {n} host(s)")
    return True


# ---------- summary ----------

def summary(state):
    rounds = [r for r in (state.get("rounds") or []) if r.get("complete")]
    print(f"complete rounds: {len(rounds)}")
    for r in rounds:
        print(f"round {r.get('round')}: {r.get('counts')}")
    prop = build_proposal(state)
    print(f"default proposal (gone/expired): {len(prop) if prop is not None else 'n/a'}")
    if prop:
        for h in prop[:50]:
            print("  ", h)


# ---------- self test ----------

def self_test():
    # RDAP canary
    ok, msg = canary()
    assert ok, msg
    print("✓ canary ok")
    # reduction candidates
    assert reduction_candidates("a.b.example.com") == ["a.b.example.com", "b.example.com", "example.com"]
    assert reduction_candidates("example.com") == ["example.com"]
    print("✓ reduction_candidates")
    # parse rdap
    sample = json.dumps({
        "ldhName": "example.com",
        "status": ["client transfer prohibited"],
        "events": [{"eventAction": "registration", "eventDate": "1995-08-14T04:00:00Z"},
                   {"eventAction": "expiration", "eventDate": "2026-08-13T04:00:00Z"}],
        "entities": [{"roles": ["registrar"], "vcardArray": ["vcard", [["fn", {}, "text", "IANA"]]]}],
        "nameservers": [{"ldhName": "a.iana-servers.net"}],
    })
    rec = parse_rdap(sample.encode(), "rdap.iana.org")
    assert rec is not None and rec["registrar"] == "IANA"
    assert rec["created"].year == 1995
    print("✓ parse_rdap")
    # DENIC parse
    denic = "Domain: example.de\nStatus: connect\nChanged: 2023-06-01T12:45:04+02:00\n"
    # use whois_lookup? it queries network; instead test parse via manual
    # decision: expired
    r = {"rdap": {"_outcome": "ok", "status": [], "expires": datetime(2020, 1, 1, tzinfo=timezone.utc), "created": datetime(2010, 1, 1, tzinfo=timezone.utc)}}
    assert decide(r) == "expired"
    # gone
    r2 = {"rdap": {"_outcome": "ok", "status": ["pending delete"], "expires": datetime(2030, 1, 1, tzinfo=timezone.utc), "created": datetime(2010, 1, 1, tzinfo=timezone.utc)}}
    assert decide(r2) == "gone"
    # registered
    r3 = {"rdap": {"_outcome": "ok", "status": ["active"], "expires": datetime(2030, 1, 1, tzinfo=timezone.utc), "created": datetime(2010, 1, 1, tzinfo=timezone.utc)}}
    assert decide(r3) == "registered"
    # a name that is registered but not delegated is a review, not a removal
    r4 = {"rdap": {"_outcome": "ok", "status": ["inactive"], "expires": datetime(2030, 1, 1, tzinfo=timezone.utc), "created": datetime(2010, 1, 1, tzinfo=timezone.utc)}}
    assert decide(r4) == "review"
    r5 = {"rdap": {"_outcome": "ok", "status": ["client hold"], "expires": datetime(2030, 1, 1, tzinfo=timezone.utc), "created": datetime(2010, 1, 1, tzinfo=timezone.utc)}}
    assert decide(r5) == "review"
    # a host that still resolves in DNS is never "gone"
    r6 = {"rdap": {"_outcome": "notfound"}, "dns": {"resolves": True, "ip": "1.2.3.4"}}
    assert decide(r6) == "review"
    r7 = {"rdap": {"_outcome": "notfound"}, "dns": {"resolves": False, "ip": None}}
    assert decide(r7) == "gone"
    print("✓ decide")
    # a 404 is only a real RDAP negative when the endpoint speaks RDAP
    assert _rdap_404_is_real(b"", "application/rdap+json")
    assert _rdap_404_is_real(json.dumps({"errorCode": 404}).encode(), "application/json")
    assert not _rdap_404_is_real(b"<html><h1>404</h1></html>", "text/html;charset=utf-8")
    assert not _rdap_404_is_real(b"", "")
    print("✓ _rdap_404_is_real")
    # build_proposal — evidence stores the verdict as a bare string
    st = {"rounds": [
        {"round": 1, "complete": True, "results": {"a.test": "gone", "b.test": "gone", "c.test": "registered"}},
        {"round": 2, "complete": True, "results": {"a.test": "gone", "b.test": "registered", "c.test": "registered"}},
    ]}
    assert build_proposal(st) == ["a.test"]
    assert build_proposal({"rounds": st["rounds"][:1]}) is None
    # a full-record round from before the format shrank still reads
    legacy = {"rounds": [
        {"round": 1, "complete": True, "results": {"a.test": {"decision": "gone"}, "b.test": {"decision": "gone"}}},
        {"round": 2, "complete": True, "results": {"a.test": {"decision": "gone"}, "b.test": {"decision": "registered"}}},
    ]}
    assert build_proposal(legacy) == ["a.test"]
    print("✓ build_proposal")
    print("self-test OK")


def main():
    global DISCOVER_ENABLED
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--round", type=int)
    ap.add_argument("--limit", type=int)
    ap.add_argument("--summary", action="store_true")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--traceroute", action="store_true", help="run traceroute for flagged hosts")
    ap.add_argument("--traceroute-all", action="store_true", help="run traceroute for every host")
    ap.add_argument("--discover", action="store_true", help="probe registry conventions for TLDs without a known endpoint (slow)")
    ap.add_argument("--aggressive", action="store_true", help="also propose recently_registered")
    ap.add_argument("--include-flaky", action="store_true")
    ap.add_argument("--workers", type=int, default=WORKERS)
    args = ap.parse_args()
    DISCOVER_ENABLED = getattr(args, "discover", False)

    if args.self_test:
        self_test()
        return

    state = _load_state()

    if args.summary:
        summary(state)
        return

    if args.apply:
        ok = apply_proposal(state, aggressive=args.aggressive, include_flaky=args.include_flaky,
                            include_review=args.aggressive)
        if ok:
            print("now run generate.py + build-catalog-docs.py + test/test.sh")
        return

    if args.round:
        do_tr = args.traceroute or args.traceroute_all
        all_mode = args.traceroute_all
        flagged = set()
        if do_tr and not all_mode:
            # flagged = candidate hosts from existing rounds
            prop = build_proposal(state)
            if prop:
                flagged = set(prop)
            # also flaky-ish: unknown hosts
            for r in state.get("rounds", []):
                for h, info in (r.get("results") or {}).items():
                    if isinstance(info, dict) and info.get("decision") in ("unknown", "review", "recently_registered"):
                        flagged.add(h)
        run_round(args.round, limit=args.limit, workers=args.workers,
                  do_traceroute=do_tr, flagged=flagged if do_tr else set())
        return

    ap.print_help()


if __name__ == "__main__":
    main()