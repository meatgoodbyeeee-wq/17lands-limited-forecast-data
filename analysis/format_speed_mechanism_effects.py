#!/usr/bin/env python3
import gzip,json,re,sys,urllib.request,itertools
from pathlib import Path
import numpy as np,pandas as pd
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ALL22={"KHM","STX","AFR","MID","VOW","NEO","SNC","DMU","BRO","ONE","MOM","LTR","WOE","LCI","MKM","OTJ","MH3","BLB","DSK","FDN","DFT","TDM"}
DEV=ALL22-{"MH3"}
BASE=["mean_mv","cheap_creature_share","cheap_interaction_share","card_advantage_share","evasion_share"]
PAIRS={"WU":{"W","U"},"WB":{"W","B"},"WR":{"W","R"},"WG":{"W","G"},"UB":{"U","B"},"UR":{"U","R"},"UG":{"U","G"},"BR":{"B","R"},"BG":{"B","G"},"RG":{"R","G"}}

# Mechanic names are mapped to common GAME-SPEED EFFECTS, not used as separate set labels.
DELAY_TERMS=["foretell","disturb","unearth","adventure","plot","impending","harmonize","renew","prepared","landcycling","flashback","escape","jump-start","retrace","suspend","rebound","aftermath"]
ENGINE_TERMS=["venture into the dungeon","the ring tempts","level up","class","case","solve","unlock","room","oil counter","proliferate","start your engines","max speed","exhaust","empower jace","lore counter"]
RECUR_TERMS=["disturb","unearth","renew","harmonize","escape","flashback","jump-start","retrace","descend","forage","threshold","collect evidence","manifest dread"]
PRESSURE_TERMS=["boast","pack tactics","blitz","enlist","toxic","corrupted","celebration","suspect","saddle","valiant","survival","mobilize","prowess"]
MANA_TERMS=["treasure token","powerstone","heartwood","landcycling"]

def targets():
    with urllib.request.urlopen("https://www.17lands.com/data/play_draw",timeout=30) as r: rows=json.load(r)["data"]
    out={str(x.get("expansion","")).upper():float(x["average_game_length"]) for x in rows
         if str(x.get("expansion","")).upper() in DEV and x.get("event_type")=="PremierDraft"}
    if set(out)!=DEV: raise SystemExit("target set guard failed")
    return out

def text_flags(text, power=0.0, is_pw=False):
    t=(text or "").lower()
    delay=float(any(k in t for k in DELAY_TERMS) or bool(re.search(r"you may (?:cast|play) .* from (?:exile|your graveyard)",t)))
    # Persistent engine: something that creates/advances reusable future value.
    engine=float(any(k in t for k in ENGINE_TERMS) or is_pw or
                 bool(re.search(r"at the beginning of (?:your|each) (?:upkeep|end step)",t)) or
                 bool(re.search(r"once each turn|the first time .* each turn",t)))
    # Empower intensity: loyalty is stored future value; scale gently so one huge empower does not dominate.
    m=re.search(r"empower jace\s+(\d+)",t)
    if m: engine=max(engine,1.0+min(int(m.group(1)),8)/16.0)

    recur=float(any(k in t for k in RECUR_TERMS) or "from your graveyard" in t or "in your graveyard" in t)
    pressure=float(any(k in t for k in PRESSURE_TERMS) or "haste" in t or
                   bool(re.search(r"whenever .* attacks|whenever you attack",t)))

    # Race buffering: approximate life actually added, not merely the presence of the word gain.
    lg=0.0
    for mm in re.finditer(r"gain\s+(\d+)\s+life",t):
        lg=max(lg,min(float(mm.group(1)),6.0)/3.0)
    if re.search(r"gain[s]? x life|gain life equal to|gain that much life",t): lg=max(lg,1.5)
    if "lifelink" in t: lg=max(lg,min(max(float(power or 0),1.0),6.0)/3.0)
    if "food token" in t: lg=max(lg,1.0)
    payoff=float(bool(re.search(r"whenever you gain life|if you gained life|life you gained",t)))

    mana=float(any(k in t for k in MANA_TERMS) or
               bool(re.search(r"search your library for (?:a|up to one) .*land",t)) or
               bool(re.search(r"\{t\}: add \{[wubrgc]\}",t)))
    return {"delay":delay,"engine":engine,"recur":recur,"pressure":pressure,
            "race_buffer":lg,"lifegain_payoff":payoff,"mana_dev":mana}

def card_colors_from_hist(g):
    out=[]
    for _,r in g.iterrows():
        out.append({c for c in "WUBRG" if float(r.get("color_"+c,0) or 0)>0})
    return out

def aggregate_mechanics(flags, colors):
    md=pd.DataFrame(flags)
    out={}
    dims=["delay","engine","recur","pressure","race_buffer","mana_dev"]
    for d in dims:
        out[d+"_mean"]=float(md[d].mean())
        pairvals=[]
        for pair,cs in PAIRS.items():
            idx=[i for i,col in enumerate(colors) if col and col.issubset(cs)]
            if idx: pairvals.append(float(md.iloc[idx][d].mean()))
        out[d+"_pairmax"]=max(pairvals) if pairvals else 0.0

    # Lifegain synergy must coexist within a color pair; whole-set averages hide GW-type archetypes.
    syn=[]
    for pair,cs in PAIRS.items():
        idx=[i for i,col in enumerate(colors) if col and col.issubset(cs)]
        if idx:
            sub=md.iloc[idx]
            syn.append(float(np.sqrt(sub["race_buffer"].clip(0,1).mean()*sub["lifegain_payoff"].mean())))
    out["lifegain_synergy_pairmax"]=max(syn) if syn else 0.0

    # Pre-composed slow-vs-pressure index reduces dimensionality.
    out["slow_effect_mean"]=out["delay_mean"]+out["engine_mean"]+out["recur_mean"]+out["race_buffer_mean"]+0.5*out["mana_dev_mean"]-out["pressure_mean"]
    out["slow_effect_pairmax"]=out["delay_pairmax"]+out["engine_pairmax"]+out["recur_pairmax"]+out["race_buffer_pairmax"]+0.5*out["mana_dev_pairmax"]-out["pressure_pairmax"]
    return out

def hist_table(path):
    d=pd.read_csv(path)
    sets=set(d["set"].astype(str).str.upper())
    if "FIN" in sets or sets!=ALL22: raise SystemExit("FIN/set guard failed")
    d=d[d["set"].ne("MH3") & d["rarity_ord"].isin([0,1]) & d["type_land"].eq(0)].copy()
    tar=targets(); rows=[]
    for s,g in d.groupby("set"):
        cr=g[g.type_creature.eq(1)]
        flags=[text_flags(str(r.oracle_text or ""),r.power, bool(r.type_planeswalker)) for _,r in g.iterrows()]
        row={"set":s,"start_date":pd.to_datetime(g.window_start.iloc[0]),"turns":tar[s],
             "mean_mv":float(g.mv.mean()),"cheap_creature_share":float((cr.mv<=2).mean()) if len(cr) else 0,
             "cheap_interaction_share":float(g.cheap_interaction.mean()),"card_advantage_share":float(g.card_advantage.mean()),
             "evasion_share":float(g.evasion.mean())}
        row.update(aggregate_mechanics(flags,card_colors_from_hist(g)))
        rows.append(row)
    return pd.DataFrame(rows)

def fra_table(path):
    with gzip.open(path,"rt",encoding="utf-8") as f: root=json.load(f)
    cards=root.get("cards") or root.get("forecast",{}).get("cards") or root.get("target",{}).get("cards")
    use=[c for c in cards if c.get("rarity") in {"common","uncommon"} and "land" not in (c.get("type_line") or "").lower()]
    vals=[];flags=[];colors=[]
    for c in use:
        t=(c.get("oracle_text") or "").lower(); typ=(c.get("type_line") or "").lower(); mv=float(c.get("cmc",c.get("mv",0)) or 0)
        creature=int("creature" in typ)
        interaction=int(bool(re.search(r"destroy target|exile target|target creature gets -|deals? [^.]*damage to (any target|target creature|target permanent)|return target .* to (its|their) owner.?s hand",t)))
        ca=int(bool(re.search(r"draw (two|three|x|that many) cards",t)) or ("create" in t and "token" in t and ("enters" in t or "enter the battlefield" in t)))
        ev=int(any(x in t for x in ["flying","menace","can't be blocked","cannot be blocked"]))
        vals.append((mv,creature,int(interaction and mv<=3),ca,ev))
        p=c.get("power")
        try:p=float(p)
        except:p=0.0
        flags.append(text_flags(t,p,"planeswalker" in typ))
        colors.append(set(c.get("colors") or []))
    a=np.array(vals,float); cr=a[a[:,1]==1]
    row={"mean_mv":float(a[:,0].mean()),"cheap_creature_share":float((cr[:,0]<=2).mean()),
         "cheap_interaction_share":float(a[:,2].mean()),"card_advantage_share":float(a[:,3].mean()),
         "evasion_share":float(a[:,4].mean()),"n":len(use)}
    row.update(aggregate_mechanics(flags,colors))
    return row

GROUPS={
 "BASE":[],
 "DELAY":["delay_mean","delay_pairmax"],
 "ENGINE":["engine_mean","engine_pairmax"],
 "RECUR":["recur_mean","recur_pairmax"],
 "LIFE":["race_buffer_mean","race_buffer_pairmax","lifegain_synergy_pairmax"],
 "MANA":["mana_dev_mean","mana_dev_pairmax"],
 "PRESSURE":["pressure_mean","pressure_pairmax"],
 "SLOW_INDEX":["slow_effect_mean","slow_effect_pairmax"],
}
# Limited, predeclared 2-effect combinations to test interactions without an exhaustive search.
COMBOS={
 "ENGINE_LIFE":GROUPS["ENGINE"]+GROUPS["LIFE"],
 "DELAY_ENGINE":GROUPS["DELAY"]+GROUPS["ENGINE"],
 "RESOURCE_ENGINE":GROUPS["DELAY"]+GROUPS["ENGINE"]+GROUPS["RECUR"],
}

def feats(name): return BASE+GROUPS.get(name,COMBOS.get(name,[]))
CAND=list(GROUPS)+list(COMBOS)

def fit_predict(train,test,name):
    m=make_pipeline(StandardScaler(),Ridge(alpha=10.0))
    m.fit(train[feats(name)],train.turns)
    return m.predict(test[feats(name)])

def loo_mae(df,name):
    es=[]
    for s in df.set:
        tr=df[df.set.ne(s)];te=df[df.set.eq(s)]
        es.append(abs(float(te.turns.iloc[0])-float(fit_predict(tr,te,name)[0])))
    return float(np.mean(es))

def outer_nested(df):
    rows=[]
    for hold in df.set:
        tr=df[df.set.ne(hold)];te=df[df.set.eq(hold)]
        scores={name:loo_mae(tr,name) for name in CAND}
        choice=min(scores,key=scores.get)
        p=float(fit_predict(tr,te,choice)[0]); y=float(te.turns.iloc[0])
        rows.append({"set":hold,"actual":y,"pred":p,"abs_err":abs(y-p),"selected":choice,"inner_scores":scores})
    return rows

def forward(df,name,min_train=8):
    d=df.sort_values("start_date").reset_index(drop=True);es=[];rows=[]
    for i in range(min_train,len(d)):
        tr=d.iloc[:i];te=d.iloc[[i]]
        p=float(fit_predict(tr,te,name)[0]);y=float(te.turns.iloc[0])
        es.append(abs(y-p));rows.append({"set":te.set.iloc[0],"pred":p,"actual":y,"abs_err":abs(y-p)})
    return float(np.mean(es)),rows

def main(dev_csv,fra_gz,outdir):
    out=Path(outdir);out.mkdir(parents=True,exist_ok=True)
    df=hist_table(dev_csv);fra=fra_table(fra_gz)
    cv={n:loo_mae(df,n) for n in CAND}
    nested=outer_nested(df); nested_mae=float(np.mean([x["abs_err"] for x in nested]))
    nested_counts={n:sum(x["selected"]==n for x in nested) for n in CAND}

    # Final candidate selection uses only 21-set internal LOO, not FRA or external test results.
    chosen=min(cv,key=cv.get)
    fwd={n:forward(df,n)[0] for n in CAND}
    m=make_pipeline(StandardScaler(),Ridge(alpha=10.0));m.fit(df[feats(chosen)],df.turns)
    fp=float(m.predict(pd.DataFrame([fra])[feats(chosen)])[0])

    # Empirical error for chosen fixed family.
    errors=[]
    for s in df.set:
        tr=df[df.set.ne(s)];te=df[df.set.eq(s)]
        errors.append(float(te.turns.iloc[0])-float(fit_predict(tr,te,chosen)[0]))
    ae=np.abs(errors)

    report={"fin_used":False,"mh3_used":False,"n_sets":21,"base_features":BASE,"candidate_groups":{k:feats(k) for k in CAND},
            "cv_mae":cv,"forward_mae":fwd,"nested":{"mae":nested_mae,"selection_counts":nested_counts,"folds":nested},
            "fra_features":fra,"chosen":chosen,"fra_pred_turns":fp,
            "interval80":float(np.quantile(ae,.8,method="higher")),"interval90":float(np.quantile(ae,.9,method="higher"))}
    (out/"format_speed_mechanism_effects.json").write_text(json.dumps(report,indent=2,default=str),encoding="utf-8")
    df.to_csv(out/"format_speed_mechanism_features.csv",index=False)
    print("SUMMARY",json.dumps({"cv_mae":cv,"forward_mae":fwd,"nested_mae":nested_mae,"nested_counts":nested_counts,
      "chosen":chosen,"fra_pred":fp,"interval80":report["interval80"],"interval90":report["interval90"],
      "fra_mechanics":{k:v for k,v in fra.items() if k not in BASE}},ensure_ascii=False))
if __name__=="__main__":main(sys.argv[1],sys.argv[2],sys.argv[3])
