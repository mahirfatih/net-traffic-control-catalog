# reference

Reference data shipped with the catalog so runs are reproducible without a
network. Nothing here is hand-written at build time.

- [`rdap/`](rdap/README.md) — RDAP (RFC 7480-7484) bootstrap and verified
  supplement data used by `scripts/catalog/verify-registrations.py`. Copied from
  the iOS project's `ReferenceData/RDAP/`; regenerating it is a deliberate,
  reviewed step.
- [`category-colors.json`](category-colors.json) — the app's category palette:
  each category's `tint`, a darkened `tintText`, and its colour `family`, copied
  from the iOS project's
  `NetTrafficControl/DomainCategoryStyle.swift`. `scripts/catalog/build-catalog-docs.py`
  reads it to colour the README treemap and pie, so a category's colour lives in
  one place instead of being re-derived (or remembered) every time. Edit this
  file to change a colour; the charts follow.
