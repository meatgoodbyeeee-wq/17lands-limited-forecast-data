// Production similarity (site code: lib/predict.mjs) over the 22-set references + the label-aware extras. Usage: node dump_prod_sim_extra.mjs <pages repo dir with trailing /> <out dir>  (feeds eval4_extra.py)
import fs from 'node:fs';import {gunzipSync} from 'node:zlib';
const P=process.argv[2], OUT=process.argv[3];
const {similarityIndex,extraIndex}=await import(P+'lib/predict.mjs');
const read=p=>JSON.parse(gunzipSync(fs.readFileSync(P+p)));
const model=read('data/model.json.gz'),refs=read('data/similar-references.json.gz'),labels=read('data/similar-labels.json.gz');
const idx=similarityIndex(refs.cards,model.models.gih),ex=extraIndex(refs.name_only,idx,model.models.gih,labels);
const all=[...idx,...ex],N=all.length,M=new Float32Array(N*N);
for(let a=0;a<N;a++){const t=all[a],map=new Map(t.v);for(let b=0;b<N;b++){const r=all[b];let d=0;for(const [i,x] of r.v){const y=map.get(i);if(y)d+=x*y;}M[a*N+b]=d/(t.n*r.n);}}
fs.writeFileSync(OUT+'/mat.f32',Buffer.from(M.buffer));
fs.writeFileSync(OUT+'/keys.json',JSON.stringify(all.map((x,i)=>[x.c.set,x.c.name,i>=idx.length?1:0,x.c.type_line,x.c.cmc,x.c.gih,x.c.gih_n])));
console.error(idx.length,ex.length,N);
