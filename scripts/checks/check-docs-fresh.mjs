#!/usr/bin/env node
/**
 * Static checks: do the documents still describe the files they name?
 *
 *   node scripts/checks/check-docs-fresh.mjs
 *
 * This catches the drift that a data repository accumulates quietly — a file
 * renamed without the README noticing, a document quoting a count the catalog
 * no longer has, a script listed that does not exist. It needs no network and
 * no build; run it before claiming a change is complete.
 */
import { readFileSync, existsSync, readdirSync, statSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
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
  // `scripts/` is grouped into subfolders, so walk it; a document may name a
  // script by its grouped path.
  const known = new Set();
  const walk = (rel) => {
    for (const name of readdirSync(join(ROOT, rel))) {
      if (name.startsWith(".") || name === "__pycache__") continue;
      const child = `${rel}/${name}`;
      if (statSync(join(ROOT, child)).isDirectory()) walk(child);
      else if (name.endsWith(".py") || name.endsWith(".mjs")) known.add(child);
    }
  };
  walk("scripts");
  for (const file of markdownFiles()) {
    const text = read(file);
    const named = new Set(
      [...text.matchAll(/scripts\/[A-Za-z0-9_./-]+\.(?:py|mjs)/g)].map((m) => m[0])
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
    problems.push("docs/CATALOG.md is missing — run scripts/catalog/build-catalog-docs.py");
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
  // The same table scripts/sources/sources.py enforces, so this check and the gate can
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

/** 7. Every directory that holds files has a README. */
function checkDirectoryReadmes() {
  const skip = new Set(["__pycache__"]);
  const dirs = [];
  const walk = (rel) => {
    for (const name of readdirSync(join(ROOT, rel))) {
      if (name.startsWith(".") || skip.has(name)) continue;
      const child = rel ? `${rel}/${name}` : name;
      if (!statSync(join(ROOT, child)).isDirectory()) continue;
      dirs.push(child);
      walk(child);
    }
  };
  walk("");

  for (const dir of dirs) {
    if (!existsSync(join(ROOT, dir, "README.md"))) {
      problems.push(`${dir}/ holds files but has no README.md — say what belongs in it`);
    }
  }
  notes.push(`checked ${dirs.length} director(ies) for a README`);
}

/** 8. Figures quoted from the reliability audit must come from its own output. */
function checkAnalysisFigures() {
  const dataPath = "docs/analysis/out/matrix-data.json";
  if (!existsSync(join(ROOT, dataPath))) {
    notes.push("no analysis output present — skipped the reliability figures");
    return;
  }
  const data = json(dataPath);
  const matrix = data.matrix || [];
  const total = matrix.reduce((sum, row) => sum + row.reduce((a, b) => a + b, 0), 0);
  const correct = matrix.reduce(
    (sum, row, i) => sum + (row[i] || 0),
    0
  );
  const classes = (data.classes || []).length;
  const accuracy = Math.round((correct / total) * 100);
  const fmt = (n) => n.toLocaleString("en-US");
  const report = data.classification_report || {};

  // "**Accuracy: 84%** (1,553/1,844, 19 classes, 5-fold CV)"
  const headline = /\*\*Accuracy: (\d+)%\*\*\s*\((\d[\d,]*)\/(\d[\d,]*),\s*(\d+) classes/;
  for (const file of ["README.md", "docs/analysis/README.md"]) {
    const m = read(file).match(headline);
    if (!m) {
      problems.push(`${file}: no accuracy headline found — is it hand-written now?`);
      continue;
    }
    const [, pct, num, den, cls] = m;
    const claims = [
      [`accuracy ${pct}%`, Number(pct), accuracy],
      [`${num} correct`, Number(num.replace(/,/g, "")), correct],
      [`${den} hosts`, Number(den.replace(/,/g, "")), total],
      [`${cls} classes`, Number(cls), classes],
    ];
    for (const [label, quoted, actual] of claims) {
      if (quoted !== actual) {
        problems.push(
          `${file}: says ${label}, ${dataPath} has ${fmt(actual)} — rerun build-matrix.py`
        );
      }
    }
  }

  // "accuracy 84% over 1844 hosts across 19 categories"
  const catalogDoc = "docs/CATALOG.md";
  const summary = read(catalogDoc).match(
    /\*\*accuracy (\d+)%\*\*\s*over (\d+) hosts across (\d+) categories/
  );
  if (summary) {
    const [, pct, hosts, cls] = summary;
    if (Number(pct) !== accuracy || Number(hosts) !== total || Number(cls) !== classes) {
      problems.push(
        `${catalogDoc}: reliability summary is stale — ${dataPath} reports ${accuracy}% over ${total} hosts across ${classes} categories`
      );
    }
  }

  // The per-class table and the F1 quotes must be the report's own numbers.
  const f1 = (c) => (report[c] ? Number(report[c]["f1-score"].toFixed(2)) : null);
  const tableRow = /^\| ([a-z]+) \| ([\d.]+) \| ([\d.]+) \| ([\d.]+) \| (\d+) \|$/;
  let rows = 0;
  const text = read("docs/analysis/README.md");
  for (const line of text.split("\n")) {
    const m = line.match(tableRow);
    if (!m || !(m[1] in report)) continue;
    rows++;
    const [, c, precision, recall, score, support] = m;
    const actual = report[c];
    for (const [field, quoted] of [
      ["precision", precision],
      ["recall", recall],
      ["f1-score", score],
      ["support", support],
    ]) {
      const want = field === "support" ? actual.support : Number(actual[field].toFixed(2));
      if (Number(quoted) !== want) {
        problems.push(
          `docs/analysis/README.md: \`${c}\` ${field} says ${quoted}, ${dataPath} has ${want}`
        );
      }
    }
  }

  // Model comparison rows must match the analysis output as well.
  const comparison = data.model_comparison || [];
  const comparisonByName = Object.fromEntries(comparison.map((row) => [row.model, row]));
  const comparisonRow = /^\| ([A-Za-z]+) \| ([\d.]+) \| ([\d.]+) \| ([\d.]+) \|$/;
  let comparisonRows = 0;
  for (const line of text.split("\n")) {
    const m = line.match(comparisonRow);
    if (!m || !(m[1] in comparisonByName)) continue;
    comparisonRows++;
    const [, model, accuracyValue, macroF1Value, weightedF1Value] = m;
    const actual = comparisonByName[model];
    for (const [field, quoted] of [
      ["accuracy", accuracyValue],
      ["macro_f1", macroF1Value],
      ["weighted_f1", weightedF1Value],
    ]) {
      const want = Number(actual[field].toFixed(3));
      if (Number(quoted) !== want) {
        problems.push(
          `docs/analysis/README.md: ${model} ${field} says ${quoted}, ${dataPath} has ${want}`
        );
      }
    }
  }
  if (comparison.length && comparisonRows !== comparison.length) {
    problems.push(
      `docs/analysis/README.md: model comparison has ${comparisonRows} row(s), ${dataPath} has ${comparison.length}`
    );
  }

  const readmeComparison = read("README.md");
  for (const row of comparison) {
    const accuracyValue = row.accuracy.toFixed(3);
    const weightedF1Value = row.weighted_f1.toFixed(3);
    const needle = `${row.model} ${accuracyValue} / ${weightedF1Value}`;
    if (!readmeComparison.includes(needle)) {
      problems.push(`README.md: missing model comparison quote \`${needle}\``);
    }
  }

  // "**Highest F1:** `education` 0.93, `government` 0.97, ..."
  const quote = /`([a-z]+)` ([\d.]+)/g;
  const lines = (text + read("README.md")).split("\n");
  let quotes = 0;
  for (const line of lines) {
    if (!/Highest F1|Lowest F1/.test(line)) continue;
    for (const m of line.matchAll(quote)) {
      const [, c, value] = m;
      const want = f1(c);
      if (want === null) {
        problems.push(`an F1 quote names \`${c}\`, which is not a class in ${dataPath}`);
      } else if (Number(value) !== want) {
        problems.push(`an F1 quote says \`${c}\` ${value}, ${dataPath} has ${want}`);
      } else {
        quotes++;
      }
    }
  }

  notes.push(
    `checked reliability figures against ${dataPath}: ${accuracy}% / ${correct} of ${total} / ${classes} classes, ${rows} metric row(s), ${quotes} F1 quote(s), ${comparisonRows} model row(s)`
  );
}

for (const check of [
  checkLinks,
  checkScriptNames,
  checkSourceIds,
  checkGeneratedDocs,
  checkCategoryTable,
  checkLicenseGate,
  checkDirectoryReadmes,
  checkAnalysisFigures,
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
