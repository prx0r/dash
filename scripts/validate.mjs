import { allItems, protocols, platforms, guides, resources } from '../src/lib/data.mjs';

let bad=0; const slugs=new Set();
for(const item of allItems){
  for(const key of ['slug','kind','title','summary','sources']) if(!item[key]) { console.error(`${item.slug||item.title||'item'} missing ${key}`); bad++; }
  if(slugs.has(item.slug)){console.error(`Duplicate slug ${item.slug}`);bad++;} slugs.add(item.slug);
  if(!/^[a-z0-9-]+$/.test(item.slug)){console.error(`Invalid slug ${item.slug}`);bad++;}
  if(!Array.isArray(item.sources)||!item.sources.length){console.error(`No sources: ${item.slug}`);bad++;continue;}
  for(const s of item.sources){
    try{new URL(s.url);}catch{console.error(`Bad source URL ${item.slug}: ${s.url}`);bad++;}
    if(!/^\d{4}-\d{2}-\d{2}$/.test(s.last_verified||'')){console.error(`Bad verification date ${item.slug}`);bad++;}
  }
}
for(const g of guides) if(g.platform && !platforms.some(p=>p.slug===g.platform)){console.error(`Unknown guide platform ${g.slug}: ${g.platform}`);bad++;}
console.log(`Validated ${allItems.length} items: ${protocols.length} protocols, ${platforms.length} platforms, ${guides.length} guides, ${resources.length} resources.`);
if(bad){console.error(`${bad} validation problem(s).`);process.exit(1)}
