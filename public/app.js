const $ = (s) => document.querySelector(s);
let catalog;

function esc(s=''){return String(s).replace(/[&<>\"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]))}
function card(item){
  const meta=item.platform || item.status || item.category || item.kind;
  return `<a class="card" href="/r/${encodeURIComponent(item.slug)}"><span class="kind">${esc(item.kind)}${meta?` · ${esc(meta)}`:''}</span><h3>${esc(item.title)}</h3><p>${esc(item.summary)}</p><div class="card-foot"><div class="chips">${(item.tags||[]).slice(0,3).map(t=>`<span>${esc(t)}</span>`).join('')}</div><span>↗</span></div></a>`;
}
function renderGrid(sel,items){$(sel).innerHTML=items.map(card).join('')}

async function load(){
  const res=await fetch('/api/v1/catalog'); catalog=await res.json();
  const c=catalog.counts;
  $('#stats').innerHTML=[['GUIDES',c.guides],['PROTOCOLS',c.protocols],['PLATFORMS',c.platforms],['RESOURCES',c.resources],['VERIFIED',catalog.meta.last_verified]].map(([k,v])=>`<div class="stat"><strong>${esc(v)}</strong><span>${k}</span></div>`).join('');
  renderGrid('#guides-grid',catalog.guides.slice(0,9));
  renderGrid('#protocols-grid',catalog.protocols);
  renderGrid('#platforms-grid',catalog.platforms);
}

let timer;
async function doSearch(q){
  const box=$('#search-results');
  if(!q.trim()){box.classList.add('hidden');return}
  const res=await fetch(`/api/v1/search?q=${encodeURIComponent(q)}&limit=24`); const data=await res.json();
  $('#results-grid').innerHTML=data.results.length?data.results.map(card).join(''):'<p>No matching canonical records yet.</p>';
  box.classList.remove('hidden'); box.scrollIntoView({behavior:'smooth',block:'start'});
}
$('#search').addEventListener('input',e=>{clearTimeout(timer);timer=setTimeout(()=>doSearch(e.target.value),180)});
$('#clear-search').addEventListener('click',()=>{$('#search').value='';$('#search-results').classList.add('hidden');$('#search').focus()});
document.addEventListener('keydown',e=>{if((e.metaKey||e.ctrlKey)&&e.key.toLowerCase()==='k'){e.preventDefault();$('#search').focus()}});

$('#audit-form').addEventListener('submit',async e=>{
  e.preventDefault(); const url=$('#audit-url').value; const out=$('#audit-result'); out.classList.remove('hidden'); out.innerHTML='<p>Auditing public machine surfaces…</p>';
  try{
    const res=await fetch('/api/v1/audit',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({url})}); const data=await res.json();
    if(!res.ok) throw new Error(data.message||data.error||'Audit failed');
    out.innerHTML=`<div class="score-row"><div class="score">${data.score}</div><div><strong>Grade ${esc(data.grade)}</strong><div>${esc(data.origin)}</div></div></div><div class="checks">${data.checks.map(c=>`<div class="check"><span>${esc(c.label)}</span><b class="${c.passed?'pass':'fail'}">${c.passed?'PASS':'FIX'}</b></div>`).join('')}</div>${data.recommendations.length?`<p><strong>Highest-value fixes:</strong> ${data.recommendations.slice(0,3).map(esc).join(' ')}</p>`:''}<small>${esc(data.note)}</small>`;
  }catch(err){out.innerHTML=`<p>Audit failed: ${esc(err.message)}</p>`}
});

load().catch(err=>console.error(err));
