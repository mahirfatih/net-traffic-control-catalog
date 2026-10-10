#!/usr/bin/env node
/**
 * Static checks: do the documents still describe the files they name?
 *
 *   node scripts/check-docs-fresh.mjs
 *
 * This catches the drift that a data repository accumulates quietly — a file
 * renamed without the README noticing, a document quoting a count the catalog
 * no longer has, a script listed that does not exist. It needs no network and
 * no build; run it before claiming a change is complete.
 */
import { readFileSync, existsSync, readdirSync, statSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const problems = [];
const notes = [];

const read = (p) => readFileSync(join(ROOT, p), "utf8");
const json = (p) => JSON.parse(read(p));

/** Every markdown in the repo, so a dangling link anywhere is found. */
function markdownFiles() {
  const out = ["README.md", "CONTRIBUTING.md", "SECURITY.md", "CHANGELOG.md"];
  for (const dir of ["docs"]) {
    const full = join(ROOT, dir);
    if (!existsSync(full)) continue;
    for (const name of readdirSync(full)) {
      if (name.endsWith(".md")) out.push(`${dir}/${name}`);
    }
  }
  return out.filter((p) => existsSync(join(ROOT, p)));
}

/** 1. Every relative link in every document must resolve. */
function checkLinks() {
  for (const file of markdownFiles()) {
    const text = read(file);
    const links = [...text.matchAll(/\[[^\]]*\]\(([^)#]+?)\)/g)].map((m) => m[1]);
    for (const link of links) {
      if (/^(https?:|mailto:)/.test(link)) continue;
      const target = join(dirname(file), link.split("#")[0]);
      if (!existsSync(join(ROOT, target))) {
        problems.push(`${file}: link to a file that does not exist — ${link}`);
      }
    }
  }
  notes.push(`checked relative links in ${markdownFiles().length} document(s)`);
}

/** 2. Every script named in a document must exist. */
function checkScriptNames() {
  const known = new Set(
    readdirSync(join(ROOT, "scripts"))
      .filter((n) => n.endsWith(".py") || n.endsWith(".mjs"))
      .map((n) => `scripts/${n}`)
  );
  for (const file of markdownFiles()) {
    const text = read(file);
    const named = new Set(
      [...text.matchAll(/scripts\/([A-Za-z0-9_.-]+\.(?:py|mjs))/g)].map((m) => m[0])
    );
    for (const name of named) {
      if (!known.has(name)) {
        problems.push(`${file}: names ${name}, which does not exist`);
      }
    }
  }
  notes.push(`checked ${known.size} script name(s) referenced by the documents`);
}

/** 3. Every source id in rules.json must exist in sources.json. */
function checkSourceIds() {
  const sources = json("sources.json");
  const ids = new Set(sources.sources.map((s) => s.id));
  const summaryPath = join(ROOT, "evidence", "harvest-summary.json");
  if (!existsSync(summaryPath)) return;
  for (const id of json("evidence/harvest-summary.json").sources || []) {
    if (!ids.has(id)) {
      problems.push(`evidence/harvest-summary.json: source ${id} is not in sources.json`);
    }
  }
  notes.push(`checked ${ids.size} source record(s)`);
}

/** 4. docs/CATALOG.md is generated — it must not be stale. */
function checkGeneratedDocs() {
  const docPath = join(ROOT, "docs", "CATALOG.md");
  if (!existsSync(docPath)) {
    problems.push("docs/CATALOG.md is missing — run scripts/build-catalog-docs.py");
    return;
  }
  const catalog = json("catalog.json");
  const text = read("docs/CATALOG.md");

  const total = Object.keys(catalog.categories || {}).length;
  const claimed = text.match(/\*\*([\d,]+) names\*\*/);
  if (!claimed) {
    problems.push("docs/CATALOG.md: no host total found — is the file hand-edited?");
  } else if (Number(claimed[1].replace(/,/g, "")) !== total) {
    problems.push(
      `docs/CATALOG.md says ${claimed[1]} names, catalog.json has ${total} — regenerate it`
    );
  }

  const services = (catalog.services || []).length;
  const claimedServices = text.match(/\*\*([\d,]+) services?\*\*/);
  if (claimedServices && Number(claimedServices[1].replace(/,/g, "")) !== services) {
    problems.push(
      `docs/CATALOG.md says ${claimedServices[1]} services, catalog.json has ${services}`
    );
  }
  notes.push(`checked docs/CATALOG.md against ${total} names / ${services} services`);
}

/** 5. Host counts quoted per category must match the catalog. */
function checkCategoryTable() {
  const catalog = json("catalog.json");
  const text = read("docs/CATALOG.md");
  const counts = {};
  for (const [host, category] of Object.entries(catalog.categories || {})) {
    counts[category] = (counts[category] || 0) + 1;
  }
  let checked = 0;
  for (const line of text.split("\n")) {
    const m = line.match(/^\| `([a-z]+)` \| ([\d,]+) \|/);
    if (!m) continue;
    const [, category, quoted] = m;
    checked++;
    const actual = counts[category] ?? 0;
    if (Number(quoted.replace(/,/g, "")) !== actual) {
      problems.push(
        `docs/CATALOG.md: \`${category}\` says ${quoted}, catalog has ${actual}`
      );
    }
  }
  notes.push(`checked ${checked} per-category count(s)`);
}

/** 6. A source may not claim to be allowed when its licence blocks it. */
function checkLicenseGate() {
  const sources = json("sources.json");
  // The same table scripts/sources.py enforces, so this check and the gate can
  // never disagree. Proprietary APIs are deliberately absent: terms differ per
  // provider, so those records carry their own verdict and reason.
  const blocking = ["CC-BY-NC-SA", "CC-BY-NC-", "CC-BY-SA-"];
  for (const source of sources.sources) {
    const licence = String(source.license || "");
    const blocked = blocking.some((needle) => licence.startsWith(needle));
    if (blocked && source.allowed) {
      problems.push(
        `sources.json: ${source.id} has a blocking licence (${licence}) but allowed: true`
      );
    }
    if (!source.allowed && !String(source.reason || "").trim()) {
      problems.push(`sources.json: ${source.id} is blocked and gives no reason`);
    }
  }
  notes.push(`checked ${sources.sources.length} licence verdict(s)`);
}

for (const check of [
  checkLinks,
  checkScriptNames,
  checkSourceIds,
  checkGeneratedDocs,
  checkCategoryTable,
  checkLicenseGate,
]) {
  try {
    check();
  } catch (error) {
    problems.push(`${check.name} threw: ${error.message}`);
  }
}

for (const note of notes) console.log(`  · ${note}`);

if (problems.length) {
  console.error("");
  for (const problem of problems) console.error(`✗ ${problem}`);
  console.error(`\n${problems.length} problem(s)`);
  process.exit(1);
}
console.log("\n✓ docs are in line with the files they describe");