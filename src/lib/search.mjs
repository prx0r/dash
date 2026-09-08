import { allItems, publicItem } from './data.mjs';

const fields = ['title', 'summary', 'slug', 'kind', 'status', 'category', 'platform'];

function searchable(item) {
  const chunks = fields.map((k) => item[k]).filter(Boolean);
  chunks.push(...(item.tags || []));
  chunks.push(...(item.capabilities || []));
  chunks.push(...(item.agent_surfaces || []));
  chunks.push(...(item.quick_actions || []));
  chunks.push(...(item.steps || []));
  return chunks.join(' ').toLowerCase();
}

function score(item, terms) {
  const title = (item.title || '').toLowerCase();
  const tags = (item.tags || []).join(' ').toLowerCase();
  const hay = searchable(item);
  let n = 0;
  for (const t of terms) {
    if (title.includes(t)) n += 8;
    if (tags.includes(t)) n += 5;
    if ((item.slug || '').includes(t)) n += 4;
    if (hay.includes(t)) n += 2;
  }
  return n;
}

export function search(query, { kind, limit = 20, baseUrl } = {}) {
  const q = String(query || '').trim().toLowerCase();
  const terms = q.split(/\s+/).filter(Boolean);
  let source = kind ? allItems.filter((i) => i.kind === kind) : allItems;
  if (!terms.length) return source.slice(0, limit).map((i) => publicItem(i, baseUrl));
  return source
    .map((item) => ({ item, score: score(item, terms) }))
    .filter((x) => x.score > 0)
    .sort((a, b) => b.score - a.score || a.item.title.localeCompare(b.item.title))
    .slice(0, limit)
    .map(({ item, score }) => ({ ...publicItem(item, baseUrl), relevance: score }));
}
