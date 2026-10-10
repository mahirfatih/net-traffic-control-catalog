# Needs review

Hosts a source listed that **no rule in `rules.json` matched**. They are not
in `seeds/categories.json` and they are not in `catalog.json`.

That is the whole point of this file. A host with no category is an open
question; putting it in `catalog.json` as `other` would convert the question
into a claim, and `other` on screen looks like an answer.

## How a host gets out of here

Either add a rule to `rules.json` (right category, and a `note` saying why), or
add it to that file's `drop.hosts` map with a reason. Both are reviewed like
anything else.

A host dropped without a reason is indistinguishable from a host somebody
forgot, so `rules.json` asks for one.

## Current

Regenerate this section with:

```sh
python3 scripts/sources/harvest.py
```

| Host | Source | Notes |
| :--- | :--- | :--- |
| `api.rlje.net` | `anudeepnd-whitelist` | Resolves to CloudFront addresses (`3.169.107.x`), returns 403 over HTTPS. No documentation, no matching name, no way to establish who operates it. |

### What was tried for `api.rlje.net`

- **DNS** — three A records, all in Amazon CloudFront's range.
- **HTTPS** — 403 from the origin.
- **Naming** — `rlje` matches nothing in any of the three source files, the
  other names in the same list, or the maintainer's repository.

It could be a legitimate API fronted behind CloudFront whose public name is
simply short. **Guessing is worse than leaving it open**, because a wrong label
is authoritative-looking and nobody can tell it was never checked. It stays
here until somebody knows.

If you know what it is, open a pull request with a rule.