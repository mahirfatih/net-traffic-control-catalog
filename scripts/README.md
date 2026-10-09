# scripts

Tooling for this catalog. Python 3, standard library only — no dependencies.

| Script | What it does |
| :--- | :--- |
| [`generate.py`](generate.py) | Builds `catalog.json` from the `seeds/` files. Deterministic, and validates **before** writing — a bad seed writes nothing. |
| [`validate.py`](validate.py) | Checks a `catalog.json` against the format and the category vocabulary. Exits non-zero on any problem. |
| [`catalog_lib.py`](catalog_lib.py) | Shared load / validate / write logic used by both. Not run on its own. |

## Workflow

`seeds/` is the source of truth; `catalog.json` is the build output. Change the
seeds, regenerate, then validate:

```sh
python3 scripts/generate.py \
    --categories seeds/categories.json \
    --services   seeds/services.json \
    --out        catalog.json
python3 scripts/validate.py
```

Do not edit `catalog.json` by hand — a hand edit is what `generate.py` would
overwrite on the next run. Edit `seeds/` instead.

## What `validate.py` checks

- `version` is `1`.
- `categories` is an object of `host → category`, **sorted by host**.
- Every category is in the vocabulary (see the top-level [`README.md`](../README.md)).
- Every host and service domain is lowercase.
- `services` is an array; every entry has a non-empty `key`, `name` and `domains`.
- Service `key`s are unique.
- The catalog is not empty.

## Exit codes

- `0` — valid.
- `1` — a problem was found (the reasons are printed to stderr).

## Adding the tooling to CI

Both scripts are plain and dependency-free, so a check is:

```sh
python3 scripts/validate.py
```
