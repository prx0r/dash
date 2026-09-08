import { allItems, getItem, protocols, platforms, guides, publicItem, manifest } from './data.mjs';
import { search } from './search.mjs';
import { itemToMarkdown } from './format.mjs';
import { auditStore } from './audit.mjs';

const SERVER = { name: 'agentcom', version: '0.1.0' };
const PROTOCOL_VERSION = '2026-07-28';

function textResult(obj) {
  return { content: [{ type: 'text', text: typeof obj === 'string' ? obj : JSON.stringify(obj, null, 2) }], structuredContent: typeof obj === 'string' ? { text: obj } : obj };
}

export const toolDefinitions = [
  { name:'search_agentcom', description:'Search AgentCom canonical guides, protocols, platforms, and resources.', inputSchema:{type:'object',properties:{query:{type:'string'},kind:{type:'string',enum:['guide','protocol','platform','resource']},limit:{type:'integer',minimum:1,maximum:50}},required:['query'],additionalProperties:false}},
  { name:'get_agentcom_item', description:'Get one canonical AgentCom record by slug.', inputSchema:{type:'object',properties:{slug:{type:'string'}},required:['slug'],additionalProperties:false}},
  { name:'list_protocols', description:'List tracked agentic-commerce protocols and payment rails.', inputSchema:{type:'object',properties:{},additionalProperties:false}},
  { name:'list_platform_playbooks', description:'List tracked platform playbooks for Shopify, Google, OpenAI, Stripe, TikTok, Meta, and future platforms.', inputSchema:{type:'object',properties:{},additionalProperties:false}},
  { name:'audit_store_readiness', description:'Run a public, heuristic agent-readiness audit on a merchant URL.', inputSchema:{type:'object',properties:{url:{type:'string',format:'uri'}},required:['url'],additionalProperties:false}}
];

const prompts = [
  { name:'prepare_store_for_agentic_commerce', description:'Create an implementation plan for a merchant to become agent-ready.', arguments:[{name:'platform',description:'Commerce platform, e.g. Shopify',required:true},{name:'goal',description:'Primary goal, e.g. ChatGPT discovery or UCP checkout',required:false}] },
  { name:'compare_agentic_protocols', description:'Compare commerce/payment/agent protocols for a specific use case.', arguments:[{name:'use_case',description:'The commerce use case to evaluate',required:true}] }
];

function resourceRows(baseUrl) {
  return allItems.map((item)=>({ uri:`agentcom://${item.kind}/${item.slug}`, name:item.title, description:item.summary, mimeType:'application/json', _meta:{ canonical:`${baseUrl}/r/${item.slug}` } }));
}

export async function handleMcp(message, { baseUrl = manifest.canonical_base_url } = {}) {
  const { id = null, method, params = {} } = message || {};
  const ok = (result) => ({ jsonrpc:'2.0', id, result });
  const err = (code, message, data) => ({ jsonrpc:'2.0', id, error:{code,message,...(data?{data}:{})} });

  try {
    if (method === 'initialize') return ok({ protocolVersion: PROTOCOL_VERSION, capabilities:{ tools:{}, resources:{}, prompts:{} }, serverInfo:SERVER, instructions:'AgentCom is a public, machine-readable resource hub for agentic commerce. Prefer canonical records and source provenance; verify time-sensitive platform requirements against the linked primary sources.' });
    if (method === 'ping') return ok({});
    if (method === 'tools/list') return ok({ tools: toolDefinitions });
    if (method === 'resources/list') return ok({ resources: resourceRows(baseUrl) });
    if (method === 'prompts/list') return ok({ prompts });
    if (method === 'resources/read') {
      const uri = params?.uri || '';
      const m = /^agentcom:\/\/[^/]+\/(.+)$/.exec(uri);
      const item = m ? getItem(m[1]) : null;
      if (!item) return err(-32002,'Resource not found');
      return ok({ contents:[{uri,mimeType:'application/json',text:JSON.stringify(publicItem(item,baseUrl),null,2)}] });
    }
    if (method === 'prompts/get') {
      const name = params?.name;
      const args = params?.arguments || {};
      if (name === 'prepare_store_for_agentic_commerce') return ok({ description:'Agentic commerce readiness plan', messages:[{role:'user',content:{type:'text',text:`Using AgentCom sources, prepare a source-grounded agentic-commerce implementation plan for a ${args.platform || 'merchant'} store. Primary goal: ${args.goal || 'general agent readiness'}. Distinguish verified platform requirements from optional best practices, and cite canonical AgentCom resource slugs.`}}] });
      if (name === 'compare_agentic_protocols') return ok({ description:'Protocol selection analysis', messages:[{role:'user',content:{type:'text',text:`Compare UCP, ACP, MCP, A2A, AP2, x402, and MPP for this use case: ${args.use_case || 'agentic commerce'}. Recommend the smallest active protocol set and identify distribution channels unlocked by each.`}}] });
      return err(-32602,'Unknown prompt');
    }
    if (method === 'tools/call') {
      const name = params?.name; const args = params?.arguments || {};
      if (name === 'search_agentcom') return ok(textResult({ results:search(args.query,{kind:args.kind,limit:Math.min(args.limit||20,50),baseUrl}) }));
      if (name === 'get_agentcom_item') {
        const item = getItem(args.slug); if (!item) return err(-32002,'Item not found');
        return ok(textResult(publicItem(item,baseUrl)));
      }
      if (name === 'list_protocols') return ok(textResult({ protocols: protocols.map((x)=>publicItem(x,baseUrl)) }));
      if (name === 'list_platform_playbooks') return ok(textResult({ platforms: platforms.map((x)=>publicItem(x,baseUrl)), guides:guides.map((x)=>publicItem(x,baseUrl)) }));
      if (name === 'audit_store_readiness') return ok(textResult(await auditStore(args.url)));
      return err(-32602,'Unknown tool');
    }
    if (method?.startsWith('notifications/')) return null;
    return err(-32601,'Method not found');
  } catch (error) {
    return err(-32603,'Internal error',{message:String(error?.message || error)});
  }
}

export function itemResourceMarkdown(slug, baseUrl) {
  const item = getItem(slug);
  return item ? itemToMarkdown(item, baseUrl) : null;
}
