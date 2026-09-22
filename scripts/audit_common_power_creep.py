#!/usr/bin/env python3
import argparse
from pathlib import Path
import pandas as pd

ORDER=["KHM","STX","AFR","MID","VOW","NEO","SNC","DMU","BRO","ONE","MOM","LTR","WOE","LCI","MKM","OTJ","BLB","DSK","FDN","DFT","TDM"]
METRICS=["stats_per_mv","power_per_mv","toughness_per_mv","interaction_per_mv","card_advantage_per_mv","oracle_len","keyword_count"]

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--input",type=Path,required=True)
    ap.add_argument("--out",type=Path,required=True)
    a=ap.parse_args()
    d=pd.read_csv(a.input)
    d["set"]=d["set"].str.upper()
    if "FIN" in set(d["set"]):
        raise SystemExit("FIN contamination detected")
    common=d[d["rarity_ord"]==0].copy()
    rows=[]
    for s in ORDER:
        g=common[common["set"]==s]
        if g.empty:
            continue
        row={"set":s,"era_index":ORDER.index(s),"n_common":len(g)}
        for col in METRICS:
            x=pd.to_numeric(g[col],errors="coerce")
            row[col+"_mean"]=x.mean()
            row[col+"_median"]=x.median()
        rows.append(row)
    out=pd.DataFrame(rows)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    out.to_csv(a.out,index=False)
    print(out.to_string(index=False))
    mh3=common[common["set"]=="MH3"]
    if not mh3.empty:
        print("MH3_REFERENCE_ONLY")
        for col in METRICS:
            x=pd.to_numeric(mh3[col],errors="coerce")
            print(col,"mean",x.mean(),"median",x.median())
    print("FIN_USED=false")

if __name__=="__main__":
    main()
