#!/usr/bin/env python3
import json,re,time,urllib.parse,urllib.request,urllib.error,sys
from pathlib import Path
import numpy as np,pandas as pd
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

EXT_TARGETS={"HOB":8.572,"MSH":9.002,"SOS":9.003,"TMT":9.134}
BASE=["mean_mv","cheap_creature_share","cheap_interaction_share","card_advantage_share","evasion_share"]
ORIGIN=pd.Timestamp("2021-01-01",tz="UTC")

def get_json(url):
    req=urllib.request.Request(url,headers={"User-Agent":"LimitedForecastResearch/2.0","Accept":"application/json"})
    for attempt in range(6):
        try:
            with urllib.request.urlopen(req,timeout=60) as r:return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code!=429 or attempt==5:raise
            time.sleep(min(2**attempt,20))

def fetch_set(code):
    url="https://api.scryfall.com/cards/search?q="+urllib.parse.quote(f"e:{code.lower()}")
    cards=[]
    while url:
        d=get_json(url); cards+=d["data"]; url=d.get("next_page") if d.get("has_more") else None
        time.sleep(.08)
    by={}
    for c in cards:
        if c.get("digital") and "arena" not in c.get("games",[]):continue
        by.setdefault(c["name"],c)
    meta=get_json("https://api.scryfall.com/sets/"+code.lower())
    return list(by.values()),meta["released_at"]

def txt(c):
    faces=c.get("card_faces") or []
    return (c.get("oracle_text") or " ".join(x.get("oracle_text","") for x in faces)).lower()
def typ(c):
    faces=c.get("card_faces") or []
    return (c.get("type_line") or " ".join(x.get("type_line","") for x in faces)).lower()
def cmc(c):return float(c.get("cmc") or 0)
def flag(t,terms=None,pat=None):
    if terms and any(x in t for x in terms): return 1
    return int(bool(re.search(pat,t))) if pat else 0

def row_flags(t):
    lifegain=flag(t,pat=r"gain[s]? (?:\d+|x|that much|life equal|an amount of) life|lifelink")
    repeat=flag(t,pat=r"at the beginning of (?:your|each) (?:upkeep|end step)|once each turn|the first time .* each turn|whenever .* (?:draw|cast|enters|dies|attacks|gain|discard|sacrifice)|\{t\}:")
    return {
      "f_progressive":flag(t,["level up","transform","case","solve","unlock","descend","collect evidence","finality counter","oil counter","lore counter"],r"put .* counter"),\n      "m_banked_value":flag(t,["foretell","disturb","unearth","adventure","plot","impending","harmonize","renew"],r"you may (?:cast|play) .* from exile|until the end of your next turn"),
      "m_progress_engine":flag(t,["venture into the dungeon","the ring tempts","oil counter","proliferate","case","solve","start your engines","max speed","exhaust"],r"put .* counter .* (?:each|whenever)|at the beginning of your upkeep .* counter"),
      "m_resource_extension":flag(t,["learn","lesson","foretell","disturb","blood token","unearth","adventure","plot","offspring","manifest dread","room","impending","harmonize","renew"],r"from your graveyard|you may cast .* from exile|you may play .* from exile"),
      "m_graveyard_engine":flag(t,["disturb","unearth","descend","collect evidence","forage","manifest dread","threshold","renew","harmonize"],r"from your graveyard|in your graveyard|cards? in your graveyard"),
      "m_aggression":flag(t,["boast","pack tactics","decayed","training","ninjutsu","blitz","enlist","toxic","corrupted","backup","celebration","suspect","saddle","valiant","survival","mobilize"],r"whenever .* attacks|\bhaste\b|\bprowess\b"),
      "m_mana_development":flag(t,["powerstone","treasure token"],r"add \{[wubrgc]\}|search your library for .* land"),
      "m_race_buffer":int(lifegain or flag(t,["food token","shield counter"])),
      "m_lifegain_engine":int(lifegain and (repeat or flag(t,pat=r"whenever you gain life|if you gained life|life you gained"))),
      "m_board_scaling":flag(t,["modified","training","backup","incubate","role token","offspring","oil counter","proliferate"],r"\+1/\+1 counter"),
      "m_repeatable_value":int(repeat or flag(t,["venture into the dungeon","the ring tempts","oil counter","proliferate","case","solve","start your engines","max speed","exhaust"]))
    }

PAIRS={"WU":["W","U"],"WB":["W","B"],"WR":["W","R"],"WG":["W","G"],"UB":["U","B"],"UR":["U","R"],"UG":["U","G"],"BR":["B","R"],"BG":["B","G"],"RG":["R","G"]}
def colors(c):
    faces=c.get("card_faces") or []
    return set(c.get("colors") or [z for x in faces for z in x.get("colors",[])])

def external_features(code):
    cards,released=fetch_set(code)
    use=[c for c in cards if c.get("rarity") in {"common","uncommon"} and "land" not in typ(c)]
    vals=[]; mechs=[]; card_colors=[]
    for c in use:
        t=txt(c); ty=typ(c); mv=cmc(c)
        creature=int("creature" in ty)
        interaction=int(bool(re.search(r"destroy target|exile target|target creature gets -|deals? [^.]*damage to (any target|target creature|target permanent)|return target .* to (its|their) owner.?s hand",t)))
        ca=int(bool(re.search(r"draw (two|three|x|that many) cards",t)) or ("create" in t and "token" in t and ("enters" in t or "enter the battlefield" in t)))
        ev=int(any(x in t for x in ["flying","menace","can't be blocked","cannot be blocked"]))
        vals.append((mv,creature,int(interaction and mv<=3),ca,ev)); mechs.append(row_flags(t)); card_colors.append(colors(c))
    a=np.array(vals,float); cr=a[a[:,1]==1]
    out={"set":code,"release_date":released,"year_num":(pd.Timestamp(released,tz="UTC")-ORIGIN).days/365.25,
         "mean_mv":float(a[:,0].mean()),"cheap_creature_share":float((cr[:,0]<=2).mean()),
         "cheap_interaction_share":float(a[:,2].mean()),"card_advantage_share":float(a[:,3].mean()),"evasion_share":float(a[:,4].mean()),"n":len(a)}
    md=pd.DataFrame(mechs)
    for c in md.columns:out[c+"_share"]=float(md[c].mean())
    return out

def hist_progress_pairmax(dev):
    d=dev[(dev["set"]!="MH3") & dev["rarity_ord"].isin([0,1]) & dev["type_land"].eq(0)].copy()
    rows=[]
    for ss,g in d.groupby("set"):
        flags=g.oracle_text.fillna("").str.lower().apply(lambda t: row_flags(t)["f_progressive"]).to_numpy(float)
        pv=[]
        for pair,cs in PAIRS.items():
            mask=np.ones(len(g),dtype=bool)
            for col in "WUBRG":
                if col not in cs: mask &= g["color_"+col].fillna(0).to_numpy()==0
            ncol=g[["color_"+col for col in "WUBRG"]].fillna(0).sum(axis=1).to_numpy()
            mask &= ncol>0
            if mask.any(): pv.append(float(flags[mask].mean()))
        rows.append({"set":ss,"f_progressive_pairmax":max(pv) if pv else 0.0})
    return pd.DataFrame(rows)

def hist_mechanics(dev):
    d=dev[(dev["set"]!="MH3") & dev["rarity_ord"].isin([0,1]) & dev["type_land"].eq(0)].copy()
    rows=[]
    for s,g in d.groupby("set"):
        md=pd.DataFrame([row_flags(str(x).lower()) for x in g.oracle_text.fillna("")])
        row={"set":s}
        for c in md.columns:row[c+"_share"]=float(md[c].mean())
        rows.append(row)
    return pd.DataFrame(rows)

def fit_predict(train,test,features):
    m=make_pipeline(StandardScaler(),Ridge(alpha=10))
    m.fit(train[features],train.turns)
    return m.predict(test[features])

def loo_base_residuals(train):
    rr=[]
    for i in train.index:
        tr=train.drop(index=i);te=train.loc[[i]]
        p=float(fit_predict(tr,te,BASE+["year_num"])[0])
        rr.append({"set":te.set.iloc[0],"resid":float(te.turns.iloc[0])-p})
    return pd.DataFrame(rr)

def life_correction(train,test,alpha=100):
    # Constrained, heavily shrunk correction: more repeatable lifegain can only lengthen games.
    rr=loo_base_residuals(train).merge(train[["set","m_lifegain_engine_share"]],on="set")
    sc=StandardScaler().fit(rr[["m_lifegain_engine_share"]])
    m=Ridge(alpha=alpha,positive=True).fit(sc.transform(rr[["m_lifegain_engine_share"]]),rr.resid)
    return m.predict(sc.transform(test[["m_lifegain_engine_share"]]))

def main(dev_csv,no_mh3_json,out):
    dev=pd.read_csv(dev_csv)
    if "FIN" in set(dev["set"].str.upper()): raise SystemExit("FIN contamination")
    rep=json.load(open(no_mh3_json))
    folds=rep["loso"]["RIDGE"]["folds"]
    targets={x["set"]:float(x["actual"]) for x in folds}
    if "FIN" in targets or "MH3" in targets or len(targets)!=21:raise SystemExit("target guard")
    # Recreate historical base features identically from the prior validated report.
    old=json.load(open(no_mh3_json))
    # The artifact does not store feature table; aggregate from dev.
    hist=[]
    dd=dev[(dev["set"]!="MH3") & dev["rarity_ord"].isin([0,1]) & dev["type_land"].eq(0)].copy()
    for s,g in dd.groupby("set"):
        cr=g[g.type_creature.eq(1)]
        hist.append({"set":s,"start_date":pd.to_datetime(g.window_start.iloc[0]),"year_num":(pd.to_datetime(g.window_start.iloc[0])-ORIGIN).days/365.25,
          "mean_mv":float(g.mv.mean()),"cheap_creature_share":float((cr.mv<=2).mean()),"cheap_interaction_share":float(g.cheap_interaction.mean()),
          "card_advantage_share":float(g.card_advantage.mean()),"evasion_share":float(g.evasion.mean()),"turns":targets[s]})
    hist=pd.DataFrame(hist).merge(hist_mechanics(dev),on="set").merge(hist_progress_pairmax(dev),on="set")
    ext=pd.DataFrame([external_features(s) for s in EXT_TARGETS])
    ext["actual"]=ext.set.map(EXT_TARGETS)

    pred_base=fit_predict(hist,ext,BASE)
    pred_year=fit_predict(hist,ext,BASE+["year_num"])
    pred_life=pred_year+life_correction(hist,ext,alpha=100)
    rows=[]
    for i,r in ext.iterrows():
        rows.append({"set":r["set"],"actual":r["actual"],"base5":float(pred_base[i]),"base5_progress":float(pred_progress[i]),"base5_progress_race":float(pred_progress_race[i]),"base5_year":float(pred_year[i]),"base5_year_lifegain":float(pred_life[i])})
    outp=Path(out);outp.mkdir(parents=True,exist_ok=True)
    pd.DataFrame(rows).to_csv(outp/"external_speed_predictions.csv",index=False)
    metrics={}
    for k in ["base5","base5_progress","base5_progress_race","base5_year","base5_year_lifegain"]:
        metrics[k]={"mae":float(np.mean([abs(x[k]-x["actual"]) for x in rows]))}
    report={"fin_used":False,"mh3_used":False,"external_targets":EXT_TARGETS,"rows":rows,"metrics":metrics,
            "external_features":ext.to_dict("records")}
    (outp/"external_speed_validation.json").write_text(json.dumps(report,indent=2,default=str))
    print("SUMMARY",json.dumps(report,default=str))
if __name__=="__main__":main(sys.argv[1],sys.argv[2],sys.argv[3])
