// Top neighbour lists for N1 (text cosine by site vector(); labels cosine; class/mv filter). Outcome-free.
import fs from 'node:fs'; import {gunzipSync} from 'node:zlib';
const P='/tmp/claude-0/-home-claude/dda3b4cf-131c-509f-af58-b2d25513cf36/scratchpad/limited-forecast-pages/';
const W='/tmp/claude-0/-home-claude/dda3b4cf-131c-509f-af58-b2d25513cf36/scratchpad/work/';
const {vector,similarityIndex}=await import(P+'lib/predict.mjs');
const rd=p=>JSON.parse(gunzipSync(fs.readFileSync(P+p)));
const model=rd('data/model.json.gz'),refs=rd('data/similar-references.json.gz'),labels=rd('data/similar-labels.json.gz');
const m=model.models.gih;
const oofSets=new Set(JSON.parse(fs.readFileSync(W+'oof_sets.json')));
const index=similarityIndex(refs.cards,m).filter(r=>oofSets.has(r.c.set)&&r.c.gih_n>=3000&&labels.refs[`${r.c.set}|${r.c.name}`]);
console.error('candidates',index.length);
const Q=JSON.parse(fs.readFileSync(W+'n1_queries.json'));
const cls=t=>/\bLand\b/.test(t||'')?0:/\bCreature\b/.test(t||'')?1:2;
const norm=a=>Math.sqrt(a.reduce((s,[,v])=>s+v*v,0))||1;
const scale2=(labels.scale||1000)**2, LW=0.5;
const cand=index.map(r=>({key:`${r.c.set}|${r.c.name}`,set:r.c.set,l:labels.refs[`${r.c.set}|${r.c.name}`],cl:cls(r.c.type_line),mv:Number(r.c.cmc)||0}));
function run(c,v,lv,pool){
  const n=norm(v),map=new Map(v),k=cls(c.type_line),mv=Number(c.cmc)||0,rows=[];
  for(let j=0;j<index.length;j++){const r=index[j];if(r.c.set===c.set)continue;
    let d=0;for(const [i,x] of r.v){const y=map.get(i);if(y)d+=x*y;}
    const cosd=d/(n*r.n);let l=0;const rl=cand[j].l;for(let i=0;i<lv.length;i++)l+=lv[i]*rl[i];
    rows.push({j,cos:cosd,lab:l/scale2,ok:cand[j].cl===k&&Math.abs(cand[j].mv-mv)<=2});}
  const old=[...rows].sort((a,b)=>b.cos-a.cos).slice(0,60).map(r=>[cand[r.j].key,+r.cos.toFixed(5)]);
  const sc=r=>r.cos+LW*r.lab;
  const ok=rows.filter(r=>r.ok).sort((a,b)=>sc(b)-sc(a)).slice(0,60).map(r=>[cand[r.j].key,+(sc(r)/(1+LW)).toFixed(5)]);
  const no=rows.filter(r=>!r.ok).sort((a,b)=>sc(b)-sc(a)).slice(0,20).map(r=>[cand[r.j].key,+(sc(r)/(1+LW)).toFixed(5)]);
  return {old,ok,no};
}
// pools per set (reconstructed objects) for context features
const poolBy={};for(const q of Q)(poolBy[q.set]||=[]).push(q.recon);
const sitePool={};for(const c of refs.cards)(sitePool[c.set]||=[]).push(c);
const out={},val={};
for(const q of Q){
  const key=`${q.set}|${q.name}`;
  out[key]=run(q.recon,vector(q.recon,m,poolBy[q.set]),q.lv,poolBy[q.set]);
  if(q.site){const r=run(q.site,vector(q.site,m,sitePool[q.set]),q.lv,sitePool[q.set]);val[key]={old:r.old.slice(0,3).map(x=>x[0]),new:r.ok.slice(0,3).map(x=>x[0])};}
}
fs.writeFileSync(W+'n1_neighbors.json',JSON.stringify(out));fs.writeFileSync(W+'n1_validation_site.json',JSON.stringify(val));
console.error('done',Object.keys(out).length);
