import test from 'node:test';
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const port=18987; let child;

async function waitForServer(){
  for(let i=0;i<50;i++){
    try{const r=await fetch(`http://127.0.0.1:${port}/api/v1/health`);if(r.ok)return;}catch{}
    await new Promise(r=>setTimeout(r,80));
  }
  throw new Error('server did not start');
}

test.before(async()=>{
  child=spawn(process.execPath,['server.mjs'],{cwd:root,env:{...process.env,PORT:String(port),HOST:'127.0.0.1',BASE_URL:`http://127.0.0.1:${port}`},stdio:['ignore','pipe','pipe']});
  await waitForServer();
});
test.after(()=>child?.kill('SIGTERM'));

test('health and catalog endpoints',async()=>{
  const h=await (await fetch(`http://127.0.0.1:${port}/api/v1/health`)).json(); assert.equal(h.ok,true);
  const c=await (await fetch(`http://127.0.0.1:${port}/api/v1/catalog`)).json(); assert.ok(c.counts.protocols>=7);
});

test('detail content negotiation',async()=>{
  const r=await fetch(`http://127.0.0.1:${port}/r/ucp`,{headers:{accept:'text/markdown'}}); assert.equal(r.status,200); assert.match(await r.text(),/Universal Commerce Protocol/);
});

test('MCP HTTP lists tools',async()=>{
  const r=await fetch(`http://127.0.0.1:${port}/mcp`,{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({jsonrpc:'2.0',id:1,method:'tools/list',params:{}})}); const j=await r.json(); assert.ok(j.result.tools.some(t=>t.name==='audit_store_readiness'));
});
