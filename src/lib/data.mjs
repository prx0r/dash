import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const dataDir = path.resolve(here, '../data');

function read(name) {
  return JSON.parse(fs.readFileSync(path.join(dataDir, `${name}.json`), 'utf8'));
}

export const manifest = read('manifest');
export const protocols = read('protocols');
export const platforms = read('platforms');
export const guides = read('guides');
export const resources = read('resources');
export const glossary = read('glossary');
export const allItems = [...protocols, ...platforms, ...guides, ...resources];

export function getItem(slug) {
  return allItems.find((item) => item.slug === slug) || null;
}

export function itemsByKind(kind) {
  return allItems.filter((item) => item.kind === kind);
}

export function provenance(item) {
  return (item.sources || []).map((s) => ({
    title: s.title,
    url: s.url,
    authority: s.authority,
    last_verified: s.last_verified
  }));
}

export function publicItem(item, baseUrl = manifest.canonical_base_url) {
  const canonical = `${baseUrl}/r/${item.slug}`;
  return {
    ...item,
    canonical,
    alternates: {
      html: canonical,
      json: `${canonical}.json`,
      markdown: `${canonical}.md`
    }
  };
}
