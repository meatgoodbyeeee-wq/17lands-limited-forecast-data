#!/usr/bin/env python3
import gzip,json,sys
from pathlib import Path

PAIRS=["WU","WB","WR","WG","UB","UR","UG","BR","BG","RG"]
JP={"WU":"白青","WB":"白黒","WR":"白赤","WG":"白緑","UB":"青黒","UR":"青赤","UG":"青緑","BR":"黒赤","BG":"黒緑","RG":"赤緑"}
BASE=56.2316667933894
INTERCEPT=-0.8713450872574361
COEF=6.3117762712328265
ERR80=2.850668336137574

path=Path(sys.argv[1])
with gzip.open(path,"rt",encoding="utf-8") as f:
    root=json.load(f)
forecast=root.get("forecast",root)
cards=forecast["cards"]
pair_gih={}
counts={}
for pair in PAIRS:
    allowed=set(pair)
    vals=[]
    for c in cards:
        if c.get("rarity") not in {"common","uncommon"}: continue
        colors=set(c.get("colors") or [])
        if not colors: continue
        if not colors.issubset(allowed): continue
        v=c.get("pre_release_gih")
        if v is None: v=c.get("gih")
        if isinstance(v,(int,float)):
            vals.append(float(v))
    if not vals: raise SystemExit(f"no eligible cards for {pair}")
    pair_gih[pair]=sum(vals)/len(vals); counts[pair]=len(vals)

all_mean=sum(pair_gih.values())/len(PAIRS)
rows=[]
for pair in PAIRS:
    x=pair_gih[pair]-all_mean
    delta_env=INTERCEPT+COEF*x
    wr=BASE+delta_env
    rows.append({"colors":pair,"name":JP[pair],"n_cards":counts[pair],"pair_gih":pair_gih[pair],"predicted_wr":wr})
mean_wr=sum(r["predicted_wr"] for r in rows)/len(rows)
for r in rows:
    r["delta_vs_10color_mean"]=r["predicted_wr"]-mean_wr
    r["interval80_low"]=r["predicted_wr"]-ERR80
    r["interval80_high"]=r["predicted_wr"]+ERR80
rows.sort(key=lambda r:r["predicted_wr"],reverse=True)
for i,r in enumerate(rows,1): r["rank"]=i
print(json.dumps({"forecast_checked_at":forecast.get("checked_at"),"forecast_retrieved_at":forecast.get("retrieved_at"),"ten_color_mean_wr":mean_wr,"rows":rows},ensure_ascii=False))
