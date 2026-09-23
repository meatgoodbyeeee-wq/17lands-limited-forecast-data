#!/usr/bin/env python3
"""Fetch FIN-blind 17Lands Premier Draft ALSA targets for development sets."""
import argparse, json, time, urllib.parse, urllib.request
from pathlib import Path
import pandas as pd

DEV_SETS={"KHM","STX","AFR","MID","VOW","NEO","SNC","DMU","BRO","ONE","MOM","LTR","WOE","LCI","MKM","OTJ","MH3","BLB","DSK","FDN","DFT","TDM"}

def fetch(set_code):
    q=urllib.parse.urlencode({"expansion":set_code,"event_type":"PremierDraft","time_period":"ALL_TIME"})
    req=urllib.request.Request("https://www.17lands.com/api/card_data?"+q,headers={"User-Agent":"LimitedForecastResearch/2.0","Accept":"application/json"})
    with urllib.request.urlopen(req,timeout=90) as r:
        x=json.load(r)
    rows=x.get("data",x) if isinstance(x,dict) else x
    out=[]
    for c in rows:
        name=c.get("name") or c.get("card_name")
        alsa=c.get("avg_seen")
        if name and alsa is not None:
            out.append({"set":set_code,"name":name,"actual_alsa":float(alsa)})
    return out

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--sets",nargs="+",required=True); ap.add_argument("--out",type=Path,required=True)
    a=ap.parse_args(); sets=[s.upper() for s in a.sets]
    bad=set(sets)-DEV_SETS
    if bad or "FIN" in sets: raise SystemExit(f"Refusing non-development/FIN sets: {sorted(bad|({'FIN'} if 'FIN' in sets else set()))}")
    all_rows=[]
    for s in sets:
        try:
            rows=fetch(s); print(s,len(rows)); all_rows.extend(rows)
        except Exception as e:
            print("FETCH_FAILED",s,repr(e))
        time.sleep(0.4)
    if not all_rows: raise SystemExit("No ALSA rows fetched")
    a.out.parent.mkdir(parents=True,exist_ok=True)
    pd.DataFrame(all_rows).to_csv(a.out,index=False)
    print("wrote",a.out,len(all_rows),"rows")

if __name__=="__main__": main()
