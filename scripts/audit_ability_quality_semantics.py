#!/usr/bin/env python3
"""FIN-blind OOF residual audit for ability-quality semantic candidates.

This is an audit only: it does not alter production features or touch FIN.
Source edits use real newlines; do not encode source newlines as literal backslash-n sequences.
"""
import argparse, json, re
import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
from sklearn.ensemble import ExtraTreesRegressor
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import Ridge

DROP={"set","name","oracle_text","type_line","gih_games","gih_wins","actual_gih","gih_wr_pct","window_start","window_end","collector_number"}
PATS={
 "immediate_removal":r"when .* enters.*(destroy|exile|deals? .* damage)|enters.*(destroy|exile|deals? .* damage)",
 "immediate_bounce":r"when .* enters.*return target .* to (its|their) owner's hand|enters.*return target .* to (its|their) owner's hand",
 "etb_token_value":r"when .* enters.*create .* token|enters.*create .* token",
 "etb_card_value":r"when .* enters.*draw .* card|enters.*draw .* card",
 "death_value":r"when .* dies|whenever .* dies|when .* leaves the battlefield|whenever .* leaves the battlefield",
 "protection_resilience":r"hexproof|indestructible|ward|can't be blocked|can't be the target|regenerate",
 "repeatable_card_value":r"whenever .* draw|whenever .* create .* token|at the beginning of .* draw|at the beginning of .* create .* token",
 "self_contained_value":r"enters.*(draw|create|destroy|exile|return target|deals? .* damage)|when .* enters.*(draw|create|destroy|exile|return target|deals? .* damage)",
 "broad_removal":r"destroy target (creature|permanent)|exile target (creature|permanent)|deals? .* damage to any target|any target",
 "external_dependency":r"another .* you control|creature type|shares? a creature type|if you control|for each .* you control",
 "cost_reduction":r"costs? .* less to cast|rather than pay|without paying .* mana cost",
 "graveyard_value":r"from your graveyard|flashback|escape|unearth|descend|delirium",
 "modal_flexibility":r"choose (one|two|three)|choose one or more|choose two|•",
 "mana_sink_repeatable":r"{[2-9x]}.*:|pay [2-9x].*:",
}

def main():
 ap=argparse.ArgumentParser(); ap.add_argument("--input",required=True); ap.add_argument("--out",required=True); a=ap.parse_args()
 d=pd.read_csv(a.input); d["set"]=d["set"].str.upper()
 if "FIN" in set(d["set"]): raise SystemExit("FIN contamination")
 nums=[c for c in d.columns if c not in DROP and not c.startswith("color_") and pd.api.types.is_numeric_dtype(d[c])]
 txt=d.oracle_text.fillna("").str.lower(); full=d.oracle_text.fillna("")+" TYPE "+d.type_line.fillna(""); pred=np.full(len(d),np.nan)
 for hold in sorted(d["set"].unique()):
  tr=d.set!=hold; te=~tr; y=d.loc[tr,"actual_gih"]
  m=make_pipeline(SimpleImputer(strategy="median"),ExtraTreesRegressor(n_estimators=600,min_samples_leaf=8,max_features=.6,n_jobs=-1,random_state=20260922)); m.fit(d.loc[tr,nums],y); pt=m.predict(d.loc[te,nums])
  t=make_pipeline(TfidfVectorizer(ngram_range=(1,2),min_df=3,max_features=12000,sublinear_tf=True),Ridge(alpha=10)); t.fit(full[tr],y); px=t.predict(full[te])
  raw=.7*pt+.3*px; c=float(y.mean()); pred[te]=c+1.25*(raw-c)
 d["resid_pp"]=(d.actual_gih-pred)*100
 lo=d.actual_gih.quantile(.10); hi=d.actual_gih.quantile(.90)
 out={}
 for name,pat in PATS.items():
  mask=txt.str.contains(pat,regex=True); z=d[mask]; base=d[~mask]
  out[name]={"n":int(mask.sum()),"mean_resid_pp":float(z.resid_pp.mean()) if len(z) else None,"mae_pp":float(z.resid_pp.abs().mean()) if len(z) else None,"resid_gap_vs_others_pp":float(z.resid_pp.mean()-base.resid_pp.mean()) if len(z) and len(base) else None,"top10_rate":float((z.actual_gih>=hi).mean()) if len(z) else None,"bottom10_rate":float((z.actual_gih<=lo).mean()) if len(z) else None}
 result={"fin_used":False,"n":int(len(d)),"candidates":out}
 with open(a.out,"w") as fh: json.dump(result,fh,indent=2)
 print(json.dumps(result,indent=2))
if __name__=="__main__": main()
