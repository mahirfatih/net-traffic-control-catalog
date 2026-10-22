# Naming conventions

One rule for file names, and each language's own standard for the identifiers
inside the file. This document says what the rule is, why it is the rule, and
where it deliberately departs from the standard it otherwise follows — so a
name that looks wrong can be checked against a written decision rather than a
guess.

## File names — kebab-case

Every script and data file is named in **kebab-case**: lowercase letters and
digits, words separated by a single `-`.

```
build-matrix.py            check-docs-fresh.mjs
catalog-core.py            public-suffix-exceptions.json
harvest-summary.json       bump-version.sh
```

| Applies to | Extension |
| :--- | :--- |
| Python | `.py` |
| JavaScript | `.mjs`, `.js` |
| Shell | `.sh` |
| Data | `.json` |

The name is the whole thing before the final extension, so
`public-suffix-exceptions.json` is one kebab-case name and `requirements.lock`
is `requirements`.

**Why kebab-case, and not something else.** This repository keeps *one* naming
rule for every file it ships. The cost is real and worth stating plainly:
[PEP 8](https://peps.python.org/pep-0008/) prefers `lowercase_with_underscores`
for a Python *module*, and a hyphen is not even legal in a module name — so
`catalog-core.py` cannot be written as an `import`. A script that needs another
one loads it by path instead (`importlib.util.spec_from_file_location` in
[`../../test/test.sh`](../../test/test.sh)). That is accepted as the price of a single,
memorable rule; it is a decision, not an oversight.

**Not covered by this rule.**

- **Markdown** keeps its own UPPERCASE convention — `README.md`, `FORMAT.md`,
  `SOURCES.md`. The `check-naming.mjs` guard does not look at it.
- **Vendored, generated and VCS directories** — `.git`, `.venv`,
  `node_modules`, `.pages`, `__pycache__` — and any file whose name begins with
  a dot (`.gitignore`, `.DS_Store`) are skipped.
- **Data values are not file names.** A host such as `vb-saarpfalz.de` inside
  `catalog.json` is a string, never inspected by the guard.

## Python identifiers — PEP 8

Inside a `.py` file the ordinary [PEP 8](https://peps.python.org/pep-0008/)
rules apply. The file *name* is the one deviation, kebab-case as above.

| Kind | Convention | Example |
| :--- | :--- | :--- |
| function, variable, parameter | `snake_case` | `host_problems`, `first_commit` |
| class | `CapWords` | `SourceRecord` |
| constant | `UPPER_CASE` | `VOCABULARY`, `EMBED_MODEL` |
| internal helper | leading underscore | `_iso_date`, `_rdap_404_is_real` |

## JavaScript identifiers — MDN

Inside a `.mjs` file the
[MDN JavaScript style guide](https://developer.mozilla.org/en-US/docs/MDN/Writing_guidelines/Code_style_guide/JavaScript)
applies.

| Kind | Convention | Example |
| :--- | :--- | :--- |
| function, variable | `camelCase` | `checkScriptNames`, `categoryColors` |
| class | `PascalCase` | `SourceRecord` |
| constant | `UPPER_CASE` | `COLOR`, `ROOT` |
| collection | plural, no type suffix | `nodes`, not `nodeArray` |

The guide says nothing about file names; the kebab-case rule above governs them.
It also rules out Hungarian notation (`sName`), `var`, and loose equality.

## JSON — snake_case keys, kebab-case file names

The object keys in a data file are **`snake_case`**, matching the syntax shown
in the [JSON reference](https://www.w3schools.com/js/json_syntax.asp) examples.

```json
{
  "format_version": 1,
  "generated_unix": 1792443600,
  "hosts_in_first_commit": 432
}
```

The file *name* is kebab-case (`harvest-summary.json`), and the *values* are
data — a host, a category, a date — and carry whatever shape their own domain
requires.

## Deliberate exceptions

Three cases look like violations and are not. Renaming them would break a
contract, so the guard leaves them alone and they are recorded here.

| Where | What | Why |
| :--- | :--- | :--- |
| `reference/category-colors.json` | `foldedTail`, `tintText` | The palette is copied from the iOS app's `DomainCategoryStyle.swift`; the keys mirror its property names on purpose. The file's own `$comment` says so. |
| `config/schema.json` | `$schema`, `$id`, `additionalProperties`, `propertyNames`, `uniqueItems` | These are [JSON Schema](https://json-schema.org/) keywords, defined by the specification, not by us. |
| any `.json` | `$comment`, `_comment` | Meta keys that carry an explanation to a human reader, not data. |

The category vocabulary itself contains an entry that is not a hostname —
`ipAddress` — which is a value, not a key, and is explained in
[`../reference/IPADDRESS.md`](../reference/IPADDRESS.md).

## Enforcement

- [`../../scripts/checks/check-naming.mjs`](../../scripts/checks/check-naming.mjs)
  checks every `.py`, `.mjs`, `.js`, `.sh` and `.json` file name. It runs as
  step 8c of [`../../test/test.sh`](../../test/test.sh).
- [`../../scripts/checks/check-docs-fresh.mjs`](../../scripts/checks/check-docs-fresh.mjs)
  fails when a document names a script that does not exist, so a rename cannot
  leave a stale reference behind.

## Sources

- Python: [PEP 8 — Style Guide for Python Code](https://peps.python.org/pep-0008/).
- JavaScript: [MDN — Guidelines for writing JavaScript code examples](https://developer.mozilla.org/en-US/docs/MDN/Writing_guidelines/Code_style_guide/JavaScript).
- JSON: [JSON syntax](https://www.w3schools.com/js/js_json_syntax.asp).
