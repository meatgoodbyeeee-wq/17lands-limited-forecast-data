#!/usr/bin/env python3
"""Build a FIN-blind feature table from Scryfall bulk/card API metadata + 17Lands aggregates.

FIN is deliberately rejected: this builder is for development sets only.
Outputs numeric, pre-release-available card features suitable for LOSO modeling.
"""
import argparse, json, re, urllib.parse, urllib.request
from pathlib import Path
import pandas as pd

DEV_SETS={"BLB","DSK","FDN","DFT","TDM"}
TYPE_WORDS=["Creature","Instant","Sorcery","Artifact","Enchantment","Planeswalker","Land"]
KEYWORDS=["flying","first strike","double strike","deathtouch","haste","hexproof","lifelink",
          "menace","reach","trample","vigilance","ward","draw","discard","destroy","exile",
          "counter","token","sacrifice","return","graveyard","search","damage","gain","surveil",
          "scry","mill"]
RARITY={"common":0,"uncommon":1,"rare":2,"mythic":3}

def get_json(url):
    req=urllib.request.Request(url,headers={"User-Agent":"LimitedForecastResearch/2.0"})
    with urllib.request.urlopen(req,timeout=60) as r: return json.load(r)

def card_features(c):
    faces=c.get("card_faces") or []
    text=c.get("oracle_text") or " ".join(x.get("oracle_text","") for x in faces)
    typ=c.get("type_line") or " ".join(x.get("type_line","") for x in faces)
    mana=c.get("mana_cost") or " ".join(x.get("mana_cost","") for x in faces)
    colors=c.get("colors") or sorted({z for x in faces for z in x.get("colors",[])})
    power=c.get("power"); toughness=c.get("toughness")
    def num(x):
        try:return float(x)
        except:return None
    f={"name":c["name"],"collector_number":c.get("collector_number"),"mv":float(c.get("cmc") or 0),
       "rarity_ord":RARITY.get(c.get("rarity"),-1),"n_colors":len(colors),"mana_symbols":mana.count("{"),
       "oracle_len":len(text),"oracle_lines":text.count("\n")+bool(text),"power":num(power),"toughness":num(toughness)}
    for w in TYPE_WORDS:f["type_"+w.lower()]=int(w.lower() in typ.lower())
    for k in KEYWORDS:f["kw_"+k.replace(" ","_")]=int(k in text.lower())
    for col in "WUBRG":f["color_"+col]=int(col in colors)
    return f

def fetch_set(code):
    url="https://api.scryfall.com/cards/search?q="+urllib.parse.quote(f"e:{code.lower()} game:arena")
    out=[]
    while url:
        d=get_json(url); out += [card_features(c) for c in d["data"] if not c.get("digital") or "arena" in c.get("games",[])]
        url=d.get("next_page") if d.get("has_more") else None
    return pd.DataFrame(out).drop_duplicates("name")

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--actuals",type=Path,required=True); ap.add_argument("--out",type=Path,default=Path("model_out/dev_feature_table.csv"))
    a=ap.parse_args(); actual=pd.read_csv(a.actuals)
    actual=actual.rename(columns={"card_name":"name","gih_wr":"actual_gih"})
    sets=set(actual["set"].str.upper())
    bad=sets-DEV_SETS
    if bad: raise SystemExit(f"Refusing non-development sets (FIN must remain untouched): {sorted(bad)}")
    rows=[]
    for s in sorted(sets):
        feat=fetch_set(s); x=actual[actual["set"].str.upper()==s].copy()
        m=x.merge(feat,on="name",how="inner"); rows.append(m)
        print(s,len(x),len(m))
    out=pd.concat(rows,ignore_index=True)
    a.out.parent.mkdir(parents=True,exist_ok=True); out.to_csv(a.out,index=False)
    print("wrote",a.out,len(out),"rows",len(out.columns),"columns")
if __name__=="__main__": main()
