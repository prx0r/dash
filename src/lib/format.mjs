import { manifest, publicItem } from './data.mjs';

function line(label, value) {
  if (value === undefined || value === null || value === '') return '';
  if (Array.isArray(value)) return value.length ? `**${label}:** ${value.join(', ')}` : '';
  return `**${label}:** ${value}`;
}

export function itemToMarkdown(raw, baseUrl = manifest.canonical_base_url) {
  const item = publicItem(raw, baseUrl);
  const out = [`# ${item.title}`, '', item.summary || '', ''];
  for (const s of [
    line('Type', item.kind), line('Status', item.status), line('Platform', item.platform),
    line('Category', item.category), line('Tags', item.tags), line('Maintainers', item.maintainers)
  ]) if (s) out.push(s, '');

  if (item.capabilities?.length) {
    out.push('## Capabilities', '', ...item.capabilities.map((x) => `- ${x}`), '');
  }
  if (item.agent_surfaces?.length) {
    out.push('## Agent-facing surfaces', '', ...item.agent_surfaces.map((x) => `- ${x}`), '');
  }
  if (item.machine_notes?.length) {
    out.push('## Machine notes', '', ...item.machine_notes.map((x) => `- ${x}`), '');
  }
  if (item.quick_actions?.length) {
    out.push('## Quick actions', '', ...item.quick_actions.map((x) => `- ${x}`), '');
  }
  if (item.steps?.length) {
    out.push('## Steps', '', ...item.steps.map((x, idx) => `${idx + 1}. ${x}`), '');
  }
  if (item.url) out.push('## Primary resource', '', item.url, '');
  if (item.sources?.length) {
    out.push('## Sources', '');
    for (const s of item.sources) {
      out.push(`- [${s.title}](${s.url}) — ${s.authority}; verified ${s.last_verified}`);
    }
    out.push('');
  }
  out.push('## Machine alternates', '', `- JSON: ${item.alternates.json}`, `- Markdown: ${item.alternates.markdown}`, `- MCP: ${baseUrl}/mcp`, '');
  return out.join('\n');
}

export function itemToHtml(raw, baseUrl = manifest.canonical_base_url) {
  const item = publicItem(raw, baseUrl);
  const esc = (s='') => String(s).replace(/[&<>\"]/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
  const list = (title, values) => !values?.length ? '' : `<section><h2>${esc(title)}</h2><ul>${values.map(v => `<li>${esc(v)}</li>`).join('')}</ul></section>`;
  const sources = !item.sources?.length ? '' : `<section><h2>Sources</h2><ul>${item.sources.map(s => `<li><a href="${esc(s.url)}">${esc(s.title)}</a><span class="source-meta">${esc(s.authority)} · verified ${esc(s.last_verified)}</span></li>`).join('')}</ul></section>`;
  const steps = !item.steps?.length ? '' : `<section><h2>Steps</h2><ol>${item.steps.map(v => `<li>${esc(v)}</li>`).join('')}</ol></section>`;
  return `<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>${esc(item.title)} · AgentCom.org</title><meta name="description" content="${esc(item.summary)}">
<link rel="canonical" href="${esc(item.canonical)}"><link rel="alternate" type="application/json" href="${esc(item.alternates.json)}"><link rel="alternate" type="text/markdown" href="${esc(item.alternates.markdown)}"><link rel="stylesheet" href="/styles.css"></head>
<body><header class="topbar"><a class="brand" href="/"><span>AGENT</span>COM<span class="dot">.ORG</span></a><nav><a href="/#guides">Guides</a><a href="/#protocols">Protocols</a><a href="/#machine">For agents</a></nav></header>
<main class="detail"><a class="back" href="/">← AgentCom index</a><p class="eyebrow">${esc(item.kind)}</p><h1>${esc(item.title)}</h1><p class="lede">${esc(item.summary)}</p>
<div class="chips">${(item.tags||[]).map(x=>`<span>${esc(x)}</span>`).join('')}</div>
<div class="machine-links"><a href="${esc(item.alternates.json)}">JSON</a><a href="${esc(item.alternates.markdown)}">Markdown</a><a href="/mcp">MCP endpoint</a></div>
${list('Capabilities', item.capabilities)}${list('Agent-facing surfaces', item.agent_surfaces)}${list('Machine notes', item.machine_notes)}${list('Quick actions', item.quick_actions)}${steps}${item.url?`<section><h2>Primary resource</h2><p><a href="${esc(item.url)}">${esc(item.url)}</a></p></section>`:''}${sources}</main></body></html>`;
}
