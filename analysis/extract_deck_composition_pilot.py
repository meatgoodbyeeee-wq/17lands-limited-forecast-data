#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,gzip,json,hashlib
from collections import defaultdict
from pathlib import Path
from urllib.request import Request,urlopen
import pandas as pd

BASE="https://17lands-public.s3.amazonaws.com/analysis_data/game_data"
FMT="PremierDraft"
PILOT={"ONE","DMU","SNC"}

def url_for(s): return f"{BASE}/game_data_public.{s}.{FMT}.csv.gz"

def download(s,dest):
    req=Request(url_for(s),headers={"User-Agent":"LimitedForecastResearch/1.0"})
    tmp=dest.with_suffix(dest.suffix+".part")
    with urlopen(req,timeout=180) as r,open(tmp,"wb") as out:
        while True:
            b=r.read(1024*1024)
            if not b: break
            out.write(b)
    tmp.replace(dest)

def sha256_file(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        while True:
            b=f.read(1024*1024)
            if not b: break
            h.update(b)
    return h.hexdigest()

def header(path):
    with gzip.open(path,"rt",encoding="utf-8-sig",newline="") as f:
        return next(csv.reader(f))

def first_window(path,chunksize):
    earliest=None
    for c in pd.read_csv(path,usecols=["draft_time"],chunksize=chunksize,compression="gzip",low_memory=True):
        t=pd.to_datetime(c["draft_time"],errors="coerce",utc=True)
        v=t.min()
        if pd.notna(v) and (earliest is None or v<earliest): earliest=v
    if earliest is None: raise RuntimeError("no valid draft_time")
    return earliest,earliest+pd.Timedelta(days=28)

def canon_pair(x):
    s=str(x).upper()
    return "".join(c for c in "WUBRG" if c in s)

def blank_splash(x):
    if pd.isna(x): return True
    return str(x).strip().lower() in {"","nan","none","null"}

def extract(s,path,out,chunksize):
    h=header(path)
    required={"draft_time","draft_id","build_index","main_colors","splash_colors"}
    miss=sorted(required-set(h))
    if miss: raise RuntimeError(f"missing required columns: {miss}")
    deck_cols=[c for c in h if c.startswith("deck_")]
    if not deck_cols: raise RuntimeError("no deck_ columns")
    start,end=first_window(path,chunksize)
    use=list(required)+deck_cols

    seen=set()
    builds=defaultdict(int)
    copies=defaultdict(lambda:defaultdict(float))
    included=defaultdict(lambda:defaultdict(int))
    deck_sizes=defaultdict(list)
    rows_window=0; rows_pure2=0; duplicate_rows=0

    for c in pd.read_csv(path,usecols=use,chunksize=chunksize,compression="gzip",low_memory=True):
        t=pd.to_datetime(c["draft_time"],errors="coerce",utc=True)
        m=(t>=start)&(t<end)
        if not m.any(): continue
        c=c.loc[m].copy(); rows_window+=len(c)
        c["_pair"]=c["main_colors"].map(canon_pair)
        c["_pure"]=c["splash_colors"].map(blank_splash)&c["_pair"].str.len().eq(2)
        c=c.loc[c["_pure"]]
        rows_pure2+=len(c)
        for row in c.itertuples(index=False,name=None):
            vals=dict(zip(c.columns,row))
            key=(str(vals["draft_id"]),str(vals["build_index"]))
            if key in seen:
                duplicate_rows+=1
                continue
            seen.add(key)
            p=vals["_pair"]
            builds[p]+=1
            size=0.0
            for col in deck_cols:
                v=vals[col]
                try: n=float(v) if pd.notna(v) else 0.0
                except Exception: n=0.0
                if n<=0: continue
                card=col[5:]
                copies[p][card]+=n
                included[p][card]+=1
                size+=n
            deck_sizes[p].append(size)

    rows=[]
    for p in sorted(builds):
        n=builds[p]
        for card in sorted(copies[p]):
            rows.append({"set":s,"pair":p,"card_name":card,"builds":n,
                         "included_builds":included[p][card],
                         "inclusion_rate":included[p][card]/n,
                         "mean_copies":copies[p][card]/n})
    pd.DataFrame(rows).to_csv(out/f"{s}_pure2_deck_composition_28d.csv",index=False)
    man={"set":s,"format":FMT,"source_url":url_for(s),"sha256":sha256_file(path),
         "window_start":start.isoformat(),"window_end":end.isoformat(),
         "rows_in_window":rows_window,"pure2_game_rows":rows_pure2,
         "unique_pure2_builds":int(sum(builds.values())),"duplicate_game_rows_removed":duplicate_rows,
         "builds_by_pair":dict(sorted(builds.items())),
         "mean_deck_size_by_pair":{p:float(pd.Series(v).mean()) for p,v in sorted(deck_sizes.items())},
         "deck_columns":len(deck_cols)}
    (out/f"{s}_pure2_deck_composition_manifest.json").write_text(json.dumps(man,indent=2),encoding="utf-8")
    print("PILOT_MANIFEST",json.dumps(man))

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--set",required=True); ap.add_argument("--out-dir",type=Path,default=Path("out")); ap.add_argument("--chunksize",type=int,default=4000)
    a=ap.parse_args(); s=a.set.upper()
    if s not in PILOT: raise SystemExit(f"pilot guard: {s} not allowed")
    a.out_dir.mkdir(parents=True,exist_ok=True)
    raw=a.out_dir/f"game_data_public.{s}.{FMT}.csv.gz"
    download(s,raw)
    extract(s,raw,a.out_dir,a.chunksize)
    raw.unlink(missing_ok=True)
if __name__=="__main__": main()
