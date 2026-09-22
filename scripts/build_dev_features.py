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
    req=urllib.request.Request(url,headers={"User-Agent":"LimitedForecastResearch/2.0","Accept":"application/json"})
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
    f={"name":c["name"],"collector_number":c.get("collector_number"),"oracle_text":text,"type_line":typ,"mv":float(c.get("cmc") or 0),
       "rarity_ord":RARITY.get(c.get("rarity"),-1),"n_colors":len(colors),"mana_symbols":mana.count("{"),
       "oracle_len":len(text),"oracle_lines":text.count("\n")+bool(text),"power":num(power),"toughness":num(toughness)}
    for w in TYPE_WORDS:f["type_"+w.lower()]=int(w.lower() in typ.lower())
    for k in KEYWORDS:f["kw_"+k.replace(" ","_")]=int(k in text.lower())
    for col in "WUBRG":f["color_"+col]=int(col in colors)
    # Pre-release structural features aimed at identifying weak/strong tails.
    mv=max(f["mv"],1.0)
    f["is_multicolor"]=int(len(colors)>1)
    f["is_colorless"]=int(len(colors)==0)
    f["has_x_cost"]=int("{X}" in mana.upper())
    f["is_aura"]=int("aura" in typ.lower())
    f["is_equipment"]=int("equipment" in typ.lower())
    f["is_vehicle"]=int("vehicle" in typ.lower())
    f["has_etb"]=int(("enters" in text.lower()) or ("enter the battlefield" in text.lower()))
    f["has_eot"]=int("until end of turn" in text.lower())
    f["targets_creature"]=int("target creature" in text.lower())
    f["keyword_count"]=sum(f["kw_"+k.replace(" ","_")] for k in KEYWORDS)
    f["ability_sentences"]=text.count(".")+text.count(";")
    # Limited-specific semantic features, all available before release.
    tl=text.lower()
    f["sem_removal_destroy"]=int(bool(re.search(r"destroy target|destroy all|destroy each",tl)))
    f["sem_removal_exile"]=int(bool(re.search(r"exile target|exile all|exile each",tl)))
    f["sem_damage_target"]=int("damage to target" in tl or bool(re.search(r"deals? [^.]*(damage) to (any target|target creature|target permanent)",tl)))
    f["sem_bounce"]=int(bool(re.search(r"return target .* to (its|their) owner.?s hand",tl)))
    f["sem_tap_freeze"]=int("tap target" in tl and ("doesn't untap" in tl or "does not untap" in tl))
    f["sem_combat_trick"]=int("until end of turn" in tl and ("target creature" in tl or "target attacking" in tl or "target blocking" in tl))
    f["sem_draw_cards"]=int(bool(re.search(r"draw (a|one|two|three|x|that many) card",tl)))
    f["sem_impulse_draw"]=int("exile" in tl and ("you may play" in tl or "you may cast" in tl))
    f["sem_loot"]=int("draw" in tl and "discard" in tl)
    f["sem_token_maker"]=int("create" in tl and "token" in tl)
    f["sem_reanimate"]=int(("return target" in tl or "return a" in tl) and "graveyard" in tl and "battlefield" in tl)
    f["sem_recursion_hand"]=int("graveyard" in tl and "to your hand" in tl)
    f["sem_evasion"]=int(any(x in tl for x in ["flying","menace","can't be blocked","cannot be blocked"]))
    f["sem_protection"]=int(any(x in tl for x in ["hexproof","indestructible","protection from","phase out"]))
    f["sem_ramp"]=int(("add {" in tl) or ("search your library" in tl and "land" in tl))
    f["sem_cost_reduction"]=int("costs {" in tl and " less to cast" in tl)
    f["sem_repeatable"]=int(":" in text)
    f["sem_sac_outlet"]=int("sacrifice" in tl and ":" in text)
    f["sem_etb_value"]=int(f["has_etb"] and any(x in tl for x in ["draw","destroy","exile","damage","create","return target","surveil","scry"]))
    f["sem_two_for_one_proxy"]=int(sum([f["sem_draw_cards"],f["sem_token_maker"],f["sem_reanimate"],f["sem_etb_value"]])>=2)
    f["power_per_mv"]=(f["power"]/mv) if f["power"] is not None else None
    f["toughness_per_mv"]=(f["toughness"]/mv) if f["toughness"] is not None else None
    f["stats_per_mv"]=((f["power"]+f["toughness"])/mv) if f["power"] is not None and f["toughness"] is not None else None
    return f

def fetch_set(code):
    url="https://api.scryfall.com/cards/search?q="+urllib.parse.quote(f"e:{code.lower()}")
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
