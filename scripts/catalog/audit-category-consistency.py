#!/usr/bin/env python3
"""Audit labels for known domain families and category boundary mistakes.

    python3 scripts/catalog/audit-category-consistency.py

This is not a classifier. It is a set of deliberately boring guardrails for
mistakes that are easy to make when a source is owner/vendor based but the
catalog is function based. For example, Microsoft owns Outlook, Skype, Xbox,
Bing Maps and Clarity; they must not all become `software` just because the
source is a Microsoft domain list.
"""
import json
import os
import sys
import importlib.util

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CATEGORIES = os.path.join(ROOT, "seeds", "categories.json")
RULES = os.path.join(ROOT, "config/rules.json")

_overrides_spec = importlib.util.spec_from_file_location(
    "overrides", os.path.join(ROOT, "scripts", "catalog", "overrides.py")
)
overrides_module = importlib.util.module_from_spec(_overrides_spec)
_overrides_spec.loader.exec_module(overrides_module)


def host_matches(host, suffixes):
    return any(host == suffix or host.endswith(f".{suffix}") for suffix in suffixes)


def main():
    with open(CATEGORIES, encoding="utf-8") as handle:
        categories = json.load(handle)

    # A host a person overrode on purpose is not a consistency mistake: the
    # override is the decision. Skip it here so the guardrail keeps reporting
    # real boundary slips rather than arguing with a review.
    try:
        decided = overrides_module.overrides(overrides_module.load_rules(RULES))
    except (OSError, ValueError):
        decided = {}

    expected = [
        ("Microsoft ads", ["adnxs.com", "adnxs.net", "appnexus.com", "xandr.com", "msads.net", "microsoftadvertising.com", "microsoftadvertisingdisplayconnect.com", "bizographics.com"], "ads"),
        ("Microsoft analytics", ["clarity.ms", "applicationinsights.io", "applicationinsights.us", "loganalytics.io", "loganalytics.us", "dc.services.visualstudio.com", "exp-tas.com"], "analytics"),
        ("Microsoft crash diagnostics", ["hockeyapp.net"], "crash"),
        ("Microsoft AI", ["githubcopilot.com", "customvision.ai", "luis.ai"], "ai"),
        ("Microsoft gaming", ["xbox.com", "xbox.co", "xboxlive.com", "xboxservices.com", "gamepass.com", "minecraft.net", "minecraftservices.com", "minecraft-services.net", "bethesda.net", "activision.com", "activisionblizzard.com", "blizzard.com", "battle.net", "callofduty.com", "demonware.net", "forza.net", "forzamotorsport.net", "ageofempires.com", "halowaypoint.com", "seaofthieves.com", "playfab.com", "playfabapi.com", "zune.com", "zune.net", "zune.org"], "gaming"),
        ("Microsoft maps", ["virtualearth.net", "bingmaps.com", "bingmapsportal.com"], "maps"),
        ("Microsoft messaging", ["skype.com", "skype.net", "skype.co", "skype.co.uk", "skypeforbusiness.com", "lync.com", "groupme.com", "teams.microsoft.com"], "messaging"),
        ("Microsoft mail", ["outlook.com", "outlook.eu", "outlookmobile.com", "hotmail.com", "hotmail.net", "hotmail.co.uk"], "email"),
        ("Bing search", ["bing.com", "bing.net", "bing.co", "bing.cn", "bingapis.com", "bingplaces.com", "bingforbusiness.com", "bingbusinessportal.com", "bing-int1.com", "binginternal.com", "bingparachute.com", "bingviz.com", "discoverbing.com", "microsoftstart.com", "msn.com", "msn.ca", "msn.de", "msn.co.in", "msn.co.jp", "msn.it", "msn.se", "playmsn.com", "s-msn.com"], "search"),
        ("LinkedIn social", ["linkedin.com", "linkedin.cn", "linkedin.at", "linkedinmobileapp.com", "lnkd.in", "licdn.com", "licdn.cn", "yammer.com", "yammerusercontent.com"], "social"),
        ("Azure DNS/CDN", ["azure-dns.com", "azure-dns.net", "azure-dns.org", "azure-dns.info", "azure-dns.cn", "azure-dns-1.cn", "akadns.net", "akadns6.net", "footprintdns.com", "jwpcdn.com"], "cdn"),
    ]

    problems = []
    for label, suffixes, category in expected:
        for host, actual in categories.items():
            if host in decided and decided[host][0] == actual:
                continue
            if host_matches(host, suffixes) and actual != category:
                problems.append(f"{host}: expected {category!r} for {label}, got {actual!r}")

    forbidden = [
        ("email", ["skype", "groupme", "lync"], "messaging"),
        ("search", ["bingmaps", "virtualearth"], "maps"),
        ("software", ["clarity.ms", "msads", "adnxs", "appnexus", "xandr"], "ads/analytics"),
    ]
    for wrong_category, tokens, expected_hint in forbidden:
        for host, actual in categories.items():
            if host in decided and decided[host][0] == actual:
                continue
            if actual == wrong_category and any(token in host for token in tokens):
                problems.append(f"{host}: suspicious {wrong_category!r}; expected {expected_hint}")

    if problems:
        print("✗ category consistency audit found problem(s):", file=sys.stderr)
        for problem in problems:
            print(f"  {problem}", file=sys.stderr)
        return 1

    print(f"✓ category consistency audit passed ({len(categories)} labels checked)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
