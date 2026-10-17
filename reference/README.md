# reference

Reference data shipped with the catalog so runs are reproducible without a
network. Nothing here is hand-written at build time.

- [`rdap/`](rdap/README.md) — RDAP (RFC 7480-7484) bootstrap and verified
  supplement data used by `scripts/catalog/verify-registrations.py`. Copied from
  the iOS project's `ReferenceData/RDAP/`; regenerating it is a deliberate,
  reviewed step.
