# ipAddress — the category that is not a host

`ipAddress` is in the category vocabulary, but it is **not a hostname category**.
The app files a *literal address* under it — the thing that actually reached the
device — rather than a domain name. A row in this catalog is always a domain
name, so an `ipAddress` verdict never appears here as a host.

## Why the catalog does not list addresses

- **They are not domains.** A DNS filter matches names; the catalog is a list of
  names. An address is the fallback label when no name matched, so enumerating it
  would mean listing the whole address space.
- **They are unbounded and churn.** Addresses are far more numerous and shorter
  lived than the domains this catalog is curated for; a frozen list of them goes
  stale the day it is committed.
- **The verdict is decided at match time**, on the device, from the same
  hostname data this catalog already carries. There is nothing to add here.

## So why is it in the vocabulary

Because the app must be able to *label* what it saw, and `ipAddress` is the only
honest label for "a literal address, not a name we know". Keeping the name in the
vocabulary means the label is always well-formed, even though no catalog row
uses it.

## What a contributor should not do

Do not add `1.2.3.4`-style entries to `seeds/categories.json` "to be thorough".
They will never match a name lookup, `scripts/catalog/validate.py` rejects
non-names, and the row would sit silently doing nothing. If an address really
needs a category, that is a routing or policy question for the app, not a row in
this file.

See [`PIPELINE.md`](PIPELINE.md) for how a *name* is decided, and
[`SOURCES.md`](SOURCES.md) for where those names come from.
