#!/usr/bin/env python3
"""Build or verify `manifest.json` — the cheap end of the distribution contract.

    python3 scripts/release/build-manifest.py            # write manifest.json
    python3 scripts/release/build-manifest.py --check    # verify; write nothing
    python3 scripts/release/build-manifest.py --sha256-out FILE

`manifest.json` is about a kilobyte: enough for an application to learn whether
`catalog.json` changed, what it hashes to and whether it understands the format
*before* downloading the whole file. Everything in it comes from the bytes of
`catalog.json` alone — no clock, no environment, no git — so the same file always
produces the same manifest, and `--check` fails the moment the two drift apart.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / "catalog.json"
DEFAULT_OUT = ROOT / "manifest.json"
MANIFEST_VERSION = 2
REQUIRED = ("version", "generated", "categories", "services", "format_version", "manifest_version", "manifest_file")


def build(catalog=CATALOG):
    """The manifest that describes `catalog`, or exit on a file that cannot be one."""
    payload = catalog.read_bytes()
    try:
        document = json.loads(payload)
    except ValueError as error:
        raise SystemExit(f"✗ {catalog.name} is not JSON: {error}")
    missing = [field for field in REQUIRED if field not in document]
    if missing:
        raise SystemExit(f"✗ {catalog.name} has no {', '.join(map(repr, missing))}")
    return {
        "manifest_version": MANIFEST_VERSION,
        "catalog": catalog.name,
        "format_version": document["version"],
        "generated": document["generated"],
        "generated_unix": document.get("generated_unix"),
        "bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "hosts": len(document["categories"]),
        "services": len(document["services"]),
    }


def render(manifest):
    return json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"


def describe(text):
    """The sha the on-disk manifest claims, for a failure message."""
    try:
        return json.loads(text).get("sha256", "<none>")
    except ValueError:
        return "<not JSON>"


def main(argv):
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify the committed manifest instead of writing it",
    )
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="manifest to write or verify")
    parser.add_argument(
        "--sha256-out",
        help="also write a sha256sum-compatible checksum file",
    )
    args = parser.parse_args(argv[1:])

    manifest = build()
    text = render(manifest)
    out = Path(args.out)

    if args.check:
        if not out.exists():
            print(
                f"✗ {out} does not exist — run scripts/release/build-manifest.py",
                file=sys.stderr,
            )
            return 1
        committed = out.read_text(encoding="utf-8")
        if committed != text:
            print(f"✗ {out.name} does not describe {manifest['catalog']}", file=sys.stderr)
            print(f"  manifest claims: {describe(committed)}", file=sys.stderr)
            print(f"  catalog is:      {manifest['sha256']}", file=sys.stderr)
            print("  Regenerate it: python3 scripts/release/build-manifest.py", file=sys.stderr)
            return 1
        print(
            f"✓ {out.name} describes {manifest['catalog']} "
            f"({manifest['sha256'][:16]}…, {manifest['bytes']} bytes)"
        )
    else:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
        print(
            f"✓ wrote {out}: {manifest['hosts']} hosts, "
            f"{manifest['services']} services, {manifest['bytes']} bytes"
        )

    if args.sha256_out:
        checksum = Path(args.sha256_out)
        checksum.write_text(f"{manifest['sha256']}  {manifest['catalog']}\n", encoding="utf-8")
        print(f"✓ wrote {checksum}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
