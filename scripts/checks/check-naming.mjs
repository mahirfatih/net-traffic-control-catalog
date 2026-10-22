#!/usr/bin/env node
/**
 * check-naming.mjs — do the script and data files keep the naming convention?
 *
 *   node scripts/checks/check-naming.mjs
 *
 * Every `.py`, `.mjs`, `.js`, `.sh` and `.json` file must be named in
 * kebab-case: lowercase, digits, words separated by `-`. The rule and why it is
 * the rule (PEP 8 would prefer `snake_case` for a Python module; this
 * repository keeps one naming rule for every script and data file) are written
 * down in docs/guides/NAMING.md.
 *
 * The scope is deliberately narrow. Markdown keeps its own UPPERCASE
 * convention (`README.md`, `FORMAT.md`), vendored and generated directories are
 * skipped, and JSON *contents* are not inspected here — only the file name, so
 * a hostname like `vb-saarpfalz.de` sitting inside a catalog is never mistaken
 * for a file name. No network, no build.
 */
import { readdirSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..", "..");

// The file types this rule governs. Markdown is excluded on purpose: the
// documentation set is UPPER-CASE named by convention (README.md, FORMAT.md).
const SCOPED = [".py", ".mjs", ".js", ".sh", ".json"];

// Vendored, generated and VCS directories that must not be walked.
const SKIP_DIRS = new Set([".git", ".venv", "node_modules", ".pages", "__pycache__"]);

// Lowercase words joined by single hyphens: `build-matrix`, `catalog-2026`.
const KEBAB = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;

const problems = [];
let checked = 0;

function stem(name) {
  // The part before the final extension, so `requirements.lock` is
  // `requirements` and `public-suffix-exceptions.json` is the whole name.
  return name.replace(/\.[^.]+$/, "");
}

function walk(rel) {
  const full = join(ROOT, rel);
  for (const entry of readdirSync(full, { withFileTypes: true })) {
    if (entry.name.startsWith(".") || SKIP_DIRS.has(entry.name)) continue;
    const child = rel ? `${rel}/${entry.name}` : entry.name;
    if (entry.isDirectory()) {
      walk(child);
      continue;
    }
    if (!SCOPED.some((ext) => entry.name.endsWith(ext))) continue;
    checked += 1;
    if (!KEBAB.test(stem(entry.name))) {
      problems.push(`${child}: ${entry.name} is not kebab-case`);
    }
  }
}

walk("");

if (problems.length) {
  for (const problem of problems) console.error(`✗ ${problem}`);
  console.error(
    `\n${problems.length} file(s) break the naming convention — see docs/guides/NAMING.md`
  );
  process.exit(1);
}

console.log(`✓ ${checked} script/data file(s) are kebab-case`);
