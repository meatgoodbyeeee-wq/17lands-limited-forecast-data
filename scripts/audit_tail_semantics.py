#!/usr/bin/env python3
"""FIN-blind residual/tail feature audit for targeted feature engineering."""
import argparse,json,re
import numpy as np,pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
from sklearn.ensemble import ExtraTreesRegressor
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import Ridge
DROP={"set","name","oracle_text","type_line","gih_games","gih_wins","actual_gih","gih_wr_pct","window_start","window_end","collector_number"}
PATS={
"modal":r"choose (one|two|three)|•","etb":r"enters( the battlefield)?|when .* enters","cast_trigger":r"when you cast|whenever you cast",
"repeatable":r"^[^:]{0,80}:|{t}:","mana_sink":r"{[2-9x]}.*:|pay [2-9x]","two_for_one":r"create .* token|draw .* card|return .* from your graveyard",
"recursion":r"from your graveyard|return .* graveyard|flashback|escape|unearth","conditional":r"\bif\b|\bunless\b|only if|as long as",
"downside":r"sacrifice|discard|lose [0-9x]+ life|deals .* damage to you","flexible_target":r"any target|target (creature or planeswalker|permanent|nonland permanent)",
"once_each_turn":r"once each turn|only once each turn","another":r"another .* you control","tribal":r"creature type|shares? a creature type"
}
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--input",required=True);ap.add_argument("--out",required=True);a=ap.parse_args()
 d=pd.read_csv(a.input);d["set"]=d["set"].str.upper()
 if "FIN" in set(d["set"]):raise SystemExit("FIN contamination")
 nums=[c for c in d.columns if c not in DROP and not c.startswith("color_") and pd.api.types.is_numeric_dtype(d[c])]
 txt=d.oracle_text.fillna("").str.lower(); full=d.oracle_text.fillna("")+" TYPE "+d.type_line.fillna("");pred=np.full(len(d),np.nan)
 for hold in sorted(d["set"].unique()):
  tr=d.set!=hold;te=~tr;y=d.loc[tr,"actual_gih"]
  m=make_pipeline(SimpleImputer(strategy="median"),ExtraTreesRegressor(n_estimators=600,min_samples_leaf=8,max_features=.6,n_jobs=-1,random_state=20260922));m.fit(d.loc[tr,nums],y);pt=m.predict(d.loc[te,nums])
  t=make_pipeline(TfidfVectorizer(ngram_range=(1,2),min_df=3,max_features=12000,sublinear_tf=True),Ridge(alpha=10));t.fit(full[tr],y);px=t.predict(full[te])
  raw=.7*pt+.3*px;c=float(y.mean());pred[te]=c+1.25*(raw-c)
 d["resid_pp"]=(d.actual_gih-pred)*100
 out={}
 for name,pat in PATS.items():
  mask=txt.str.contains(pat,regex=True)
  z=d[mask];base=d[~mask]
  out[name]={"n":int(mask.sum()),"mean_resid_pp":float(z.resid_pp.mean()) if len(z) else None,"mae_pp":float(z.resid_pp.abs().mean()) if len(z) else None,"resid_gap_vs_others_pp":float(z.resid_pp.mean()-base.resid_pp.mean()) if len(z) and len(base) else None}
 open(a.out,"w").write(json.dumps({"fin_used":False,"features":out},indent=2));print(json.dumps({"fin_used":False,"features":out},indent=2))
if __name__=="__main__":main()
