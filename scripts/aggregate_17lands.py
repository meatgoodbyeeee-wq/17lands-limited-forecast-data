#!/usr/bin/env python3
from __future__ import annotations
import argparse, csv, gzip, hashlib, json
from pathlib import Path
from urllib.request import Request, urlopen
import pandas as pd

BASE="https://17lands-public.s3.amazonaws.com/analysis_data/game_data"
FMT="PremierDraft"

def url_for(s): return f"{BASE}/game_data_public.{s}.{FMT}.csv.gz"

def sha256_file(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        while True:
            b=f.read(1024*1024)
            if not b: break
            h.update(b)
    return h.hexdigest()

def download(s,dest):
    req=Request(url_for(s),headers={"User-Agent":"LimitedForecastResearch/1.0"})
    tmp=dest.with_suffix(dest.suffix+".part")
    with urlopen(req,timeout=180) as r, open(tmp,"wb") as out:
        while True:
            b=r.read(1024*1024)
            if not b: break
            out.write(b)
    tmp.replace(dest)

def header(path):
    with gzip.open(path,"rt",encoding="utf-8-sig",newline="") as f:
        return next(csv.reader(f))

def first_window(path,days,chunksize):
    earliest=None
    for c in pd.read_csv(path,usecols=["draft_time"],chunksize=chunksize,compression="gzip",low_memory=True):
        t=pd.to_datetime(c["draft_time"],errors="coerce",utc=True)
        v=t.min()
        if pd.notna(v) and (earliest is None or v<earliest): earliest=v
    if earliest is None: raise RuntimeError("no valid draft_time")
    return earliest, earliest+pd.Timedelta(days=days)

def aggregate(set_code,path,days,min_games,chunksize):
    h=header(path)
    if "draft_time" not in h or "won" not in h: raise RuntimeError("required columns missing")
    prefixes=("opening_hand_","drawn_","tutored_")
    card_cols={}
    for col in h:
        for p in prefixes:
            if col.startswith(p):
                card_cols.setdefault(col[len(p):],[]).append(col)
                break
    start,end=first_window(path,days,chunksize)
    selected={"draft_time","won"}
    for cols in card_cols.values(): selected.update(cols)
    games={k:0 for k in card_cols}; wins={k:0 for k in card_cols}
    rows_in_window=0
    for c in pd.read_csv(path,usecols=list(selected),chunksize=chunksize,compression="gzip",low_memory=True):
        t=pd.to_datetime(c["draft_time"],errors="coerce",utc=True)
        m=(t>=start)&(t<end)
        if not m.any(): continue
        c=c.loc[m]
        rows_in_window += len(c)
        won=c["won"].astype(str).str.strip().str.lower().isin(["true","1","1.0"]).to_numpy()
        for card,cols in card_cols.items():
            present=None
            for col in cols:
                v=pd.to_numeric(c[col],errors="coerce").fillna(0).to_numpy()!=0
                present=v if present is None else (present|v)
            n=int(present.sum())
            if n:
                games[card]+=n
                wins[card]+=int((present&won).sum())
    out=[]
    for card in sorted(card_cols):
        n=games[card]
        if n<min_games: continue
        w=wins[card]
        out.append({"set":set_code,"card_name":card,"gih_games":n,"gih_wins":w,"gih_wr":w/n,"gih_wr_pct":100*w/n,
                    "window_start":start.isoformat(),"window_end":end.isoformat()})
    manifest={"set":set_code,"source_url":url_for(set_code),"sha256":sha256_file(path),"format":FMT,
              "window_days":days,"window_start":start.isoformat(),"window_end":end.isoformat(),
              "game_rows_in_window":rows_in_window,"cards_output":len(out),"min_gih_games":min_games}
    return out,manifest

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--set",required=True)
    ap.add_argument("--days",type=int,default=28)
    ap.add_argument("--min-games",type=int,default=500)
    ap.add_argument("--chunksize",type=int,default=5000)
    ap.add_argument("--out-dir",type=Path,default=Path("out"))
    a=ap.parse_args()
    s=a.set.upper()
    a.out_dir.mkdir(parents=True,exist_ok=True)
    raw=a.out_dir/f"game_data_public.{s}.{FMT}.csv.gz"
    download(s,raw)
    rows,man=aggregate(s,raw,a.days,a.min_games,a.chunksize)
    pd.DataFrame(rows).to_csv(a.out_dir/f"{s}_gih_28d.csv",index=False)
    (a.out_dir/f"{s}_manifest.json").write_text(json.dumps(man,indent=2),encoding="utf-8")
    raw.unlink(missing_ok=True)

if __name__=="__main__": main()
