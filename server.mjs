import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { manifest, protocols, platforms, guides, resources, glossary, allItems, getItem, publicItem } from './src/lib/data.mjs';
import { search } from './src/lib/search.mjs';
import { itemToMarkdown, itemToHtml } from './src/lib/format.mjs';
import { auditStore } from './src/lib/audit.mjs';
import { handleMcp } from './src/lib/mcp.mjs';

const root = path.dirname(fileURLToPath(import.meta.url));
const publicDir = path.join(root, 'public');
const PORT = Number(process.env.PORT || 8787);
const HOST = process.env.HOST || '0.0.0.0';
const BASE_URL = (process.env.BASE_URL || manifest.canonical_base_url).replace(/\/$/, '');

const MIME = {
  '.html':'text/html; charset=utf-8','.css':'text/css; charset=utf-8','.js':'text/javascript; charset=utf-8',
  '.json':'application/json; charset=utf-8','.txt':'text/plain; charset=utf-8','.md':'text/markdown; charset=utf-8',
  '.xml':'application/xml; charset=utf-8','.svg':'image/svg+xml','.ico':'image/x-icon'
};

function setCommon(res) {
  res.setHeader('Access-Control-Allow-Origin','*');
  res.setHeader('Access-Control-Allow-Headers','content-type,accept,mcp-protocol-version');
  res.setHeader('Access-Control-Allow-Methods','GET,POST,OPTIONS');
  res.setHeader('X-Content-Type-Options','nosniff');
  res.setHeader('Referrer-Policy','strict-origin-when-cross-origin');
}

function send(res, status, body, type='text/plain; charset=utf-8', extra={}) {
  setCommon(res);
  res.statusCode=status;
  res.setHeader('Content-Type',type);
  for (const [k,v] of Object.entries(extra)) res.setHeader(k,v);
  res.end(body);
}
function json(res,status,obj,extra={}) { send(res,status,JSON.stringify(obj,null,2)+'\n','application/json; charset=utf-8',extra); }

async function bodyJson(req, max=1_000_000) {
  const chunks=[]; let size=0;
  for await (const chunk of req) { size+=chunk.length; if(size>max) throw new Error('Request body too large'); chunks.push(chunk); }
  if (!chunks.length) return {};
  return JSON.parse(Buffer.concat(chunks).toString('utf8'));
}

function safeStaticPath(pathname) {
  const clean = decodeURIComponent(pathname).replace(/\\/g,'/');
  const rel = clean === '/' ? 'index.html' : clean.replace(/^\/+/, '');
  const full = path.resolve(publicDir, rel);
  if (!full.startsWith(path.resolve(publicDir) + path.sep) && full !== path.join(publicDir,'index.html')) return null;
  return full;
}

function serveStatic(pathname,res) {
  const full=safeStaticPath(pathname); if(!full) return false;
  let stat; try{stat=fs.statSync(full);}catch{return false;}
  if(!stat.isFile()) return false;
  const ext=path.extname(full).toLowerCase();
  const cache = /\.(css|js|svg)$/.test(ext) ? 'public, max-age=300' : 'public, max-age=60';
  setCommon(res); res.statusCode=200; res.setHeader('Content-Type',MIME[ext]||'application/octet-stream'); res.setHeader('Cache-Control',cache);
  fs.createReadStream(full).pipe(res); return true;
}

function graph() {
  const nodes=allItems.map(i=>({id:`${i.kind}:${i.slug}`,kind:i.kind,slug:i.slug,title:i.title,tags:i.tags||[]}));
  const edges=[];
  for(const g of guides){
    if(g.platform) edges.push({from:`guide:${g.slug}`,to:`platform:${g.platform}`,type:'targets-platform'});
    for(const tag of g.tags||[]) if(protocols.some(p=>p.slug===tag)) edges.push({from:`guide:${g.slug}`,to:`protocol:${tag}`,type:'references-protocol'});
  }
  for(const p of platforms) for(const tag of p.tags||[]) if(protocols.some(x=>x.slug===tag)) edges.push({from:`platform:${p.slug}`,to:`protocol:${tag}`,type:'uses-protocol'});
  for(const r of resources) for(const tag of r.tags||[]) {
    if(protocols.some(x=>x.slug===tag)) edges.push({from:`resource:${r.slug}`,to:`protocol:${tag}`,type:'documents-protocol'});
    if(platforms.some(x=>x.slug===tag)) edges.push({from:`resource:${r.slug}`,to:`platform:${tag}`,type:'documents-platform'});
  }
  return {generated_at:new Date().toISOString(),nodes,edges};
}

function catalog() {
  return {
    meta:{name:manifest.name,tagline:manifest.tagline,last_verified:manifest.last_verified,license:manifest.license},
    counts:{protocols:protocols.length,platforms:platforms.length,guides:guides.length,resources:resources.length,glossary:glossary.length},
    endpoints:manifest.machine_endpoints,
    protocols:protocols.map(x=>publicItem(x,BASE_URL)),platforms:platforms.map(x=>publicItem(x,BASE_URL)),
    guides:guides.map(x=>publicItem(x,BASE_URL)),resources:resources.map(x=>publicItem(x,BASE_URL)),glossary
  };
}

const server=http.createServer(async (req,res)=>{
  try{
    const url=new URL(req.url,`http://${req.headers.host||'localhost'}`); const p=url.pathname;
    if(req.method==='OPTIONS'){setCommon(res);res.statusCode=204;return res.end();}

    if(req.method==='GET' && p==='/api/v1'){return json(res,200,{name:manifest.name,description:manifest.description,endpoints:manifest.machine_endpoints,last_verified:manifest.last_verified});}
    if(req.method==='GET' && p==='/api/v1/health'){return json(res,200,{ok:true,service:'agentcom',version:'0.1.0',time:new Date().toISOString()});}
    if(req.method==='GET' && p==='/api/v1/catalog'){return json(res,200,catalog());}
    if(req.method==='GET' && p==='/api/v1/protocols'){return json(res,200,{data:protocols.map(x=>publicItem(x,BASE_URL))});}
    if(req.method==='GET' && p==='/api/v1/platforms'){return json(res,200,{data:platforms.map(x=>publicItem(x,BASE_URL))});}
    if(req.method==='GET' && p==='/api/v1/guides'){return json(res,200,{data:guides.map(x=>publicItem(x,BASE_URL))});}
    if(req.method==='GET' && p==='/api/v1/resources'){return json(res,200,{data:resources.map(x=>publicItem(x,BASE_URL))});}
    if(req.method==='GET' && p==='/api/v1/glossary'){return json(res,200,{data:glossary});}
    if(req.method==='GET' && p==='/api/v1/search'){
      const q=url.searchParams.get('q')||''; const kind=url.searchParams.get('kind')||undefined; const limit=Math.min(Number(url.searchParams.get('limit')||20),50);
      return json(res,200,{query:q,kind:kind||null,count:search(q,{kind,limit,baseUrl:BASE_URL}).length,results:search(q,{kind,limit,baseUrl:BASE_URL})});
    }
    if(req.method==='GET' && p==='/api/v1/graph'){return json(res,200,graph());}
    if(req.method==='GET' && p==='/api/v1/export.ndjson'){
      const lines=allItems.map(x=>JSON.stringify(publicItem(x,BASE_URL))).join('\n')+'\n'; return send(res,200,lines,'application/x-ndjson; charset=utf-8');
    }
    if(req.method==='GET' && p.startsWith('/api/v1/items/')){
      const slug=decodeURIComponent(p.slice('/api/v1/items/'.length)); const item=getItem(slug); if(!item)return json(res,404,{error:'not_found'}); return json(res,200,publicItem(item,BASE_URL));
    }
    if(req.method==='POST' && p==='/api/v1/audit'){
      const body=await bodyJson(req); if(!body.url)return json(res,400,{error:'url_required'}); return json(res,200,await auditStore(body.url));
    }

    if(req.method==='POST' && p==='/mcp'){
      const msg=await bodyJson(req); const result=await handleMcp(msg,{baseUrl:BASE_URL});
      if(result===null){setCommon(res);res.statusCode=202;return res.end();}
      return json(res,200,result,{'MCP-Protocol-Version':'2026-07-28','Cache-Control':'no-store'});
    }
    if(req.method==='GET' && p==='/mcp') return json(res,405,{error:'method_not_allowed',message:'POST JSON-RPC messages to this endpoint. See /examples/mcp-config.json and /openapi.json.'},{Allow:'POST'});

    if(req.method==='GET' && p.startsWith('/r/')){
      let slug=p.slice(3); let format='html';
      if(slug.endsWith('.json')){slug=slug.slice(0,-5);format='json';}
      else if(slug.endsWith('.md')){slug=slug.slice(0,-3);format='md';}
      const item=getItem(slug); if(!item)return send(res,404,'Not found\n');
      const links=`<${BASE_URL}/r/${slug}.json>; rel="alternate"; type="application/json", <${BASE_URL}/r/${slug}.md>; rel="alternate"; type="text/markdown"`;
      if(format==='json'||req.headers.accept?.includes('application/json'))return json(res,200,publicItem(item,BASE_URL),{Link:links});
      if(format==='md'||req.headers.accept?.includes('text/markdown'))return send(res,200,itemToMarkdown(item,BASE_URL)+'\n','text/markdown; charset=utf-8',{Link:links});
      return send(res,200,itemToHtml(item,BASE_URL),'text/html; charset=utf-8',{Link:links});
    }

    if(req.method==='GET' && serveStatic(p,res)) return;
    return json(res,404,{error:'not_found',path:p});
  }catch(error){return json(res,500,{error:'internal_error',message:String(error?.message||error)});}
});

server.listen(PORT,HOST,()=>console.log(`AgentCom listening on http://${HOST}:${PORT} (canonical ${BASE_URL})`));
