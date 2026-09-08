import test from 'node:test';
import assert from 'node:assert/strict';
import { allItems, getItem } from '../src/lib/data.mjs';
import { search } from '../src/lib/search.mjs';
import { itemToMarkdown } from '../src/lib/format.mjs';
import { handleMcp } from '../src/lib/mcp.mjs';

test('canonical slugs are unique',()=>{
  assert.equal(new Set(allItems.map(x=>x.slug)).size,allItems.length);
});

test('search finds Shopify UCP material',()=>{
  const rows=search('shopify ucp',{limit:10});
  assert.ok(rows.length>0);
  assert.ok(rows.some(x=>x.slug==='shopify-agent-readiness'||x.slug==='shopify'));
});

test('markdown includes provenance and machine alternates',()=>{
  const md=itemToMarkdown(getItem('ucp'));
  assert.match(md,/## Sources/);
  assert.match(md,/\.json/);
  assert.match(md,/Universal Commerce Protocol/);
});

test('MCP initialize and search tool work',async()=>{
  const init=await handleMcp({jsonrpc:'2.0',id:1,method:'initialize',params:{}});
  assert.equal(init.result.serverInfo.name,'agentcom');
  const call=await handleMcp({jsonrpc:'2.0',id:2,method:'tools/call',params:{name:'search_agentcom',arguments:{query:'x402'}}});
  assert.ok(call.result.structuredContent.results.some(x=>x.slug==='x402'));
});
