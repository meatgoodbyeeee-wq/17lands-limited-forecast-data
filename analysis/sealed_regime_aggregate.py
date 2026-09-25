#!/usr/bin/env python3
import sys,json,tempfile,urllib.request
from pathlib import Path
import pandas as pd

SETS=["NEO","SNC","DMU","BRO","ONE","MOM","LTR","WOE","LCI","MKM","OTJ","BLB","DSK","FDN","DFT","TDM"]
ORDER="WUBRG"

def canon(s):
    ss=set(str(s).upper())
    return "".join(c for c in ORDER if c in ss)

def main(feature_csv,outdir):
    out=Path(outdir); out.mkdir(parents=True,exist_ok=True)
    feat=pd.read_csv(feature_csv)
    if "FIN" in set(feat["set"].astype(str).str.upper()): raise SystemExit("FIN guard")
    windows=feat.groupby("set")[["window_start","window_end"]].first().to_dict("index")
    rows=[]; summary={}
    for s in SETS:
        st=pd.to_datetime(windows[s]["window_start"],utc=True)
        en=pd.to_datetime(windows[s]["window_end"],utc=True)
        url=f"https://17lands-public.s3.amazonaws.com/analysis_data/game_data/game_data_public.{s}.Sealed.csv.gz"
        fn=Path(tempfile.gettempdir())/f"{s}.Sealed.csv.gz"
        urllib.request.urlretrieve(url,fn)
        hdr=pd.read_csv(fn,nrows=0).columns.tolist()
        timecol="game_time" if "game_time" in hdr else ("draft_time" if "draft_time" in hdr else None)
        use=["main_colors","splash_colors","won"] + ([timecol] if timecol else [])
        agg={}
        nwindow=0
        for ch in pd.read_csv(fn,usecols=use,chunksize=20000,low_memory=False):
            if timecol:
                gt=pd.to_datetime(ch[timecol],utc=True,errors="coerce")
                ch=ch[(gt>=st)&(gt<en)].copy()
            nwindow+=len(ch)
            if ch.empty: continue
            main=ch.main_colors.fillna("").astype(str).map(canon)
            splash=ch.splash_colors.fillna("").astype(str).map(canon)
            won=pd.to_numeric(ch.won,errors="coerce").fillna(0).astype(int)
            for mc,sp,w in zip(main,splash,won):
                nm=len(mc); ns=len(sp)
                if nm==2 and ns==0:
                    regime="PURE2"; key=mc
                elif nm==2 and ns>0:
                    regime="PAIR_SPLASH"; key=mc
                elif nm>=3:
                    regime="MAIN3PLUS"; key=mc
                else:
                    regime="OTHER"; key=mc or "NONE"
                k=(regime,key)
                if k not in agg: agg[k]=[0,0]
                agg[k][0]+=1; agg[k][1]+=int(w)
        for (regime,key),(g,w) in agg.items():
            rows.append({"set":s,"regime":regime,"color_key":key,"n_main_colors":len(key),
                         "games":g,"wins":w,"actual_wr":w/g})
        sd={}
        for regime in ["PURE2","PAIR_SPLASH","MAIN3PLUS","OTHER"]:
            rr=[r for r in rows if r["set"]==s and r["regime"]==regime]
            g=sum(r["games"] for r in rr); w=sum(r["wins"] for r in rr)
            sd[regime]={"games":g,"wr":w/g if g else None,"groups":len(rr),"groups_ge100":sum(r["games"]>=100 for r in rr)}
        summary[s]={"window_games":nwindow,"regimes":sd}
        print("SET",s,json.dumps(summary[s]))
        fn.unlink(missing_ok=True)

    df=pd.DataFrame(rows)
    df.to_csv(out/"sealed_regime_actuals.csv",index=False)
    (out/"sealed_regime_report.json").write_text(json.dumps({"sets":SETS,"summary":summary},indent=2),encoding="utf-8")
    totals=df.groupby("regime").agg(games=("games","sum"),groups=("color_key","count")).reset_index()
    print("SUMMARY",json.dumps({"totals":totals.to_dict("records"),
      "ge100":df.groupby("regime").apply(lambda x:int((x.games>=100).sum()),include_groups=False).to_dict()}))
if __name__=="__main__": main(sys.argv[1],sys.argv[2])
