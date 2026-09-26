#!/usr/bin/env python3
"""Research-only 21-set LOSO audit: excludes FIN and MH3."""
import argparse, json, re
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
from sklearn.ensemble import ExtraTreesRegressor
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import Ridge

DROP={"set","name","oracle_text","type_line","gih_games","gih_wins","actual_gih","gih_wr_pct","window_start","window_end","collector_number"}
PATS={
 "additional_cost":r"as an additional cost|additional cost to cast|sacrifice .*:|discard .*:",
 "narrow_target":r"target (attacking|blocking|tapped|nonblack|nonartifact|creature with (power|toughness|mana value))",
 "self_contained_value":r"(when|whenever) .* enters|enters( the battlefield)?.*(draw|create|destroy|exile|return)|draw (two|three|x|that many) cards",
 "broad_removal":r"(destroy|exile) target (creature|permanent|nonland permanent)|any target",
 "repeatable_engine":r"once each turn|whenever .* (dies|enters|attacks|casts?)|{t}:",
 "dependency":r"another .* you control|creature type|shares? a creature type|if you control|for each .* you control",
}
def metrics(y,p):
    n=len(y); k=max(1,int(np.ceil(n*.10)))
    ay=np.argsort(y); ap=np.argsort(p)
    top=set(ay[-k:]); bot=set(ay[:k]); ptop=set(ap[-k:])
    return {
      "n":int(n),"mae_pp":float(np.mean(np.abs(y-p))*100),
      "spearman":float(spearmanr(y,p).statistic),
      "top10_capture":float(len(top & ptop)/k),
      "actual_top10_mae_pp":float(np.mean(np.abs((p-y)[list(top)]))*100),
      "actual_top10_bias_pred_minus_actual_pp":float(np.mean((p-y)[list(top)])*100),
      "actual_bottom10_mae_pp":float(np.mean(np.abs((p-y)[list(bot)]))*100),
      "actual_bottom10_bias_pred_minus_actual_pp":float(np.mean((p-y)[list(bot)])*100),
    }
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--input",required=True); ap.add_argument("--out",required=True); a=ap.parse_args()
    d=pd.read_csv(a.input); d["set"]=d["set"].str.upper()
    sets=set(d["set"])
    if "FIN" in sets or "MH3" in sets: raise SystemExit("FIN/MH3 contamination")
    if len(sets)!=21: raise SystemExit(f"Expected 21 sets, got {len(sets)}: {sorted(sets)}")
    nums=[c for c in d.columns if c not in DROP and not c.startswith("color_") and pd.api.types.is_numeric_dtype(d[c])]
    full=d.oracle_text.fillna("")+" TYPE "+d.type_line.fillna("")
    pred=np.full(len(d),np.nan); folds={}
    for hold in sorted(sets):
        tr=d["set"]!=hold; te=~tr; y=d.loc[tr,"actual_gih"]
        tree=make_pipeline(SimpleImputer(strategy="median"),ExtraTreesRegressor(n_estimators=600,min_samples_leaf=8,max_features=.6,n_jobs=-1,random_state=20260922))
        tree.fit(d.loc[tr,nums],y); pt=tree.predict(d.loc[te,nums])
        text=make_pipeline(TfidfVectorizer(ngram_range=(1,2),min_df=3,max_features=12000,sublinear_tf=True),Ridge(alpha=10))
        text.fit(full[tr],y); px=text.predict(full[te])
        raw=.7*pt+.3*px; center=float(y.mean()); ph=center+1.25*(raw-center)
        pred[te]=ph; folds[hold]=metrics(d.loc[te,"actual_gih"].to_numpy(),ph)
    d["pred"]=pred; d["resid_pp"]=(d["actual_gih"]-pred)*100
    groups={}
    tl=d.oracle_text.fillna("").str.lower()
    for name,pat in PATS.items():
        m=tl.str.contains(pat,regex=True)
        groups[name]={"n":int(m.sum()),"mean_resid_actual_minus_pred_pp":float(d.loc[m,"resid_pp"].mean()),"mae_pp":float(d.loc[m,"resid_pp"].abs().mean()),"gap_vs_others_pp":float(d.loc[m,"resid_pp"].mean()-d.loc[~m,"resid_pp"].mean())}
    out={"fin_used":False,"mh3_used":False,"sets":sorted(sets),"overall":metrics(d.actual_gih.to_numpy(),pred),"folds":folds,"candidate_residual_groups":groups}
    open(a.out,"w").write(json.dumps(out,indent=2)); print(json.dumps(out,indent=2))
if __name__=="__main__": main()
