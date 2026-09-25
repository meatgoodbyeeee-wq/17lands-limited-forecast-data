#!/usr/bin/env python3
import sys, os, json, tempfile, urllib.request
from pathlib import Path
import numpy as np, pandas as pd

SETS=["NEO","SNC","DMU","BRO","ONE","MOM","LTR","WOE","LCI","MKM","OTJ","BLB","DSK","FDN","DFT","TDM"]
ORDER="WUBRG"
PAIRS={"WU","WB","WR","WG","UB","UR","UG","BR","BG","RG"}

def canon(s):
    ss=set(str(s).upper())
    return "".join(c for c in ORDER if c in ss)

def main(feature_csv,outdir):
    out=Path(outdir);out.mkdir(parents=True,exist_ok=True)
    feat=pd.read_csv(feature_csv)
    if "FIN" in set(feat["set"].astype(str).str.upper()):raise SystemExit("FIN guard")
    windows=feat.groupby("set")[["window_start","window_end"]].first().to_dict("index")
    cards_out=[]; colors_out=[]; summary={}
    for s in SETS:
        if s not in windows:raise SystemExit(f"missing window {s}")
        st=pd.to_datetime(windows[s]["window_start"],utc=True)
        en=pd.to_datetime(windows[s]["window_end"],utc=True)
        url=f"https://17lands-public.s3.amazonaws.com/analysis_data/game_data/game_data_public.{s}.Sealed.csv.gz"
        fn=Path(tempfile.gettempdir())/f"{s}.Sealed.csv.gz"
        urllib.request.urlretrieve(url,fn)

        # Header only, then select necessary columns. All card columns are wide.
        hdr=pd.read_csv(fn,nrows=0).columns.tolist()
        oh=[c for c in hdr if c.startswith("opening_hand_")]
        dr=[c for c in hdr if c.startswith("drawn_")]
        names=[c[len("opening_hand_"):] for c in oh]
        drmap={c[len("drawn_"):]:c for c in dr}
        common=[n for n in names if n in drmap]
        timecol="game_time" if "game_time" in hdr else ("draft_time" if "draft_time" in hdr else None)
        basecols=["main_colors","splash_colors","won"]
        if timecol: basecols=[timecol]+basecols
        use=basecols+[f"opening_hand_{n}" for n in common]+[drmap[n] for n in common]

        gih_n={n:0.0 for n in common}; gih_w={n:0.0 for n in common}
        pair_n={p:0 for p in PAIRS};pair_w={p:0 for p in PAIRS}
        nrows=0;nwindow=0
        for ch in pd.read_csv(fn,usecols=use,chunksize=1500,low_memory=False):
            nrows+=len(ch)
            if timecol:
                gt=pd.to_datetime(ch[timecol],utc=True,errors="coerce")
                ch=ch[(gt>=st)&(gt<en)].copy()
            nwindow+=len(ch)
            if ch.empty:continue
            won=pd.to_numeric(ch["won"],errors="coerce").fillna(0).to_numpy(float)
            # Exact current GIH definition: opening hand + cards drawn later; tutored cards excluded.
            for n in common:
                a=pd.to_numeric(ch[f"opening_hand_{n}"],errors="coerce").fillna(0).to_numpy(float)
                b=pd.to_numeric(ch[drmap[n]],errors="coerce").fillna(0).to_numpy(float)
                x=a+b
                z=float(x.sum())
                if z:
                    gih_n[n]+=z;gih_w[n]+=float((x*won).sum())
            splash=ch["splash_colors"].fillna("").astype(str).str.strip()
            main=ch["main_colors"].fillna("").astype(str).map(canon)
            for p in PAIRS:
                m=(main==p)&(splash=="")
                nn=int(m.sum())
                if nn:
                    pair_n[p]+=nn;pair_w[p]+=int(pd.to_numeric(ch.loc[m,"won"],errors="coerce").fillna(0).sum())

        for n in common:
            if gih_n[n]>=30:
                cards_out.append({"set":s,"name":n,"sealed_gih_count":gih_n[n],"sealed_gih_wins":gih_w[n],"sealed_gih":gih_w[n]/gih_n[n]})
        for p in sorted(PAIRS):
            if pair_n[p]>0:
                colors_out.append({"set":s,"pair":p,"games":pair_n[p],"wins":pair_w[p],"actual_wr":pair_w[p]/pair_n[p]})
        summary[s]={"download_bytes":fn.stat().st_size,"all_rows":nrows,"window_rows":nwindow,
                    "cards_ge30":sum(1 for n in common if gih_n[n]>=30),"pair_games":pair_n}
        fn.unlink(missing_ok=True)
        print("SET_DONE",s,json.dumps(summary[s]))

    ca=pd.DataFrame(cards_out);co=pd.DataFrame(colors_out)
    ca.to_csv(out/"sealed_card_actuals.csv",index=False)
    co.to_csv(out/"sealed_color_actuals.csv",index=False)
    (out/"sealed_aggregate_report.json").write_text(json.dumps({"sets":SETS,"summary":summary},indent=2),encoding="utf-8")
    print("SUMMARY",json.dumps({"sets":len(SETS),"card_rows":len(ca),"color_rows":len(co),
      "missing_pairs":{s:sorted(PAIRS-set(co[co.set==s].pair)) for s in SETS}}))
if __name__=="__main__":main(sys.argv[1],sys.argv[2])
