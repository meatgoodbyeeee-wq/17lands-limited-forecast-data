#!/usr/bin/env python3
"""Research-only 21-set GIH WR LOSO (Premier Draft). FIN and MH3 are excluded.

Baseline = currently adopted model, identical to scripts/audit_gih_21set.py:
  ExtraTrees(600, leaf 8, max_features 0.6) 70% + word TF-IDF/Ridge(alpha 10) 30%,
  fixed decompression center + 1.25*(raw-center), center = training-fold mean.

Modes
  oof      : baseline out-of-fold predictions per card + residual audit tables
  compare  : baseline vs candidate feature sets (same folds, same seeds)

Nothing here touches the Pages repo or production predictions.
"""
import argparse, json, re, sys
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
from sklearn.ensemble import ExtraTreesRegressor
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import Ridge

RESEARCH_SETS = {"KHM","STX","AFR","MID","VOW","NEO","SNC","DMU","BRO","ONE","MOM",
                 "LTR","WOE","LCI","MKM","OTJ","BLB","DSK","FDN","DFT","TDM"}
FORBIDDEN = {"FIN", "MH3"}
DROP = {"set","name","oracle_text","type_line","gih_games","gih_wins","actual_gih","gih_wr_pct",
        "window_start","window_end","collector_number"}
SEED = 20260922


def load(path):
    d = pd.read_csv(path)
    d["set"] = d["set"].str.upper()
    d = d[~d["set"].isin(FORBIDDEN)].reset_index(drop=True)   # MH3 may be present in the stored 22-set table
    sets = set(d["set"])
    if sets & FORBIDDEN:
        raise SystemExit("FIN/MH3 contamination")
    if sets != RESEARCH_SETS:
        raise SystemExit(f"Expected the 21 research sets, got {sorted(sets)}")
    # The original 21-set audit kept the MH3 metadata columns (constant for these sets) in
    # its feature list; keep them so ExtraTrees feature sampling matches that run exactly.
    return d


def numeric_cols(d, extra_drop=()):
    return [c for c in d.columns if c not in DROP and c not in extra_drop and not c.startswith("color_")
            and pd.api.types.is_numeric_dtype(d[c])]


def loso(d, nums, text_col="__text"):
    pred = np.full(len(d), np.nan)
    for hold in sorted(set(d["set"])):
        tr = (d["set"] != hold).to_numpy(); te = ~tr
        y = d.loc[tr, "actual_gih"]
        tree = make_pipeline(SimpleImputer(strategy="median"),
                             ExtraTreesRegressor(n_estimators=600, min_samples_leaf=8, max_features=.6,
                                                 n_jobs=-1, random_state=SEED))
        tree.fit(d.loc[tr, nums], y); pt = tree.predict(d.loc[te, nums])
        text = make_pipeline(TfidfVectorizer(ngram_range=(1,2), min_df=3, max_features=12000, sublinear_tf=True),
                             Ridge(alpha=10))
        text.fit(d.loc[tr, text_col], y); px = text.predict(d.loc[te, text_col])
        raw = .7*pt + .3*px; center = float(y.mean())
        pred[te] = center + 1.25*(raw - center)
    return pred


def pooled_metrics(y, p):
    """Same definition as audit_gih_21set.metrics (pooled over all cards)."""
    n = len(y); k = max(1, int(np.ceil(n*.10)))
    ay = np.argsort(y); ap = np.argsort(p)
    top = set(ay[-k:]); bot = set(ay[:k]); ptop = set(ap[-k:])
    return {"n": int(n), "mae_pp": float(np.mean(np.abs(y-p))*100),
            "spearman": float(spearmanr(y, p).statistic),
            "top10_capture": float(len(top & ptop)/k),
            "actual_top10_mae_pp": float(np.mean(np.abs((p-y)[list(top)]))*100),
            "actual_top10_bias_pred_minus_actual_pp": float(np.mean((p-y)[list(top)])*100),
            "actual_bottom10_mae_pp": float(np.mean(np.abs((p-y)[list(bot)]))*100),
            "actual_bottom10_bias_pred_minus_actual_pp": float(np.mean((p-y)[list(bot)])*100)}


def within_set(d, p):
    """Handoff metrics computed inside each set, then averaged over sets (equal weight)."""
    rows = []
    for s, g in d.assign(_p=p).groupby("set"):
        y = g["actual_gih"].to_numpy(); q = g["_p"].to_numpy(); n = len(y)
        k = max(1, int(np.ceil(n*.10)))
        ay = np.argsort(y); aq = np.argsort(q)
        top, bot = ay[-k:], ay[:k]
        rows.append({"set": s, "n": n, "mae_pp": np.mean(np.abs(y-q))*100,
                     "spearman": spearmanr(y, q).statistic,
                     "bias_pp": np.mean(q-y)*100,
                     "sd_ratio": np.std(q)/np.std(y),
                     "top10_bias_pp": np.mean((q-y)[top])*100,
                     "bottom10_bias_pp": np.mean((q-y)[bot])*100,
                     "top10_mae_pp": np.mean(np.abs(q-y)[top])*100,
                     "bottom10_mae_pp": np.mean(np.abs(q-y)[bot])*100,
                     "strong_recall": len(set(top) & set(aq[-k:]))/k,
                     "weak_recall": len(set(bot) & set(aq[:k]))/k})
    f = pd.DataFrame(rows)
    summary = {c: float(f[c].mean()) for c in f.columns if c not in ("set","n")}
    return summary, f


def text_of(d):
    return d["oracle_text"].fillna("") + " TYPE " + d["type_line"].fillna("")


def residual_tables(d):
    r = d["resid_pp"]; out = {}
    def grp(name, key):
        g = d.groupby(key)["resid_pp"].agg(["count","mean",lambda x: x.abs().mean()])
        g.columns = ["n","mean_resid_actual_minus_pred_pp","mae_pp"]
        out[name] = g.reset_index().to_dict(orient="records")
    rarity = d["rarity_ord"].map({0:"common",1:"uncommon",2:"rare",3:"mythic"}).fillna("other")
    grp("by_rarity", rarity)
    t = np.select([d["type_creature"]==1, d["type_instant"]==1, d["type_sorcery"]==1,
                   d["type_enchantment"]==1, d["type_artifact"]==1, d["type_land"]==1],
                  ["creature","instant","sorcery","enchantment","artifact","land"], "other")
    grp("by_type", pd.Series(t, index=d.index))
    grp("by_mv", pd.cut(d["mv"], [-1,1,2,3,4,5,99], labels=["<=1","2","3","4","5","6+"]).astype(str))
    grp("by_n_colors", d["n_colors"].clip(upper=3))
    grp("by_actual_decile_within_set", d.groupby("set")["actual_gih"].rank(pct=True).mul(10).clip(upper=9.999).astype(int))
    grp("by_pred_decile_within_set", d.groupby("set")["pred"].rank(pct=True).mul(10).clip(upper=9.999).astype(int))
    grp("by_set", d["set"])
    flags = [c for c in d.columns if (c.startswith("kw_") or c.startswith("semantic_") or c.startswith("quality_")
             or c in ("interaction","cheap_interaction","clean_interaction","card_advantage","evasion",
                      "has_etb","is_aura","is_equipment","is_vehicle","has_x_cost","is_multicolor"))]
    frows = []
    for c in flags:
        m = d[c].fillna(0) > 0
        if m.sum() < 30: continue
        frows.append({"feature": c, "n": int(m.sum()),
                      "mean_resid_pp": float(r[m].mean()), "mean_resid_others_pp": float(r[~m].mean()),
                      "gap_pp": float(r[m].mean()-r[~m].mean()), "mae_pp": float(r[m].abs().mean()),
                      "sets_with_positive_mean": int((d[m].groupby("set")["resid_pp"].mean() > 0).sum()),
                      "sets_present": int(d[m]["set"].nunique())})
    out["binary_feature_gaps"] = sorted(frows, key=lambda x: -abs(x["gap_pp"]))
    return out


def cmd_oof(a):
    d = load(a.features); d["__text"] = text_of(d)
    nums = numeric_cols(d)
    p = loso(d, nums)
    d["pred"] = p; d["resid_pp"] = (d["actual_gih"]-p)*100
    ws, fs = within_set(d, p)
    out = {"fin_used": False, "mh3_used": False, "sets": sorted(set(d["set"])), "n_features": len(nums),
           "features": nums, "pooled": pooled_metrics(d["actual_gih"].to_numpy(), p),
           "within_set_mean": ws, "per_set": fs.to_dict(orient="records"),
           "residuals": residual_tables(d),
           "versions": {"sklearn": __import__("sklearn").__version__, "pandas": pd.__version__,
                        "numpy": np.__version__}}
    a.out_dir.mkdir(parents=True, exist_ok=True)
    (a.out_dir/"baseline_metrics.json").write_text(json.dumps(out, indent=2, default=float))
    cols = ["set","name","rarity_ord","mv","type_line","oracle_text","gih_games","actual_gih","pred","resid_pp"]
    d[cols].to_csv(a.out_dir/"baseline_oof.csv.gz", index=False, compression="gzip")
    print(json.dumps({k: out[k] for k in ("pooled","within_set_mean","n_features")}, indent=2))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    o = sub.add_parser("oof"); o.add_argument("--features", required=True); o.add_argument("--out-dir", type=Path, required=True)
    a = ap.parse_args()
    {"oof": cmd_oof}[a.cmd](a)


if __name__ == "__main__":
    main()
