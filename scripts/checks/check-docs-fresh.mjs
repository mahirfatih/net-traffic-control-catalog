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
import { execFileSync } from "node:child_process";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
const problems = [];
const notes = [];

const read = (p) => readFileSync(join(ROOT, p), "utf8");
const json = (p) => JSON.parse(read(p));

/**
 * Every markdown in the repo, so a dangling link anywhere is found.
 *
 * This used to walk only the repository root and one level of `docs/`, which
 * left fourteen documents unchecked — including `docs/analysis/README.md`,
 * `scripts/README.md` and every subdirectory README. Drift was found hiding in
 * exactly those files. Vendored and generated-noise directories are skipped.
 */
const SKIP_DIRS = new Set([".git", ".venv", "node_modules", ".pages", "__pycache__"]);

function markdownFiles() {
  const out = [];
  const walk = (rel) => {
    const full = join(ROOT, rel);
    for (const entry of readdirSync(full, { withFileTypes: true })) {
      if (entry.isDirectory()) {
        if (SKIP_DIRS.has(entry.name)) continue;
        walk(rel ? `${rel}/${entry.name}` : entry.name);
      } else if (entry.name.endsWith(".md")) {
        out.push(rel ? `${rel}/${entry.name}` : entry.name);
      }
    }
  };
  walk("");
  return out.sort().filter((p) => existsSync(join(ROOT, p)));
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

/** 5b. docs/COVERAGE.md is generated — its headline numbers must match the data. */
function checkCoverageDoc() {
  const docPath = join(ROOT, "docs", "COVERAGE.md");
  if (!existsSync(docPath)) {
    problems.push("docs/COVERAGE.md is missing — run scripts/catalog/build-coverage.py");
    return;
  }
  const catalog = json("catalog.json");
  const text = read("docs/COVERAGE.md");
  const counts = {};
  for (const category of Object.values(catalog.categories || {})) {
    counts[category] = (counts[category] || 0) + 1;
  }
  const total = Object.keys(catalog.categories || {}).length;

  const claimed = text.match(/\*\*([\d,]+) names\*\*/);
  if (!claimed) {
    problems.push("docs/COVERAGE.md: no host total found — is the file hand-edited?");
  } else if (Number(claimed[1].replace(/,/g, "")) !== total) {
    problems.push(
      `docs/COVERAGE.md says ${claimed[1]} names, catalog.json has ${total} — regenerate it`
    );
  }

  // The skew table is the load-bearing part of the page: a stale finance count
  // would understate the majority class the whole analysis is balanced against.
  const row = text.match(/^\| `finance` \| ([\d,]+) \| ([\d.]+)% \|/m);
  if (!row) {
    problems.push("docs/COVERAGE.md: no finance row in the skew table");
  } else {
    const quoted = Number(row[1].replace(/,/g, ""));
    if (quoted !== (counts.finance ?? 0)) {
      problems.push(
        `docs/COVERAGE.md: finance says ${row[1]}, catalog has ${counts.finance ?? 0}`
      );
    }
  }
  notes.push(`checked docs/COVERAGE.md against ${total} names / finance ${counts.finance ?? 0}`);
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

  // The Turkish README carries the same hand-written numbers in its own words
  // ("Doğruluk: %89% … 4,563 … 27 sınıf"), so it is checked the same way rather
  // than by pretending it is a second English file.
  const trHeadline = /\*\*Doğruluk: %(\d+)\*\*\s*\((\d[\d,]*)\/(\d[\d,]*),\s*(\d+) sınıf/;
  const tr = read("README.tr.md").match(trHeadline);
  if (tr) {
    const [, pct, num, den, cls] = tr;
    const claims = [
      [`accuracy ${pct}%`, Number(pct), accuracy],
      [`${num} correct`, Number(num.replace(/,/g, "")), correct],
      [`${den} hosts`, Number(den.replace(/,/g, "")), total],
      [`${cls} classes`, Number(cls), classes],
    ];
    for (const [label, quoted, actual] of claims) {
      if (quoted !== actual) {
        problems.push(
          `README.tr.md: says ${label}, ${dataPath} has ${fmt(actual)} — rerun build-matrix.py`
        );
      }
    }
  }
  const balanced = Math.round((data.balanced_accuracy || 0) * 100);
  if (tr && read("README.tr.md").match(/\*\*dengeli doğruluk %(\d+)\*\*/)) {
    const tb = read("README.tr.md").match(/\*\*dengeli doğruluk %(\d+)\*\*/);
    if (Number(tb[1]) !== balanced) {
      problems.push(
        `README.tr.md: says balanced accuracy ${tb[1]}%, ${dataPath} has ${balanced}%`
      );
    }
  }

  // "accuracy 84% over 1,844 hosts across 19 categories"
  const catalogDoc = "docs/CATALOG.md";  const summary = read(catalogDoc).match(
    /\*\*accuracy (\d+)%\*\*\s*over ([\d,]+) hosts across ([\d,]+) categories/
  );
  if (summary) {
    const [, pct, hosts, cls] = summary;
    if (
      Number(pct) !== accuracy ||
      Number(hosts.replace(/,/g, "")) !== total ||
      Number(cls.replace(/,/g, "")) !== classes
    ) {
      problems.push(
        `${catalogDoc}: reliability summary is stale — ${dataPath} reports ${accuracy}% over ${total} hosts across ${classes} categories`
      );
    }
  }

  // Every check above compares the documents to the report, and the report to
  // itself. None of them asks whether the report is still about *this* catalog —
  // so a figure can describe a catalog two and a half times smaller than the
  // one shipped, and stay internally consistent while being wrong. `total_hosts`
  // is the catalog size at the time of the audit, which makes the drift visible.
  //
  // A note rather than a failure: rerunning the audit needs the network and the
  // analysis venv, and `test/test.sh` must never require either. Blocking here
  // would only teach people to ignore the checker.
  const catalogSize = Object.keys(json("catalog.json").categories || {}).length;
  if (data.total_hosts && data.total_hosts !== catalogSize) {
    notes.push(
      `the reliability figures describe a ${fmt(data.total_hosts)}-host catalog, ` +
        `but catalog.json now has ${fmt(catalogSize)} — rerun scripts/analysis/ ` +
        `when convenient; the percentages are about the older catalog`
    );
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

  // The coverage table says how much of each category a score actually covers.
  // A per-class F1 describes the hosts that yielded text, and for `gaming` that
  // is 69 of 360 - a fact worth failing a build over if it goes missing.
  const coverage = data.coverage || {};
  const covRow = /^\| ([a-z]+) \| (\d+) \| (\d+) \| (\d+)% \|$/;
  let covRows = 0;
  for (const line of text.split("\n")) {
    const m = line.match(covRow);
    if (!m) continue;
    const [, category, inCatalog, measured, pct] = m;
    const actual = coverage[category];
    if (!actual) continue;
    covRows++;
    for (const [what, quoted, want] of [
      ["in catalog", Number(inCatalog), actual.in_catalog],
      ["measured", Number(measured), actual.measured],
      ["coverage", Number(pct), Math.round((actual.measured / actual.in_catalog) * 100)],
    ]) {
      if (quoted !== want) {
        problems.push(
          `docs/analysis/README.md: ${category} ${what} says ${quoted}, ${dataPath} has ${want}`
        );
      }
    }
  }
  if (Object.keys(coverage).length && covRows < Object.keys(coverage).length) {
    problems.push(
      `docs/analysis/README.md: coverage table has ${covRows} row(s), ` +
        `${dataPath} covers ${Object.keys(coverage).length} categories`
    );
  }

  // Why the unmeasured hosts are unmeasured has to add up. The three reasons
  // plus the measured count must equal the catalog, or a document has a gap
  // nobody can see: the first version of this paragraph said "445 return under
  // 100 bytes" against a 1,721 that summed to 2,166 and not 2,180, and no check
  // noticed the 14 hosts it had silently dropped.
  const unmeasured = data.unmeasured;
  if (unmeasured) {
    const parts =
      unmeasured.never_fetched +
      unmeasured.no_response +
      unmeasured.too_short +
      unmeasured.dropped_by_class_filter;
    if (parts + data.measured_hosts !== data.total_hosts) {
      problems.push(
        `${dataPath}: the unmeasured breakdown does not add up — ` +
          `${parts} + ${data.measured_hosts} measured != ${data.total_hosts} hosts`
      );
    }
    const num = (s) => Number(String(s).replace(/,/g, ""));
    for (const [pattern, want, what] of [
      [/([\d,]+) answer nothing at all/, unmeasured.no_response, "no response"],
      [/([\d,]+) return under \d+\s+characters/, unmeasured.too_short, "under min_text"],
    ]) {
      if (data.total_hosts >= 2000) {
        const m = text.match(pattern);
        if (!m) {
          problems.push(
            `docs/analysis/README.md: must state the ${what} count (${want}) when ` +
              `${dataPath} records it`
          );
        } else if (num(m[1]) !== want) {
          problems.push(
            `docs/analysis/README.md: says ${m[1]} hosts ${what}, ${dataPath} has ${want}`
          );
        }
      }
    }
  }

  // Model comparison rows must match the analysis output as well.
  const comparison = data.model_comparison || [];
  const comparisonByName = Object.fromEntries(comparison.map((row) => [row.model, row]));
  const comparisonRow = /^\| ([A-Za-z]+) \| ([\d.]+) \| ([\d.]+) \| ([\d.]+) \| ([\d.]+) \|$/;
  let comparisonRows = 0;
  for (const line of text.split("\n")) {
    const m = line.match(comparisonRow);
    if (!m || !(m[1] in comparisonByName)) continue;
    comparisonRows++;
    const [, model, accuracyValue, balancedValue, macroF1Value, weightedF1Value] = m;
    const actual = comparisonByName[model];
    for (const [field, quoted] of [
      ["accuracy", accuracyValue],
      ["balanced_accuracy", balancedValue],
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

  // The READMEs show the same comparison as a table. Each row and value has to
  // be the report's own numbers, or the figure a reader sees would be a
  // hand-typed copy that nothing recomputes.
  const readmeComparison = read("README.md");
  const fieldNames = ["accuracy", "balanced_accuracy", "macro_f1", "weighted_f1"];
  for (const file of ["README.md", "README.tr.md"]) {
    let rows = 0;
    for (const line of read(file).split("\n")) {
      const m = line.match(comparisonRow);
      if (!m || !(m[1] in comparisonByName)) continue;
      rows++;
      const actual = comparisonByName[m[1]];
      m.slice(2).forEach((quoted, i) => {
        const want = actual[fieldNames[i]].toFixed(3);
        if (Number(quoted) !== Number(want)) {
          problems.push(
            `${file}: ${m[1]} ${fieldNames[i]} says ${quoted}, ${dataPath} has ${want}`
          );
        }
      });
    }
    if (comparison.length && rows !== comparison.length) {
      problems.push(
        `${file}: the model comparison table has ${rows} row(s), ${dataPath} has ${comparison.length}`
      );
    }
  }

  // The headline quotes balanced accuracy next to accuracy, because the gap is
  // the finding. If the audit stops reporting it, the quote goes with it.
  const balancedPct = Math.round(data.balanced_accuracy * 100);
  const balancedQuote = `**balanced accuracy\n${balancedPct}%**`;
  if (comparison.length && !readmeComparison.includes(balancedQuote)) {
    problems.push(
      `README.md: should quote \`${balancedPct}%\` balanced accuracy — it is ${Math.round(
        data.balanced_accuracy * 100
      )}% against ${Math.round(data.accuracy * 100)}% accuracy, and the gap is why ` +
        `accuracy alone misleads`
    );
  }

  // The fold count is data-dependent now: `maps` has three examples, so the
  // matrix is 3-fold and a document saying 5 is describing a run that does not
  // exist. It drifted exactly that way — build-catalog-docs.py printed "5-fold"
  // while the same page's thin-class note printed "3-fold", and no check
  // compared either against the data.
  const folds = data.folds;
  if (folds) {
    // Every fold claim is checked, not only the ones phrased "N-fold
    // cross-validation": a document saying "cross-validates it (5-fold)" is
    // making the same claim and drifted the same way. The calibration step's
    // own inner CV is a different quantity that happens to share the wording,
    // so lines about it are named and skipped rather than left to pass by luck.
    for (const file of markdownFiles()) {
      const lines = read(file).split("\n");
      for (let i = 0; i < lines.length; i++) {
        if (/CalibratedClassifierCV|sigmoid/.test(lines[i])) continue;
        for (const m of lines[i].matchAll(/(\d+)-fold/g)) {
          if (Number(m[1]) !== folds) {
            problems.push(
              `${file}:${i + 1}: says ${m[1]}-fold cross-validation, ${dataPath} used ${folds} ` +
                `(the fold count follows the smallest category)`
            );
          }
        }
      }
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

/** 9. Durations the documents quote must be measured, not guessed. */
function checkMeasuredRuntimes() {
  // A quoted runtime is a claim that decays silently: nothing about the catalog
  // changing invalidates "~30 minutes", so the wrong number survives until a
  // person waits on it. The sweep records its own elapsed time, so the claim
  // can be checked against the run that produced it instead of against taste.
  const evidencePath = "evidence/dead-domain-sweep.json";
  if (!existsSync(join(ROOT, evidencePath))) {
    notes.push("no dead-domain sweep evidence — skipped the duration claims");
    return;
  }
  const sweep = json(evidencePath);
  const rounds = (sweep.rounds || []).filter((r) => r.complete && r.elapsed_seconds);
  if (!rounds.length) {
    problems.push(
      `${evidencePath}: no complete round records elapsed_seconds, so the documents' ` +
        `duration claims cannot be checked — rerun the sweep`
    );
    return;
  }

  // The slowest complete round is the number worth quoting: a reader planning
  // the work is sizing the worst case, not the luckiest one.
  const slowest = Math.max(...rounds.map((r) => r.elapsed_seconds));
  const minutes = Math.round(slowest / 60);

  let claims = 0;
  for (const file of markdownFiles()) {
    const text = read(file);
    const lines = text.split("\n");
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      if (!/probe-dead\.py/.test(line)) continue;
      // "# ~10 minutes" — an estimate attached to the sweep command. The
      // round-2 lines say "10 minutes later", which is the enforced minimum
      // gap, not a duration, and is checked separately below.
      const claimed = line.match(/~\s*(\d+)\s*minutes?/);
      if (claimed) {
        claims++;
        if (Number(claimed[1]) !== minutes) {
          problems.push(
            `${file}:${i + 1}: says the sweep takes ~${claimed[1]} minutes, ` +
              `${evidencePath} measured ${slowest.toFixed(0)}s (${minutes} minutes) — ` +
              `measure it, do not guess it`
          );
        }
      }
      // A host count on the same line must be the real catalog size.
      const hosts = line.match(/([\d,]+)\s+hosts/);
      if (hosts) {
        claims++;
        const total = Object.keys(json("catalog.json").categories || {}).length;
        if (Number(hosts[1].replace(/,/g, "")) !== total) {
          problems.push(
            `${file}:${i + 1}: says the sweep covers ${hosts[1]} hosts, ` +
              `catalog.json has ${total.toLocaleString("en-US")}`
          );
        }
      }
    }
  }
  notes.push(
    `checked ${claims} duration/count claim(s) against ${evidencePath}: ${slowest.toFixed(0)}s slowest complete round`
  );
}

/**
 * 9. The dead-domain sweep's evidence must still describe this catalog.
 *
 * The evidence is a point-in-time snapshot, and nothing re-ran it. Duration and
 * count claims were checked; coverage and agreement were not — so a host added
 * after the last sweep, or a host both rounds called dead that never left the
 * catalog, went unnoticed. Everything here is offline: it reads the evidence,
 * the seeds and the drop list, and never touches the network.
 */
function checkSweepEvidence() {
  const evidencePath = "evidence/dead-domain-sweep.json";
  if (!existsSync(join(ROOT, evidencePath))) {
    notes.push("no dead-domain sweep evidence — skipped the coverage checks");
    return;
  }
  const sweep = json(evidencePath);
  const seeds = json("seeds/categories.json");
  const catalog = json("catalog.json").categories || {};
  const drops = (json("rules.json").drop || {}).hosts || {};

  const rounds = (sweep.rounds || [])
    .filter((r) => r.complete && r.results)
    .sort((a, b) => a.round - b.round);
  if (rounds.length < 2) {
    problems.push(
      `${evidencePath}: ${rounds.length} complete round(s) with results — a host is only ` +
        `dead when two independent rounds agree, so at least two are required`
    );
    return;
  }

  // The sweep probes the seeds, so every seed host must appear in every
  // complete round. This is what makes the evidence go stale by *data*: add a
  // host and the sweep no longer covers the catalog, whatever the date says.
  const seedCount = Object.keys(seeds).length;
  for (const round of rounds) {
    const results = round.results;
    const missing = Object.keys(seeds).filter((h) => !(h in results));
    if (missing.length) {
      problems.push(
        `${evidencePath}: round ${round.round} covers ${Object.keys(results).length} host(s) ` +
          `but seeds/categories.json has ${seedCount} — ${missing.length} never verified ` +
          `(e.g. ${missing.slice(0, 3).join(", ")}) — rerun the sweep`
      );
    }
  }

  // A host both complete rounds call dead must not still be in the catalog:
  // either the proposal was applied or the evidence is being ignored.
  const [first, second] = rounds;

  // Both rounds must have asked the same resolvers. A round re-run after a
  // resolver was added produces a pair that cannot be compared — "dead in both"
  // would mean six NXDOMAINs in one round and nine in the other — and that is
  // exactly what a resolver addition leaves behind if only one round is rerun.
  const resetResolvers = (round) => {
    const sample = Object.values(round.results)[0];
    return sample ? Object.keys(sample.statuses || {}).sort() : [];
  };
  const r1 = resetResolvers(first);
  const r2 = resetResolvers(second);
  if (r1.join(",") !== r2.join(",")) {
    problems.push(
      `${evidencePath}: the rounds asked different resolvers — round ${first.round} used ` +
        `[${r1.join(", ")}], round ${second.round} used [${r2.join(", ")}] — rerun both ` +
        `rounds so the pair is comparable`
    );
  }

  const deadBoth = Object.keys(first.results).filter(
    (h) => first.results[h].decision === "dead" && second.results[h]?.decision === "dead"
  );
  const survivors = deadBoth.filter((h) => h in catalog);
  if (survivors.length) {
    problems.push(
      `${evidencePath}: ${survivors.length} host(s) dead in both rounds are still in ` +
        `catalog.json (e.g. ${survivors.slice(0, 3).join(", ")}) — apply the proposal`
    );
  }

  // A host the sweep probed that the seeds no longer has was removed; the
  // reason has to be on record or the removal cannot be explained later.
  const probed = new Set(Object.keys(first.results));
  const unrecorded = [...probed].filter((h) => !(h in seeds) && !(h in drops));
  if (unrecorded.length) {
    problems.push(
      `${evidencePath}: ${unrecorded.length} host(s) left seeds/categories.json without a ` +
        `rules.json → drop.hosts entry (e.g. ${unrecorded.slice(0, 3).join(", ")})`
    );
  }

  // The reason is what makes a removal explainable. "; ?" is the placeholder a
  // bug wrote for all 432 hosts removed on 2026-10-14, because the category was
  // deleted before the reason that was supposed to cite it was built.
  const placeholder = Object.entries(drops).filter(([, reason]) => /;\s*\?\s*$/.test(reason));
  if (placeholder.length) {
    problems.push(
      `rules.json → drop.hosts: ${placeholder.length} reason(s) end in "; ?" instead of the ` +
        `category (e.g. ${placeholder[0][0]}) — the category is the point of the record`
    );
  }

  const dates = rounds.map((r) => (r.generated || "").slice(0, 10)).filter(Boolean).sort();
  notes.push(
    `checked the dead-domain sweep evidence: ${rounds.length} complete round(s) over ` +
      `${seedCount} host(s)${dates.length ? `, latest ${dates.at(-1)}` : ""}, ` +
      `${deadBoth.length} dead in both rounds`
  );
}

/**
 * 10. The live sweep's evidence must still describe this catalog.
 *
 * The DNS sweep asks whether a name exists; the live sweep asks whether it
 * still serves a page, with a real browser (agent-browser + Lightpanda). Same
 * staleness risk, so the same coverage rule applies: the sweep probes the
 * seeds, so every seed host must appear in every complete round. Unlike the DNS
 * sweep, applying the proposal is discretionary — a 404 finance endpoint may
 * belong here anyway — so "a candidate is still in the catalog" is not a
 * failure; only an *unexplained* departure is.
 */
function checkLiveSweepEvidence() {
  const evidencePath = "evidence/live-sweep.json";
  if (!existsSync(join(ROOT, evidencePath))) {
    notes.push("no live sweep evidence — skipped the live coverage checks");
    return;
  }
  const sweep = json(evidencePath);
  const seeds = json("seeds/categories.json");
  const drops = (json("rules.json").drop || {}).hosts || {};

  const rounds = (sweep.rounds || [])
    .filter((r) => r.complete && r.results)
    .sort((a, b) => a.round - b.round);
  if (rounds.length < 2) {
    problems.push(
      `${evidencePath}: ${rounds.length} complete round(s) with results — a host is only ` +
        `proposed when two independent rounds agree, so at least two are required`
    );
    return;
  }

  // The evidence is only meaningful when it was the browser that produced it.
  // A run that fell back to a plain fetch would report an empty shell for every
  // modern page and call the catalog dead.
  for (const round of rounds) {
    if (round.engine !== "lightpanda") {
      problems.push(
        `${evidencePath}: round ${round.round} was produced by ` +
          `engine ${JSON.stringify(round.engine)}, not lightpanda — rerun it`
      );
    }
  }

  // Coverage: the sweep probes the seeds, so a host added since the last sweep
  // leaves the evidence unable to speak for the catalog.
  const seedCount = Object.keys(seeds).length;
  for (const round of rounds) {
    const results = round.results;
    const missing = Object.keys(seeds).filter((h) => !(h in results));
    if (missing.length) {
      problems.push(
        `${evidencePath}: round ${round.round} covers ${Object.keys(results).length} host(s) ` +
          `but seeds/categories.json has ${seedCount} — ${missing.length} never visited ` +
          `(e.g. ${missing.slice(0, 3).join(", ")}) — rerun the sweep`
      );
    }
    const sum = Object.values(round.counts || {}).reduce((a, b) => a + b, 0);
    if (round.counts && sum !== Object.keys(results).length) {
      problems.push(
        `${evidencePath}: round ${round.round} counts add up to ${sum} but it has ` +
          `${Object.keys(results).length} result(s) — the table in the report would lie`
      );
    }
  }

  // A host the sweep visited that the seeds no longer has was removed; the
  // reason has to be on record or the removal cannot be explained later.
  const probed = new Set(Object.keys(rounds[0].results));
  const unrecorded = [...probed].filter((h) => !(h in seeds) && !(h in drops));
  if (unrecorded.length) {
    problems.push(
      `${evidencePath}: ${unrecorded.length} host(s) left seeds/categories.json with no ` +
        `rules.json → drop.hosts entry (e.g. ${unrecorded.slice(0, 3).join(", ")})`
    );
  }

  const dates = rounds
    .map((r) => (r.generated || "").slice(0, 10))
    .filter(Boolean)
    .sort();
  notes.push(
    `checked the live sweep evidence: ${rounds.length} complete round(s) over ` +
      `${seedCount} host(s)${dates.length ? `, latest ${dates.at(-1)}` : ""}`
  );
}

/**
 * 11. The category treemap in README.md must match the catalog.
 *
 * A treemap of "this category, this many hosts" is exactly the kind of figure
 * that drifts quietly: nothing about a host changing makes the numbers on the
 * diagram look wrong. So the counts are read back out of the mermaid block and
 * compared, category by category, against catalog.json.
 */
function checkRegistrationEvidence() {
  const evidencePath = "evidence/registration-verify.json";
  if (!existsSync(join(ROOT, evidencePath))) {
    notes.push("no registration-verify evidence — skipped the registration checks");
    return;
  }
  const sweep = json(evidencePath);
  const seeds = json("seeds/categories.json");
  const drops = (json("rules.json").drop || {}).hosts || {};

  const rounds = (sweep.rounds || [])
    .filter((r) => r.complete && r.results)
    .sort((a, b) => a.round - b.round);
  if (rounds.length < 2) {
    problems.push(
      `${evidencePath}: ${rounds.length} complete round(s) — at least two are required`
    );
    return;
  }
  for (const round of rounds) {
    const results = round.results;
    const missing = Object.keys(seeds).filter((h) => !(h in results));
    if (missing.length) {
      problems.push(
        `${evidencePath}: round ${round.round} covers ${Object.keys(results).length} host(s) ` +
          `but seeds/categories.json has ${Object.keys(seeds).length} — ${missing.length} never visited`
      );
    }
  }
  const probed = new Set(Object.keys(rounds[0].results));
  const unrecorded = [...probed].filter((h) => !(h in seeds) && !(h in drops));
  if (unrecorded.length) {
    problems.push(
      `${evidencePath}: ${unrecorded.length} host(s) left seeds/categories.json with no ` +
        `rules.json -> drop.hosts entry`
    );
  }
  notes.push(`checked registration-verify evidence: ${rounds.length} complete round(s)`);
}

function checkCategoryTreemap() {
  const text = read("README.md");
  const block = text.match(/```mermaid\n(treemap-beta[\s\S]*?)```/);
  if (!block) {
    notes.push("no category treemap in README.md — skipped the treemap check");
    return;
  }
  const catalog = json("catalog.json");
  const counts = {};
  for (const category of Object.values(catalog.categories || {})) {
    counts[category] = (counts[category] || 0) + 1;
  }

  const quoted = {};
  for (const m of block[1].matchAll(/"([a-z]+)":\s*([\d,]+)/g)) {
    quoted[m[1]] = Number(m[2].replace(/,/g, ""));
  }

  let checked = 0;
  for (const category of Object.keys(counts).sort()) {
    if (!(category in quoted)) {
      problems.push(`README.md: the category treemap has no \`${category}\` leaf`);
      continue;
    }
    checked++;
    if (quoted[category] !== counts[category]) {
      problems.push(
        `README.md: the treemap says \`${category}\` has ${quoted[category]}, ` +
          `catalog.json has ${counts[category]}`
      );
    }
  }
  for (const category of Object.keys(quoted)) {
    if (!(category in counts)) {
      problems.push(`README.md: the treemap has \`${category}\`, which is not a category`);
    }
  }

  // Colour: every leaf must carry its own class (`:::c_<category>`) and that
  // class must resolve to the palette file's tint, or the diagram would show
  // the wrong legend without any count looking wrong.
  const palette = categoryColors();
  const classes = {};
  for (const m of block[1].matchAll(/classDef c_([a-z]+) fill:(#[0-9A-Fa-f]{6})/g)) {
    classes[m[1]] = m[2];
  }
  const leaves = {};
  for (const m of block[1].matchAll(/"([a-z]+)":\s*[\d,]+:::c_([a-z]+)/g)) {
    leaves[m[1]] = m[2];
  }
  let colored = 0;
  for (const category of Object.keys(counts)) {
    if (leaves[category] !== category) {
      problems.push(
        `README.md: the treemap leaf \`${category}\` is not coloured by its own class`
      );
      continue;
    }
    colored++;
    const expected = (palette.categories[category] || {}).tint;
    const actual = classes[category];
    if (!actual) {
      problems.push(`README.md: the treemap has no classDef for \`${category}\``);
    } else if (expected && actual.toUpperCase() !== expected.toUpperCase()) {
      problems.push(
        `README.md: the treemap colours \`${category}\` ${actual}, ` +
          `reference/category-colors.json says ${expected}`
      );
    }
  }
  notes.push(`checked ${checked} category count(s) and ${colored} colour(s) in the README treemap`);
}

/** The palette a category's colour comes from, read once. */
function categoryColors() {
  const path = "reference/category-colors.json";
  if (!existsSync(join(ROOT, path))) return { categories: {}, foldedTail: null };
  return json(path);
}

/**
 * The category palette must cover the catalog.
 *
 * `reference/category-colors.json` is the one place a category's colour lives,
 * copied from the iOS app so it does not have to be remembered. The treemap and
 * pie read it. A category added to the catalog without a colour would fall back
 * to grey and say the wrong thing quietly, so every catalog category needs a
 * well-formed tint.
 */
function checkCategoryColors() {
  const path = "reference/category-colors.json";
  if (!existsSync(join(ROOT, path))) {
    problems.push(`${path}: missing — the category charts read their colours from it`);
    return;
  }
  const palette = json(path);
  const { counts } = categoryCounts();
  const colors = palette.categories || {};
  const hex = /^#[0-9A-Fa-f]{6}$/;
  for (const [name, entry] of Object.entries(colors)) {
    if (!hex.test(entry.tint || "")) {
      problems.push(
        `${path}: \`${name}\` has no valid tint (got ${JSON.stringify(entry.tint)})`
      );
    }
    if (entry.tintText && !hex.test(entry.tintText)) {
      problems.push(
        `${path}: \`${name}\` has an invalid tintText (got ${JSON.stringify(entry.tintText)})`
      );
    }
  }
  const missing = Object.keys(counts).filter((c) => !(c in colors)).sort();
  if (missing.length) {
    problems.push(
      `${path}: no colour for ${missing.join(", ")} — add it so the charts stay in step`
    );
  }
  notes.push(
    `checked ${Object.keys(colors).length} category colour(s) cover the catalog`
  );
}

function categoryCounts() {
  const catalog = json("catalog.json");
  const counts = {};
  for (const category of Object.values(catalog.categories || {})) {
    counts[category] = (counts[category] || 0) + 1;
  }
  return { catalog, counts };
}

/** The pie of the category share must match the catalog. */
function checkCategoryPie() {
  const text = read("README.md");
  const block = text.match(/```mermaid\n((?:%%\{[^\n]*\}%%\n)?pie title Catalog by category[\s\S]*?)```/);
  if (!block) {
    notes.push("no category pie in README.md — skipped");
    return;
  }
  const { counts } = categoryCounts();
  const quoted = {};
  const order = [];
  let otherQuoted = null;
  let otherCount = null;
  for (const m of block[1].matchAll(/^\s*"([^"]+)"\s*:\s*(\d+)/gm)) {
    const label = m[1];
    const value = Number(m[2]);
    order.push(label);
    const tail = label.match(/^other \((\d+) smaller\)$/);
    if (tail) {
      otherQuoted = value;
      otherCount = Number(tail[1]);
    } else {
      quoted[label] = value;
    }
  }
  let checked = 0;
  for (const [category, value] of Object.entries(quoted)) {
    checked++;
    if (counts[category] !== value) {
      problems.push(
        `README.md: the pie says \`${category}\` has ${value}, catalog.json has ${counts[category] ?? 0}`
      );
    }
  }
  if (otherQuoted !== null) {
    const rest = Object.keys(counts).filter((c) => !(c in quoted));
    const restTotal = rest.reduce((sum, c) => sum + counts[c], 0);
    if (otherQuoted !== restTotal) {
      problems.push(
        `README.md: the pie "other" is ${otherQuoted}, the remaining categories total ${restTotal}`
      );
    }
    if (otherCount !== rest.length) {
      problems.push(
        `README.md: the pie "other" counts ${otherCount} categories, there are ${rest.length}`
      );
    }
  }

  // Colour: the init directive lists `pieN` in slice order, so the N-th slice
  // and the N-th colour must line up with the palette, or the legend would
  // disagree with the diagram.
  const palette = categoryColors();
  const init = text.match(/%%\{init:[^\n]*?('pie1':[^\n]*?)\}%%/);
  const pieColors = init ? [...init[1].matchAll(/'pie\d+':'(#[0-9A-Fa-f]{6})'/g)].map((m) => m[1]) : [];
  if (pieColors.length !== order.length) {
    problems.push(
      `README.md: the pie has ${order.length} slice(s) but ${pieColors.length} colour(s)`
    );
  } else {
    order.forEach((label, i) => {
      const expected = label.startsWith("other (")
        ? palette.foldedTail
        : (palette.categories[label] || {}).tint;
      if (expected && pieColors[i].toUpperCase() !== expected.toUpperCase()) {
        problems.push(
          `README.md: the pie slice \`${label}\` is ${pieColors[i]}, ` +
            `reference/category-colors.json says ${expected}`
        );
      }
    });
  }
  notes.push(`checked ${checked} pie slice(s) + the folded tail, all tinted from the palette`);
}

/**
 * A removed host must not still be in the seeds.
 *
 * `rules.json → drop.hosts` is the ledger of every host this project removed
 * and why. The seeds are what the generator reads. A host in both means a
 * removal is being silently undone: `generate.py` drops it from `catalog.json`
 * without saying so, and the next person finds a seed that appears to do
 * nothing. The one thing the ledger must never allow is a decision reversing
 * itself.
 */
function checkDropListSeparation() {
  const seeds = json("seeds/categories.json");
  const drops = (json("rules.json").drop || {}).hosts || {};
  const overlap = Object.keys(drops).filter((h) => h in seeds);
  if (overlap.length) {
    problems.push(
      `rules.json → drop.hosts: ${overlap.length} host(s) were removed but are back in ` +
        `seeds/categories.json (e.g. ${overlap.slice(0, 3).join(", ")}) — a removal ` +
        `being silently undone; keep it in exactly one of the two`
    );
    return;
  }
  notes.push(`checked ${Object.keys(drops).length} dropped host(s) are absent from the seeds`);
}

/** The headline badges must match the catalog. */
function checkCatalogBadges() {
  const text = read("README.md");
  const block = text.match(/<!-- catalog-badges:start -->([\s\S]*?)<!-- catalog-badges:end -->/);
  if (!block) {
    notes.push("no catalog badges in README.md — skipped");
    return;
  }
  const { catalog, counts } = categoryCounts();
  const badges = {};
  for (const m of block[1].matchAll(/badge\/([a-z]+)-([\d]+)-[a-z]+/g)) {
    badges[m[1]] = Number(m[2]);
  }
  const drops = ((json("rules.json").drop || {}).hosts) || {};
  const expected = {
    hosts: Object.keys(catalog.categories || {}).length,
    categories: Object.keys(counts).length,
    services: (catalog.services || []).length,
    removed: Object.keys(drops).length,
  };
  for (const [name, value] of Object.entries(expected)) {
    if (badges[name] === undefined) {
      problems.push(`README.md: no \`${name}\` badge`);
    } else if (badges[name] !== value) {
      problems.push(`README.md: the \`${name}\` badge says ${badges[name]}, expected ${value}`);
    }
  }
  notes.push(`checked ${Object.keys(expected).length} catalog badge(s)`);
}

/** The verification chart must match the dead-domain sweep evidence. */
function checkVerificationStatus() {  const text = read("README.md");
  const block = text.match(/<!-- verification-status:start -->([\s\S]*?)<!-- verification-status:end -->/);
  if (!block) {
    notes.push("no verification-status block in README.md — skipped");
    return;
  }
  const path = "evidence/dead-domain-sweep.json";
  if (!existsSync(join(ROOT, path))) {
    notes.push("no dead-domain-sweep evidence — skipped the verification chart");
    return;
  }
  const sweep = json(path);
  const complete = (sweep.rounds || []).filter((r) => r.complete && r.counts);
  if (!complete.length) {
    notes.push("no complete dead-domain round — skipped the verification chart");
    return;
  }
  const counts = complete[complete.length - 1].counts;
  const order = ["alive", "nodata", "servfail", "dead", "unknown"];
  const names = (block[1].match(/x-axis \[([^\]]+)\]/) || [])[1] || "";
  const values = (block[1].match(/bar \[([^\]]+)\]/) || [])[1] || "";
  const nameList = names.split(",").map((s) => s.trim());
  const valueList = values.split(",").map((s) => Number(s.trim()));
  let checked = 0;
  nameList.forEach((name, i) => {
    if (!order.includes(name)) {
      problems.push(`README.md: the verification chart has an unknown verdict \`${name}\``);
      return;
    }
    checked++;
    if (counts[name] !== valueList[i]) {
      problems.push(
        `README.md: the verification chart says \`${name}\` is ${valueList[i]}, ` +
          `the last sweep round has ${counts[name]}`
      );
    }
  });
  notes.push(`checked ${checked} verification verdict(s) against the DNS sweep`);
}

/**
 * README.tr.md is the Turkish translation of README.md and must carry the same
 * generated blocks.
 *
 * README.md is the source of truth; the Turkish file mirrors it. The generator
 * writes the identical block content to both, so the counts cannot drift by
 * language. This compares the two files' marked blocks directly, so a hand-edit
 * that changes one and not the other fails the build rather than shipping two
 * documents that disagree about the catalog.
 */
function checkTurkishMirror() {
  const tr = "README.tr.md";
  if (!existsSync(join(ROOT, tr))) {
    problems.push(`${tr} is missing — it mirrors README.md`);
    return;
  }
  const enText = read("README.md");
  const trText = read(tr);
  const block = (text, name) => {
    const m = text.match(
      new RegExp(`<!-- ${name}:start -->([\\s\\S]*?)<!-- ${name}:end -->`)
    );
    return m ? m[1].trim() : null;
  };
  let checked = 0;
  for (const name of [
    "catalog-badges",
    "category-treemap",
    "category-pie",
    "verification-status",
  ]) {
    const expected = block(enText, name);
    if (expected === null) continue;
    const actual = block(trText, name);
    if (actual === null) {
      problems.push(`${tr}: missing the ${name} block that README.md has`);
      continue;
    }
    checked++;
    if (actual !== expected) {
      problems.push(
        `${tr}: the ${name} block differs from README.md — both are written by ` +
          `build-catalog-docs.py and must stay identical`
      );
    }
  }
  notes.push(`checked README.tr.md mirrors ${checked} generated block(s) from README.md`);
  // The generated blocks are only part of the file. A section added to one
  // language and not the other drifts silently, so the shape is compared too:
  // the same number of level-2/3 headings and the same number of diagrams.
  const count = (text, re) => (text.match(re) || []).length;
  for (const [what, re] of [
    ["level-2 heading", /^## /gm],
    ["level-3 heading", /^### /gm],
    ["mermaid diagram", /^```mermaid/gm],
  ]) {
    const en = count(enText, re);
    const tr = count(trText, re);
    if (en !== tr) {
      problems.push(
        `${tr}: has ${tr} ${what}(s), README.md has ${en} — the translation must ` +
          `mirror it section for section`
      );
    }
  }
}

/**
 * 20. The seeds provenance is current, and the pages that quote it agree.
 *
 * `evidence/seeds-only.json` is generated by `scripts/catalog/seeds-provenance.py`
 * from `catalog.json`, `rules.json` and the committed source caches. Re-run the
 * script's `--check` so the file cannot drift, then confirm the figures
 * `docs/INGEST.md` and `docs/FOUNDING.md` quote are the ones the file holds.
 */
function checkSeedsProvenance() {
  const script = "scripts/catalog/seeds-provenance.py";
  try {
    execFileSync("python3", [join(ROOT, script), "--check"], { cwd: ROOT, stdio: "pipe" });
  } catch (error) {
    const detail = `${error.stdout || ""}${error.stderr || ""}`.trim().split("\n")[0];
    problems.push(`seeds provenance: ${detail || "scripts/catalog/seeds-provenance.py --check failed"}`);
    return;
  }
  const data = json("evidence/seeds-only.json");
  const n = (v) => v.toLocaleString("en-US");
  const figures = {
    "docs/INGEST.md": [
      n(data.attributed_to_rule),
      n(data.attributed_to_source),
      n(data.unattributed.public_institution.count),
      n(data.unattributed.hand_entered.count),
      n(data.unattributed.total),
    ],
    "docs/FOUNDING.md": [
      n(data.catalog_hosts),
      n(data.attributed_to_rule),
      n(data.attributed_to_source),
      n(data.unattributed.public_institution.count),
      n(data.unattributed.hand_entered.count),
      n(data.unattributed.total),
    ],
  };
  for (const [file, values] of Object.entries(figures)) {
    const text = read(file);
    for (const value of values) {
      if (!text.includes(value)) {
        problems.push(`${file}: does not quote the seeds-provenance figure ${value}`);
      }
    }
  }
  notes.push(
    `checked seeds provenance (${n(data.unattributed.total)} unattributed of ${n(data.catalog_hosts)})`
  );
}

function checkHandAdded() {
  // Door 3 records who/when/why per host in seeds/hand-added.json; the rules live
  // in catalog-core so the build and the tests share them. This just runs them.
  try {
    execFileSync("python3", [join(ROOT, "scripts/catalog/check-hand-added.py")], {
      cwd: ROOT,
      stdio: "pipe",
    });
  } catch (error) {
    const detail = `${error.stdout || ""}${error.stderr || ""}`.trim().split("\n")[0];
    problems.push(`hand-added provenance: ${detail || "scripts/catalog/check-hand-added.py failed"}`);
    return;
  }
  const added = json("seeds/hand-added.json").added || {};
  const n = Object.keys(added).length;
  notes.push(`checked hand-added provenance (${n} host(s) with by/at/reason)`);
}

function checkPendingBacklog() {
  // harvest.py prints the hosts no rule matched, but only for the run that just
  // happened; NEEDS-REVIEW.md kept the ones a person investigated. This pairs the
  // machine-recorded backlog with the document that promises it, so "how many open
  // questions are there?" has an answer that outlives a terminal.
  const script = "scripts/sources/pending.py";
  try {
    execFileSync("python3", [join(ROOT, script), "--check"], { cwd: ROOT, stdio: "pipe" });
  } catch (error) {
    const detail = `${error.stdout || ""}${error.stderr || ""}`.trim().split("\n")[0];
    problems.push(`pending backlog: ${detail || "scripts/sources/pending.py --check failed"}`);
    return;
  }
  const data = json("evidence/pending-source-hosts.json");
  const n = (v) => v.toLocaleString("en-US");
  const text = read("docs/NEEDS-REVIEW.md");
  for (const [what, value] of [
    ["distinct hosts", n(data.unique_hosts)],
    ["source mentions", n(data.mentions)],
  ]) {
    if (!text.includes(value)) {
      problems.push(
        `docs/NEEDS-REVIEW.md: does not quote the backlog's ${what} figure ${value}`
      );
    }
  }
  notes.push(`checked the review backlog (${n(data.unique_hosts)} hosts / ${n(data.mentions)} mentions)`);
}

for (const check of [
  checkLinks,
  checkScriptNames,
  checkSourceIds,
  checkGeneratedDocs,
  checkCategoryTable,
  checkCoverageDoc,
  checkLicenseGate,
  checkDirectoryReadmes,
  checkAnalysisFigures,
  checkMeasuredRuntimes,
  checkSweepEvidence,
  checkDropListSeparation,
  checkLiveSweepEvidence,
  checkRegistrationEvidence,
  checkCategoryTreemap,
  checkCategoryColors,
  checkCategoryPie,
  checkCatalogBadges,
  checkVerificationStatus,
  checkTurkishMirror,
  checkSeedsProvenance,
  checkHandAdded,
  checkPendingBacklog,
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
