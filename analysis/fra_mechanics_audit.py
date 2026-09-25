#!/usr/bin/env python3
import gzip,json,re,sys,math
from collections import Counter
import pandas as pd

hist=pd.read_csv(sys.argv[1])
hist=hist[(hist["set"]!="MH3") & hist["rarity_ord"].isin([0,1]) & hist["type_land"].eq(0)]
with gzip.open(sys.argv[2],"rt",encoding="utf-8") as f: root=json.load(f)
cards=root.get("cards") or root.get("forecast",{}).get("cards") or root.get("target",{}).get("cards")
fra=[c for c in cards if c.get("rarity") in {"common","uncommon"} and "land" not in (c.get("type_line") or "").lower()]

stop=set("""the a an and or of to in on with without from for as at this that it its you your opponent opponents player players card cards creature creatures target each one two three up may if when whenever until end turn control battlefield enters enter has have gets get put into is are was be by than other another choose chosen any all then only can can't cannot would could where while among equal number more less their they them""".replace("'","").split())
def toks(text):
    return [w for w in re.findall(r"[a-z][a-z\-']+",(text or "").lower()) if len(w)>=4 and w.replace("'","") not in stop]

hc=Counter()
for t in hist.oracle_text.fillna(""): hc.update(set(toks(t)))
fc=Counter()
for c in fra: fc.update(set(toks(c.get("oracle_text",""))))
HN=len(hist); FN=len(fra)
arr=[]
for w,n in fc.items():
    if n<2: continue
    p=(n+.5)/(FN+1); q=(hc[w]+.5)/(HN+1)
    arr.append((math.log(p/q),n,hc[w],w))

setup=[]
for c in fra:
    tx=(c.get("oracle_text") or "").lower()
    if re.search(r"\b(prepared|prep|heartwood|landcycling)\b",tx):
        setup.append(c.get("name"))

print("FRA_CU_NONLAND",FN)
print("FRA_SETUP_COUNT",len(setup))
print("FRA_SETUP_SHARE",len(setup)/FN)
print("FRA_SETUP_CARDS",json.dumps(setup,ensure_ascii=False))
print("TOP_TERMS",json.dumps([{"term":w,"fra_cards":n,"hist_cards":h,"log_ratio":round(sc,3)} for sc,n,h,w in sorted(arr,reverse=True)[:50]],ensure_ascii=False))
