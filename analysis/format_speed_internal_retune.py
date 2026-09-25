#!/usr/bin/env python3
import sys,json
from pathlib import Path
import numpy as np,pandas as pd
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
sys.path.insert(0,"analysis")
import format_speed_mechanism_effects as fm

BASE=fm.BASE

# IMPORTANT: this script uses only the 21 development sets returned by fm.hist_table().
# It never loads TMT/SOS/MSH/HOB or any external-holdout result.
def add_candidates(df):
    z=df.copy()
    # Separate "amount", "concentration in one archetype", and "enabler x payoff".
    z["life_amount_global"]=z["race_buffer_mean"]
    z["life_amount_pair"]=z["race_buffer_pairmax"]
    z["life_concentration"]=z["race_buffer_pairmax"]-z["race_buffer_mean"]
    z["life_synergy"]=z["lifegain_synergy_pairmax"]

    # Compact composites: one scalar per hypothesis, so we do not spend degrees of freedom
    # on 3 separate lifegain columns in a 21-set sample.
    z["life_effect_balanced"]=z["race_buffer_mean"] + z["lifegain_synergy_pairmax"]
    z["life_effect_pair"]=z["race_buffer_pairmax"] + z["lifegain_synergy_pairmax"]
    z["life_effect_synergy_heavy"]=z["race_buffer_pairmax"] + 2.0*z["lifegain_synergy_pairmax"]

    # Persistent value is split into broad density vs archetype concentration.
    z["engine_global"]=z["engine_mean"]
    z["engine_pair"]=z["engine_pairmax"]
    z["engine_concentration"]=z["engine_pairmax"]-z["engine_mean"]

    # Delayed-resource effects are kept compact.
    z["resource_global"]=z["delay_mean"]+z["recur_mean"]+0.5*z["mana_dev_mean"]
    z["resource_pair"]=z["delay_pairmax"]+z["recur_pairmax"]+0.5*z["mana_dev_pairmax"]

    # A slow-game balance index. Pressure enters negatively.
    z["slow_balance_global"]=z["engine_mean"]+z["race_buffer_mean"]+z["delay_mean"]+z["recur_mean"]+0.5*z["mana_dev_mean"]-z["pressure_mean"]
    z["slow_balance_pair"]=z["engine_pairmax"]+z["race_buffer_pairmax"]+z["delay_pairmax"]+z["recur_pairmax"]+0.5*z["mana_dev_pairmax"]-z["pressure_pairmax"]
    return z

CANDIDATES={
 "BASE":[],
 "LIFE_AMOUNT_GLOBAL":["life_amount_global"],
 "LIFE_AMOUNT_PAIR":["life_amount_pair"],
 "LIFE_CONCENTRATION":["life_concentration"],
 "LIFE_SYNERGY":["life_synergy"],
 "LIFE_BALANCED":["life_effect_balanced"],
 "LIFE_PAIR":["life_effect_pair"],
 "LIFE_SYNERGY_HEAVY":["life_effect_synergy_heavy"],
 "ENGINE_GLOBAL":["engine_global"],
 "ENGINE_PAIR":["engine_pair"],
 "ENGINE_CONCENTRATION":["engine_concentration"],
 "RESOURCE_GLOBAL":["resource_global"],
 "RESOURCE_PAIR":["resource_pair"],
 "SLOW_BALANCE_GLOBAL":["slow_balance_global"],
 "SLOW_BALANCE_PAIR":["slow_balance_pair"],
}

def feats(name): return BASE+CANDIDATES[name]

def predict(train,test,name):
    m=make_pipeline(StandardScaler(),Ridge(alpha=10.0))
    m.fit(train[feats(name)],train.turns)
    return m.predict(test[feats(name)])

def loo_mae(df,name):
    e=[]
    for s in df.set:
        tr=df[df.set.ne(s)]; te=df[df.set.eq(s)]
        e.append(abs(float(te.turns.iloc[0])-float(predict(tr,te,name)[0])))
    return float(np.mean(e))

def nested_loso(df):
    rows=[]
    for hold in df.set:
        tr=df[df.set.ne(hold)].copy(); te=df[df.set.eq(hold)]
        scores={n:loo_mae(tr,n) for n in CANDIDATES}
        choice=min(scores,key=scores.get)
        p=float(predict(tr,te,choice)[0]); y=float(te.turns.iloc[0])
        rows.append({"set":hold,"actual":y,"pred":p,"abs_err":abs(y-p),"selected":choice,"inner_scores":scores})
    return rows

def forward_fixed(df,name,min_train=8):
    d=df.sort_values("start_date").reset_index(drop=True); rows=[]
    for i in range(min_train,len(d)):
        tr=d.iloc[:i];te=d.iloc[[i]]
        p=float(predict(tr,te,name)[0]); y=float(te.turns.iloc[0])
        rows.append({"set":te.set.iloc[0],"actual":y,"pred":p,"abs_err":abs(y-p)})
    return rows

def forward_nested(df,min_train=8):
    # At each historical point choose the variable definition using only earlier sets.
    d=df.sort_values("start_date").reset_index(drop=True); rows=[]
    for i in range(min_train,len(d)):
        tr=d.iloc[:i].copy();te=d.iloc[[i]]
        scores={n:loo_mae(tr,n) for n in CANDIDATES}
        choice=min(scores,key=scores.get)
        p=float(predict(tr,te,choice)[0]);y=float(te.turns.iloc[0])
        rows.append({"set":te.set.iloc[0],"actual":y,"pred":p,"abs_err":abs(y-p),"selected":choice,"inner_scores":scores})
    return rows

def main(dev_csv,fra_gz,outdir):
    out=Path(outdir);out.mkdir(parents=True,exist_ok=True)
    df=add_candidates(fm.hist_table(dev_csv))
    fra=add_candidates(pd.DataFrame([fm.fra_table(fra_gz)])).iloc[0].to_dict()
    if len(df)!=21 or "MH3" in set(df.set) or "FIN" in set(df.set):
        raise SystemExit("21-set guard failed")

    fixed_cv={n:loo_mae(df,n) for n in CANDIDATES}
    fixed_forward={}
    for n in CANDIDATES:
        rr=forward_fixed(df,n)
        fixed_forward[n]=float(np.mean([x["abs_err"] for x in rr]))

    outer=nested_loso(df)
    outer_mae=float(np.mean([x["abs_err"] for x in outer]))
    outer_counts={n:sum(x["selected"]==n for x in outer) for n in CANDIDATES}

    wf=forward_nested(df)
    wf_mae=float(np.mean([x["abs_err"] for x in wf]))
    wf_counts={n:sum(x["selected"]==n for x in wf) for n in CANDIDATES}

    # A final deployable family must improve BOTH fixed LOSO and fixed walk-forward vs BASE.
    eligible=[n for n in CANDIDATES if fixed_cv[n] < fixed_cv["BASE"] and fixed_forward[n] < fixed_forward["BASE"]]
    chosen=min(eligible,key=lambda n:(fixed_cv[n]+fixed_forward[n])) if eligible else "BASE"

    train=df.copy()
    test=pd.DataFrame([fra])
    model=make_pipeline(StandardScaler(),Ridge(alpha=10.0))
    model.fit(train[feats(chosen)],train.turns)
    fra_pred=float(model.predict(test[feats(chosen)])[0])

    # Error intervals from fixed chosen family only.
    errs=[]
    for s in df.set:
        tr=df[df.set.ne(s)];te=df[df.set.eq(s)]
        errs.append(float(te.turns.iloc[0])-float(predict(tr,te,chosen)[0]))
    ae=np.abs(errs)

    # Stability: coefficients sign in standardized model across LOSO folds.
    coef=[]
    if chosen!="BASE":
        for s in df.set:
            tr=df[df.set.ne(s)]
            m=make_pipeline(StandardScaler(),Ridge(alpha=10.0));m.fit(tr[feats(chosen)],tr.turns)
            coef.append(float(m.named_steps["ridge"].coef_[-1]))

    report={
      "external_holdouts_loaded":False,
      "fin_used":False,"mh3_used":False,"n_sets":21,
      "candidates":CANDIDATES,
      "fixed_loso_mae":fixed_cv,
      "fixed_forward_mae":fixed_forward,
      "nested_loso":{"mae":outer_mae,"selection_counts":outer_counts,"folds":outer},
      "nested_forward":{"mae":wf_mae,"selection_counts":wf_counts,"folds":wf},
      "eligible_both_improve":eligible,
      "chosen":chosen,
      "chosen_extra_coefficient_signs":{"positive":sum(x>0 for x in coef),"negative":sum(x<0 for x in coef),"median":float(np.median(coef)) if coef else None},
      "fra_pred_turns":fra_pred,
      "fra_candidate_features":{k:fra[k] for k in set(sum(CANDIDATES.values(),[]))},
      "interval80":float(np.quantile(ae,.8,method="higher")),
      "interval90":float(np.quantile(ae,.9,method="higher"))
    }
    (out/"format_speed_internal_retune.json").write_text(json.dumps(report,indent=2,default=str),encoding="utf-8")
    df.to_csv(out/"format_speed_internal_retune_features.csv",index=False)
    print("SUMMARY",json.dumps({
      "fixed_loso_mae":fixed_cv,"fixed_forward_mae":fixed_forward,
      "nested_loso_mae":outer_mae,"nested_loso_counts":outer_counts,
      "nested_forward_mae":wf_mae,"nested_forward_counts":wf_counts,
      "eligible":eligible,"chosen":chosen,"coef_signs":report["chosen_extra_coefficient_signs"],
      "fra_pred":fra_pred,"interval80":report["interval80"],"interval90":report["interval90"],
      "fra_candidate_features":report["fra_candidate_features"]
    },ensure_ascii=False))
if __name__=="__main__":main(sys.argv[1],sys.argv[2],sys.argv[3])
