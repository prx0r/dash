import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { manifest, protocols, platforms, guides, resources, allItems, publicItem } from '../src/lib/data.mjs';
import { itemToMarkdown } from '../src/lib/format.mjs';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const pub=path.join(root,'public'); const base=process.env.BASE_URL||manifest.canonical_base_url;
fs.mkdirSync(path.join(pub,'.well-known'),{recursive:true});

const llms=[`# ${manifest.name}`,'',`> ${manifest.description}`,'','Canonical machine interfaces:','',`- [Full context](${base}/llms-full.txt)`,`- [JSON catalog](${base}/api/v1/catalog)`,`- [Search API](${base}/api/v1/search?q=shopify)`,`- [Knowledge graph](${base}/api/v1/graph)`,`- [MCP endpoint](${base}/mcp)`,`- [OpenAPI](${base}/openapi.json)`,'','## Guides','',...guides.map(x=>`- [${x.title}](${base}/r/${x.slug}.md): ${x.summary}`),'','## Protocols','',...protocols.map(x=>`- [${x.title}](${base}/r/${x.slug}.md): ${x.summary}`),'','## Platforms','',...platforms.map(x=>`- [${x.title}](${base}/r/${x.slug}.md): ${x.summary}`),''];
fs.writeFileSync(path.join(pub,'llms.txt'),llms.join('\n'));

const full=[`# ${manifest.name} — full machine context`,'',`Generated from canonical structured records. Last source-verification sweep: ${manifest.last_verified}.`,'',...allItems.flatMap(x=>[itemToMarkdown(x,base),'','---',''])];
fs.writeFileSync(path.join(pub,'llms-full.txt'),full.join('\n'));

const agents=[`# ${manifest.name}`,'',manifest.description,'','## Purpose','','AgentCom is a public reference corpus for agentic commerce. Agents may use the API and MCP endpoint to search protocols, platform playbooks, guides, and source-grounded resources.','','## Machine interfaces','',`- MCP: ${base}/mcp`,`- API: ${base}/api/v1`,`- Catalog JSON: ${base}/api/v1/catalog`,`- Search: ${base}/api/v1/search?q={query}`,`- Bulk NDJSON: ${base}/api/v1/export.ndjson`,`- Knowledge graph: ${base}/api/v1/graph`,`- llms.txt: ${base}/llms.txt`,`- Full context: ${base}/llms-full.txt`,'','## Source policy','','Prefer primary protocol/platform documentation. Each record includes source authority and last_verified. Time-sensitive instructions should be rechecked against the linked primary source before consequential implementation.',''];
fs.writeFileSync(path.join(pub,'agents.md'),agents.join('\n'));

const descriptor={name:'AgentCom.org',description:manifest.description,version:'0.1.0',canonical:base,license:manifest.license,last_verified:manifest.last_verified,interfaces:{mcp:`${base}/mcp`,api:`${base}/api/v1`,openapi:`${base}/openapi.json`,llms:`${base}/llms.txt`,agents:`${base}/agents.md`,ndjson:`${base}/api/v1/export.ndjson`,graph:`${base}/api/v1/graph`},content_types:['protocol','platform','guide','resource'],counts:{protocols:protocols.length,platforms:platforms.length,guides:guides.length,resources:resources.length}};
fs.writeFileSync(path.join(pub,'.well-known','agentcom.json'),JSON.stringify(descriptor,null,2)+'\n');
fs.writeFileSync(path.join(pub,'.well-known','mcp.json'),JSON.stringify({note:'AgentCom discovery descriptor; not asserted as a universal well-known MCP standard.',name:'agentcom',transport:'streamable-http-jsonrpc',endpoint:`${base}/mcp`,protocol_version:'2026-07-28',documentation:`${base}/r/mcp`},null,2)+'\n');
fs.writeFileSync(path.join(pub,'robots.txt'),`User-agent: *\nAllow: /\n\nSitemap: ${base}/sitemap.xml\n`);
fs.writeFileSync(path.join(pub,'sitemap.xml'),`<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n  <url><loc>${base}/</loc></url>\n${allItems.map(x=>`  <url><loc>${base}/r/${x.slug}</loc></url>`).join('\n')}\n</urlset>\n`);

const openapi={openapi:'3.1.0',info:{title:'AgentCom API',version:'0.1.0',description:manifest.description},servers:[{url:base}],paths:{'/api/v1/catalog':{get:{summary:'Get the entire AgentCom catalog',responses:{'200':{description:'Catalog'}}}},'/api/v1/search':{get:{summary:'Search canonical AgentCom records',parameters:[{name:'q',in:'query',required:true,schema:{type:'string'}},{name:'kind',in:'query',required:false,schema:{type:'string',enum:['guide','protocol','platform','resource']}}],responses:{'200':{description:'Search results'}}}},'/api/v1/items/{slug}':{get:{summary:'Get a canonical item',parameters:[{name:'slug',in:'path',required:true,schema:{type:'string'}}],responses:{'200':{description:'Item'},'404':{description:'Not found'}}}},'/api/v1/audit':{post:{summary:'Run a public agent-readiness audit',requestBody:{required:true,content:{'application/json':{schema:{type:'object',properties:{url:{type:'string',format:'uri'}},required:['url']}}}},responses:{'200':{description:'Audit result'}}}},'/mcp':{post:{summary:'MCP JSON-RPC endpoint',responses:{'200':{description:'MCP JSON-RPC response'}}}}}};
fs.writeFileSync(path.join(pub,'openapi.json'),JSON.stringify(openapi,null,2)+'\n');

const snapshot={generated_at:new Date().toISOString(),base_url:base,items:allItems.map(x=>publicItem(x,base))};
fs.writeFileSync(path.join(pub,'catalog.json'),JSON.stringify(snapshot,null,2)+'\n');
console.log(`Generated machine files for ${allItems.length} canonical items.`);
