const UA = 'AgentComReadinessBot/0.1 (+https://agentcom.org/audit)';

function withTimeout(ms) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), ms);
  return { signal: controller.signal, done: () => clearTimeout(timer) };
}

async function get(url, timeout = 7000) {
  const t = withTimeout(timeout);
  try {
    const res = await fetch(url, { headers: { 'user-agent': UA, accept: 'text/html,application/json,text/plain,*/*' }, redirect: 'follow', signal: t.signal });
    const text = await res.text();
    return { ok: res.ok, status: res.status, url: res.url, contentType: res.headers.get('content-type') || '', text: text.slice(0, 2_000_000) };
  } catch (error) {
    return { ok: false, status: 0, url, contentType: '', text: '', error: String(error?.message || error) };
  } finally { t.done(); }
}

function check(id, label, weight, passed, evidence, recommendation) {
  return { id, label, weight, passed: Boolean(passed), evidence, recommendation };
}

function hasProductSchema(html) {
  return /application\/ld\+json/i.test(html) && /["']@type["']\s*:\s*["']Product["']/i.test(html);
}

export async function auditStore(inputUrl) {
  let u;
  try { u = new URL(inputUrl); } catch { throw new Error('Invalid URL'); }
  if (!['http:', 'https:'].includes(u.protocol)) throw new Error('Only http/https URLs are supported');
  const origin = u.origin;
  const [home, robots, llms, agents, ucp, sitemap] = await Promise.all([
    get(origin + u.pathname), get(origin + '/robots.txt'), get(origin + '/llms.txt'), get(origin + '/agents.md'), get(origin + '/.well-known/ucp'), get(origin + '/sitemap.xml')
  ]);
  const html = home.text || '';
  const bodyLower = html.toLowerCase();
  const ucpJson = (() => { try { return JSON.parse(ucp.text); } catch { return null; } })();
  const checks = [
    check('reachable','Storefront reachable',5,home.ok,home.ok?`HTTP ${home.status}`:(home.error||`HTTP ${home.status}`),'Make the canonical storefront reliably accessible.'),
    check('https','HTTPS',5,u.protocol==='https:','HTTPS origin','Serve commerce and machine endpoints over HTTPS.'),
    check('robots','robots.txt',5,robots.ok,robots.ok?`HTTP ${robots.status}`:'Missing or inaccessible','Publish robots.txt and make intentional crawler policy decisions.'),
    check('llms','llms.txt',10,llms.ok && llms.text.trim().length>20,llms.ok?'Present':'Not found','Publish a concise /llms.txt index of authoritative merchant information where useful.'),
    check('agents','agents.md',15,agents.ok && agents.text.trim().length>20,agents.ok?'Present':'Not found','Publish /agents.md when your platform/workflow supports an agent-facing store description.'),
    check('product-schema','Product structured data',15,hasProductSchema(html),hasProductSchema(html)?'schema.org Product detected':'Not detected','Expose variant/product facts in server-rendered structured data.'),
    check('price','Price signals',10,/price|pricecurrency|offers/i.test(html),/price|pricecurrency|offers/i.test(html)?'Detected':'Not detected','Expose current price and currency in structured product data.'),
    check('availability','Availability signals',5,/availability|instock|outofstock|inventory/i.test(html),/availability|instock|outofstock|inventory/i.test(html)?'Detected':'Not detected','Expose current inventory/availability at variant level.'),
    check('policies','Return/refund policy',5,/return|refund/i.test(bodyLower),/return|refund/i.test(bodyLower)?'Detected':'Not detected','Publish a directly accessible return/refund policy.'),
    check('shipping','Shipping/delivery facts',5,/shipping|delivery/i.test(bodyLower),/shipping|delivery/i.test(bodyLower)?'Detected':'Not detected','Publish shipping regions, cost logic, and delivery expectations.'),
    check('ucp','UCP discovery',15,ucp.ok && Boolean(ucpJson?.ucp),ucp.ok?(ucpJson?.ucp?.version?`UCP ${ucpJson.ucp.version}`:'Document found'):'Not found','If your commerce stack supports UCP, expose /.well-known/ucp with explicit capabilities and service endpoints.'),
    check('sitemap','Sitemap',5,sitemap.ok,sitemap.ok?'Present':'Not found','Publish a current sitemap for deterministic URL discovery.')
  ];
  const score = checks.reduce((sum,c)=>sum+(c.passed?c.weight:0),0);
  return {
    url: home.url || inputUrl,
    origin,
    audited_at: new Date().toISOString(),
    score,
    grade: score >= 85 ? 'A' : score >= 70 ? 'B' : score >= 55 ? 'C' : score >= 40 ? 'D' : 'F',
    checks,
    recommendations: checks.filter(c=>!c.passed).sort((a,b)=>b.weight-a.weight).map(c=>c.recommendation),
    note: 'Heuristic public-surface audit only. Platform eligibility, feed quality, auth, conversion, and merchant-policy compliance require deeper tests.'
  };
}
