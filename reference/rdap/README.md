# reference/rdap

RDAP (RFC 7480-7484) reference data used by `scripts/catalog/verify-registrations.py`
to resolve which registry answers for a name or an address block. Copied from the
iOS project's `ReferenceData/RDAP/` (net-traffic-control-ios).

## Files

- `rdap-dns.json` — IANA bootstrap registry for domain names (RFC 9224). TLD →
  registry base URL(s).
- `rdap-cc.json` — country-code registries IANA omits, each verified by a real
  RDAP domain lookup. Also lists TLDs known to publish no RDAP (`unsupported`,
  e.g. `.tr` via TRABIS).
- `rdap-ipv4.json` / `rdap-ipv6.json` — IP address block → RIR registry
  (longest-prefix match).

## Provenance

This is **research data, not a build-time fetch.** Every entry was verified by
performing a real RDAP lookup and requiring an object with
`objectClassName`/`ldhName`/`events` in the response. Regenerating these files is
a deliberate, reviewed step (see the iOS project's generator). The catalog repo
does not fetch them at runtime; it ships the snapshot so a run is reproducible
offline and so no third party is asked where to look.

Publication dates: `rdap-dns.json` 2026-09-16, `rdap-cc.json` verified 2026-09-28,
`rdap-ipv4.json` 2019-06-07, `rdap-ipv6.json` 2019-06-07.
