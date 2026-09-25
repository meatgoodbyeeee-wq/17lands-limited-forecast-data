#!/usr/bin/env python3
import json,re,sys,time,urllib.parse,urllib.request,urllib.error
from pathlib import Path
import numpy as np,pandas as pd
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
sys.path.insert(0,"analysis")
import format_speed_mechanism_effects as fm

EXT=["TMT","SOS","MSH","HOB"]

def get_json(url):
    req=urllib.request.Request(url,headers={"User-Agent":"LimitedForecastResearch/3.0","Accept":"application/json"})
    for attempt in range(6):
        try:
            with urllib.request.urlopen(req,timeout=60) as r:return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code!=429 or attempt==5:raise
            time.sleep(min(2**attempt,20))

def fetch_cards(code):
    url="https://api.scryfall.com/cards/search?q="+urllib.parse.quote(f"e:{code.lower()}")
    cards=[]
    while url:
        d=get_json(url);cards+=d["data"];url=d.get("next_page") if d.get("has_more") else None
        time.sleep(.08)
    by={}
    for c in cards:
        if c.get("digital") and "arena" not in c.get("games",[]): continue
        by.setdefault(c["name"],c)
    return list(by.values())

def txt(c):
    faces=c.get("card_faces") or []
    return (c.get("oracle_text") or " ".join(x.get("oracle_text","") for x in faces)).lower()
def typ(c):
    faces=c.get("card_faces") or []
    return (c.get("type_line") or " ".join(x.get("type_line","") for x in faces)).lower()
def cols(c):
    faces=c.get("card_faces") or []
    return set(c.get("colors") or [z for f in faces for z in f.get("colors",[])])
def power(c):
    try:return float(c.get("power"))
    except:return 0.0

def feature_row(cards):
    use=[c for c in cards if c.get("rarity") in {"common","uncommon"} and "land" not in typ(c)]
    vals=[]; flags=[]; colors=[]
    for c in use:
        t=txt(c);ty=typ(c);mv=float(c.get("cmc") or 0);creature=int("creature" in ty)
        interaction=int(bool(re.search(r"destroy target|exile target|target creature gets -|deals? [^.]*damage to (any target|target creature|target permanent)|return target .* to (its|their) owner.?s hand",t)))
        ca=int(bool(re.search(r"draw (two|three|x|that many) cards",t)) or ("create" in t and "token" in t and ("enters" in t or "enter the battlefield" in t)))
        ev=int(any(x in t for x in ["flying","menace","can't be blocked","cannot be blocked"]))
        vals.append((mv,creature,int(interaction and mv<=3),ca,ev))
        flags.append(fm.text_flags(t,power(c),"planeswalker" in ty))
        colors.append(cols(c))
    a=np.array(vals,float);cr=a[a[:,1]==1]
    row={"mean_mv":float(a[:,0].mean()),"cheap_creature_share":float((cr[:,0]<=2).mean()),
         "cheap_interaction_share":float(a[:,2].mean()),"card_advantage_share":float(a[:,3].mean()),
         "evasion_share":float(a[:,4].mean()),"n":len(use)}
    row.update(fm.aggregate_mechanics(flags,colors))
    return row

def speed_targets():
    with urllib.request.urlopen("https://www.17lands.com/data/play_draw",timeout=30) as r: rows=json.load(r)["data"]
    out={str(x.get("expansion","")).upper():float(x["average_game_length"]) for x in rows
         if str(x.get("expansion","")).upper() in EXT and x.get("event_type")=="PremierDraft"}
    if set(out)!=set(EXT):raise SystemExit(f"missing external speed targets {sorted(set(EXT)-set(out))}")
    return out

def main(dev_csv,outdir):
    out=Path(outdir);out.mkdir(parents=True,exist_ok=True)
    hist=fm.hist_table(dev_csv)
    if "FIN" in set(hist.set) or "MH3" in set(hist.set) or len(hist)!=21:raise SystemExit("training guard")
    tar=speed_targets()
    ext=[]
    for code in EXT:
        row={"set":code,"actual":tar[code]};row.update(feature_row(fetch_cards(code)));ext.append(row)
    ext=pd.DataFrame(ext)

    candidates=["BASE","ENGINE","RESOURCE_ENGINE","SLOW_INDEX","LIFE"]
    rows=[]
    for _,r in ext.iterrows():
        z={"set":r["set"],"actual":float(r["actual"])}
        for name in candidates:
            m=make_pipeline(StandardScaler(),Ridge(alpha=10.0))
            m.fit(hist[fm.feats(name)],hist.turns)
            z[name]=float(m.predict(pd.DataFrame([r])[fm.feats(name)])[0])
            z[name+"_err"]=abs(z[name]-z["actual"])
        rows.append(z)
    metrics={n:float(np.mean([x[n+"_err"] for x in rows])) for n in candidates}
    report={"fin_used":False,"mh3_used":False,"training_sets":21,"external_sets":EXT,
            "metrics_mae":metrics,"rows":rows,
            "external_features":ext.to_dict("records")}
    (out/"format_speed_external_mechanism.json").write_text(json.dumps(report,indent=2,default=str),encoding="utf-8")
    print("SUMMARY",json.dumps(report,default=str))
if __name__=="__main__":main(sys.argv[1],sys.argv[2])
