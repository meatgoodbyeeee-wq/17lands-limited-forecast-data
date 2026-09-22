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
    # Cost/condition-aware Limited interaction features (pre-release only).
    tl=text.lower()
    removal_destroy=int(bool(re.search(r"destroy target",tl)))
    removal_exile=int(bool(re.search(r"exile target",tl)))
    damage_removal=int(bool(re.search(r"deals? [^.]*(damage) to (any target|target creature|target permanent)",tl)))
    bounce=int(bool(re.search(r"return target .* to (its|their) owner.?s hand",tl)))
    interaction=int(removal_destroy or removal_exile or damage_removal or bounce)
    f["interaction"]=interaction
    f["interaction_per_mv"]=interaction/mv
    f["cheap_interaction"]=int(interaction and f["mv"]<=3)
    conditional_words=["if ","unless ","only ","with power ","with toughness ","mana value ","that was dealt","attacking","blocking","tapped"]
    f["interaction_condition_count"]=sum(int(x in tl) for x in conditional_words) if interaction else 0
    f["clean_interaction"]=int(interaction and f["interaction_condition_count"]==0)
    card_adv=int(bool(re.search(r"draw (two|three|x|that many) cards",tl)) or ("create" in tl and "token" in tl and f["has_etb"]))
    f["card_advantage"]=card_adv
    f["card_advantage_per_mv"]=card_adv/mv
    evasion=int(any(x in tl for x in ["flying","menace","can't be blocked","cannot be blocked"]))
    f["evasion"]=evasion
    f["evasion_power_efficiency"]=(evasion*f["power"]/mv) if f["power"] is not None else None
    card_adv=int(bool(re.search(r"draw (two|three|x|that many) cards",tl)) or ("create" in tl and "token" in tl and f["has_etb"]))
    evasion=int(any(x in tl for x in ["flying","menace","can't be blocked","cannot be blocked"]))
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



def add_synergy_supply_features(feat):
    """Card-demand x set-supply features available from the full preview card pool."""
    x=feat.copy()
    tl=x["oracle_text"].fillna("").str.lower()
    typ=x["type_line"].fillna("").str.lower()
    # Demand: only cards that explicitly care about the resource receive the environment signal.
    demand_grave=(tl.str.contains("graveyard")|tl.str.contains("from your graveyard")).astype(int)
    demand_sac=(tl.str.contains("sacrifice")|tl.str.contains("whenever you sacrifice")).astype(int)
    demand_art=(tl.str.contains("artifact")).astype(int)
    demand_ench=(tl.str.contains("enchantment")).astype(int)
    demand_token=(tl.str.contains("token")).astype(int)
    demand_creature=(tl.str.contains("creature card")|tl.str.contains("creatures you control")).astype(int)
    # Supply proxies from card text/type only; no gameplay outcomes.
    grave_supply=(tl.str.contains("mill")|tl.str.contains("surveil")|tl.str.contains("discard")|tl.str.contains("put")&tl.str.contains("graveyard")).mean()
    sac_fodder=((tl.str.contains("create")&tl.str.contains("token"))|tl.str.contains("when this creature dies")|tl.str.contains("when ~ dies")).mean()
    art_supply=(typ.str.contains("artifact")|(tl.str.contains("create")&tl.str.contains("artifact"))).mean()
    ench_supply=typ.str.contains("enchantment").mean()
    token_supply=(tl.str.contains("create")&tl.str.contains("token")).mean()
    creature_supply=typ.str.contains("creature").mean()
    x["syn_graveyard_supply"]=demand_grave*float(grave_supply)
    x["syn_sacrifice_supply"]=demand_sac*float(sac_fodder)
    x["syn_artifact_supply"]=demand_art*float(art_supply)
    x["syn_enchantment_supply"]=demand_ench*float(ench_supply)
    x["syn_token_supply"]=demand_token*float(token_supply)
    x["syn_creature_supply"]=demand_creature*float(creature_supply)
    x["syn_demand_count"]=demand_grave+demand_sac+demand_art+demand_ench+demand_token+demand_creature
    return x

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--actuals",type=Path,required=True); ap.add_argument("--out",type=Path,default=Path("model_out/dev_feature_table.csv"))
    a=ap.parse_args(); actual=pd.read_csv(a.actuals)
    actual=actual.rename(columns={"card_name":"name","gih_wr":"actual_gih"})
    sets=set(actual["set"].str.upper())
    bad=sets-DEV_SETS
    if bad: raise SystemExit(f"Refusing non-development sets (FIN must remain untouched): {sorted(bad)}")
    rows=[]
    for s in sorted(sets):
        feat=add_synergy_supply_features(fetch_set(s)); x=actual[actual["set"].str.upper()==s].copy()
        m=x.merge(feat,on="name",how="inner"); rows.append(m)
        print(s,len(x),len(m))
    out=pd.concat(rows,ignore_index=True)
    a.out.parent.mkdir(parents=True,exist_ok=True); out.to_csv(a.out,index=False)
    print("wrote",a.out,len(out),"rows",len(out.columns),"columns")
if __name__=="__main__": main()
