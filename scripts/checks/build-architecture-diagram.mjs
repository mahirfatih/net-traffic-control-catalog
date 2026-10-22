#!/usr/bin/env node
/**
 * build-architecture-diagram.mjs — regenerate docs/diagrams/architecture/architecture.html
 * from the `architecture-diagram` skill template plus the Source outline in
 * docs/architecture/source.json.
 *
 *   node scripts/checks/build-architecture-diagram.mjs
 *   node scripts/checks/build-architecture-diagram.mjs --check   # exit 1 when stale
 *
 * The HTML is a generated artifact. Edit source.json, then run this. Never
 * hand-edit the HTML: the next build overwrites it.
 */

import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { execSync } from 'node:child_process';

const repoRoot = execSync('git rev-parse --show-toplevel', { encoding: 'utf8' }).trim();
const srcPath = path.join(repoRoot, 'docs/architecture/source.json');
const outPath = path.join(repoRoot, 'docs/diagrams/architecture/architecture.html');
const SKILL = path.join(os.homedir(), '.config/opencode/skills/architecture-diagram');
const templatePath = path.join(SKILL, 'assets/template.html');

const ICONS = {
  user: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>',
  orch: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>',
  compute: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="4" y="4" width="16" height="16" rx="2"/><rect x="9" y="9" width="6" height="6"/><line x1="9" y1="1" x2="9" y2="4"/><line x1="15" y1="1" x2="15" y2="4"/><line x1="9" y1="20" x2="9" y2="23"/><line x1="15" y1="20" x2="15" y2="23"/><line x1="20" y1="9" x2="23" y2="9"/><line x1="20" y1="14" x2="23" y2="14"/><line x1="1" y1="9" x2="4" y2="9"/><line x1="1" y1="14" x2="4" y2="14"/></svg>',
  embed: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>',
  vector: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/></svg>',
  seed: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>'
};

const COLOR = {
  user: '--c-user', orch: '--c-orch', compute: '--c-compute',
  embed: '--c-embed', vector: '--c-vector', seed: '--c-seed'
};

const esc = (s) => String(s)
  .replace(/`/g, '\\`')
  .replace(/\$\{/g, '\\${')
  .replace(/<\/script>/gi, '<\\/script>')
  .replace(/<\/style>/gi, '<\\/style>');

function build(src, template) {
  let t = template;

  // 1. title + header
  t = t.replace(/<title>[^<]*<\/title>/, `<title>${src.system} — Architecture</title>`);
  t = t.replace('{{PROJECT_LABEL}}', src.projectLabel ?? 'architecture · didactic walkthrough');
  t = t.replace('{{SYSTEM_NAME}}', src.system);
  t = t.replace('{{TAGLINE}}', src.tagline ?? '');
  t = t.replace('{{SUBTITLE}}', src.subtitle ?? '');

  // 2. mode buttons
  const modeButtons = src.modes.map((m, i) =>
    `    <button data-mode="${m}" aria-pressed="${i === 0}">${m.toUpperCase()} <span class="pill">${esc(src.mode_hints?.[m] ?? m)}</span></button>`
  ).join('\n');
  t = t.replace(/(<div class="modepick" role="group"[^>]*>)[\s\S]*?\n  <\/div>/,
    `$1\n${modeButtons}\n  </div>`);

  // 3. flow tabs
  const flowTabs = src.flows.map((f, i) =>
    `    <button class="flowtab" data-flow="${f.key}" aria-pressed="${i === 0}"><span class="num">${i + 1}</span> ${esc(f.short ?? f.name)}</button>`
  ).join('\n');
  t = t.replace(/(<nav class="flowtabs"[^>]*>)[\s\S]*?<\/nav>/, `$1\n${flowTabs}\n  </nav>`);

  // 4. nodes — inserted right after the wires <svg> inside the stage
  const stageStart = t.indexOf('<div class="stage" id="stage">');
  if (stageStart < 0) throw new Error('stage container not found in template');
  // In the template the wires <svg> comes AFTER the node divs, so the node
  // block is everything from the stage open tag to that svg.
  const wiresOpen = t.indexOf('<svg class="wires"', stageStart);
  if (wiresOpen < 0) throw new Error('wires <svg> not found in stage');
  const stageEnd = wiresOpen;

  const nodeHtml = src.nodes.map((n) => {
    const label = n.label.default ?? Object.values(n.label)[0];
    const tech = n.tech.default ?? Object.values(n.tech)[0];
    const portDefault = n.port.default ?? Object.values(n.port)[0];
    const portAttrs = src.modes
      .map((m) => ` data-port-${m}="${esc(n.port[m] ?? portDefault)}"`)
      .join('');
    const labelAttrs = Object.entries(n.label).filter(([k]) => k !== 'default')
      .map(([k, v]) => ` data-label-${k}="${esc(v)}"`).join('');
    const techAttrs = Object.entries(n.tech).filter(([k]) => k !== 'default')
      .map(([k, v]) => ` data-tech-${k}="${esc(v)}"`).join('');
    return `      <div class="node" data-role="${n.role}" data-id="${n.id}" style="${n.position}">
        <div class="icon">${ICONS[n.role] ?? ICONS.orch}</div>
        <div class="label"${labelAttrs}>${esc(label)}</div>
        <div class="tech"${techAttrs}>${esc(tech)}</div>
        <div class="port"${portAttrs}>${esc(portDefault)}</div>
        <span class="step-badge">·</span>
      </div>`;
  }).join('\n\n');

  t = `${t.slice(0, stageStart + '<div class="stage" id="stage">'.length)}\n\n${nodeHtml}\n\n${t.slice(stageEnd)}`;

  // 5. flows object
  const roleOf = Object.fromEntries(src.nodes.map((n) => [n.id, n.role]));
  const flowBlocks = src.flows.map((f) => {
    const steps = f.steps.map((s) => {
      const color = COLOR[roleOf[s.to] ?? 'orch'];
      return `      {
        from:"${s.from}", to:"${s.to}", color:"${color}",
        title:${JSON.stringify(s.title)},
        route:${JSON.stringify(s.route ?? '')},
        desc:${JSON.stringify(s.desc ?? '')},
        payload:\`${esc(s.payload ?? '')}\`,
        chips:${JSON.stringify(s.chips ?? [])}
      }`;
    }).join(',\n');
    const onlyMode = f.onlyMode ? `\n    onlyMode: "${f.onlyMode}",` : '';
    return `  ${f.key}: {
    name: ${JSON.stringify(f.name)},
    note: ${JSON.stringify(f.note ?? '')},${onlyMode}
    steps: [
${steps}
    ]
  }`;
  }).join(',\n\n');
  t = t.replace(/const flows = \{[\s\S]*?\n\};/, `const flows = {\n${flowBlocks}\n};`);

  // 6. initial state
  t = t.replace(/mode: "offline",(\s*)\/\/ ← if you renamed mode keys, update this/, `mode: "${src.modes[0]}",$1`);
  t = t.replace(/flow: "flow_a",(\s*)\/\/ ← if you renamed flow keys, update this/, `flow: "${src.flows[0].key}",$1`);

  // 7. legend
  if (src.legend) {
    const items = src.legend.map((l) =>
      `    <span class="item"><span class="swatch" style="background:var(--c-${l.role})"></span> ${esc(l.label)}</span>`
    ).join('\n');
    t = t.replace(/(<div class="legend" role="group"[^>]*>)[\s\S]*?(\n  <\/div>)/, `$1\n${items}$2`);
  }

  // 8. the template's own placeholder-hint comment is documentation, not content
  t = t.replace(/\{\{PLACEHOLDERS?\}\}/g, 'PLACEHOLDERS');

  const leftover = [...new Set([...t.matchAll(/\{\{([A-Z_]+)\}\}/g)].map((m) => m[1]))];
  if (leftover.length) throw new Error(`leftover placeholders: ${leftover.join(', ')}`);

  return t;
}

const src = JSON.parse(fs.readFileSync(srcPath, 'utf8'));
const template = fs.readFileSync(templatePath, 'utf8');
const html = build(src, template);

const check = process.argv.includes('--check');
if (check) {
  const current = fs.existsSync(outPath) ? fs.readFileSync(outPath, 'utf8') : '';
  if (current !== html) {
    console.error(`❌ ${path.relative(repoRoot, outPath)} is stale — run: node scripts/checks/build-architecture-diagram.mjs`);
    process.exit(1);
  }
  console.log(`✅ ${path.relative(repoRoot, outPath)} is current`);
  process.exit(0);
}

fs.writeFileSync(outPath, html);
console.log(`✅ ${path.relative(repoRoot, outPath)} — ${src.nodes.length} nodes, ${src.flows.length} flows, ${src.modes.length} modes`);
