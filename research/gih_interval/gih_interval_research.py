#!/usr/bin/env python3
"""Compare GIH WR forecast-range methods by leave-one-set-out (see PLAN.md).

Inputs are frozen files already in this repository; nothing is downloaded.
FIN and MH3 are refused. Point predictions are not changed.
"""
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import ExtraTreesRegressor
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
OOF = ROOT / "research/gih_21set/baseline/baseline_oof.csv.gz"
FEAT = ROOT / "data/features/dev_feature_22.csv.gz"
TARGET = 0.80
ALPHA = 1 - TARGET
LEGACY_RADIUS = 3.684267349645218
SHRINK_K = 50
SIGMA_FLOOR = 0.5
SEED = 20260922
RARITY = {0: "common", 1: "uncommon", 2: "rare", 3: "mythic"}
TYPES = ["creature", "spell", "other_permanent", "land"]
DROP = {"set", "name", "oracle_text", "type_line", "gih_games", "gih_wins", "actual_gih", "gih_wr_pct",
        "window_start", "window_end", "collector_number"}


def type_group(type_line: str) -> str:
    t = (type_line or "").lower()
    if "creature" in t:
        return "creature"
    if "land" in t:
        return "land"
    if "instant" in t or "sorcery" in t:
        return "spell"
    return "other_permanent"


def conformal_q(scores: np.ndarray, level: float = TARGET) -> float:
    n = len(scores)
    return float(np.quantile(scores, min(1.0, math.ceil((n + 1) * level) / n), method="higher"))


def load() -> tuple[pd.DataFrame, list[str]]:
    b = pd.read_csv(OOF)
    f = pd.read_csv(FEAT)
    bad = {"FIN", "MH3"} & set(b["set"].str.upper())
    if bad:
        raise SystemExit(f"refusing {sorted(bad)}")
    nums = [c for c in f.columns if c not in DROP and not c.startswith("color_") and pd.api.types.is_numeric_dtype(f[c])]
    nums = [c for c in nums if c not in {"rarity_ord", "mv", "is_supplemental_power_set", "is_premier_set"}]
    d = b.merge(f[["set", "name"] + nums], on=["set", "name"], how="left", validate="one_to_one")
    d["pred_pp"] = d["pred"] * 100
    d["actual_pp"] = d["actual_gih"] * 100
    d["r"] = d["actual_pp"] - d["pred_pp"]
    d["rarity"] = d["rarity_ord"].map(RARITY)
    d["type_group"] = d["type_line"].map(type_group)
    cols = ["pred_pp", "rarity_ord", "mv"] + nums
    return d, cols


# Each method: fit(train_df) -> params; apply(params, test_df) -> (lo, hi) arrays in pp.
def m0_fit(tr, cols):
    return None


def m0_apply(p, te, cols):
    return te.pred_pp - LEGACY_RADIUS, te.pred_pp + LEGACY_RADIUS


def m1_fit(tr, cols):
    return conformal_q(tr.r.abs().to_numpy())


def m1_apply(q, te, cols):
    return te.pred_pp - q, te.pred_pp + q


def rarity_q(tr):
    return {k: conformal_q(g.r.abs().to_numpy()) for k, g in tr.groupby("rarity")}


def m2_fit(tr, cols):
    return rarity_q(tr)


def m2_apply(q, te, cols):
    rad = te.rarity.map(q)
    return te.pred_pp - rad, te.pred_pp + rad


def m3_fit(tr, cols):
    return {k: (float(np.quantile(g.r, ALPHA / 2)), float(np.quantile(g.r, 1 - ALPHA / 2))) for k, g in tr.groupby("rarity")}


def m3_apply(q, te, cols):
    lo = te.rarity.map(lambda k: q[k][0])
    hi = te.rarity.map(lambda k: q[k][1])
    return te.pred_pp + lo, te.pred_pp + hi


def m4_fit(tr, cols):
    qr = rarity_q(tr)
    out = {}
    for (rar, typ), g in tr.groupby(["rarity", "type_group"]):
        n = len(g)
        out[(rar, typ)] = (n * conformal_q(g.r.abs().to_numpy()) + SHRINK_K * qr[rar]) / (n + SHRINK_K)
    return {"cell": out, "rarity": qr}


def m4_radius(p, te):
    return np.array([p["cell"].get((r, t), p["rarity"][r]) for r, t in zip(te.rarity, te.type_group)])


def m4_apply(p, te, cols):
    rad = m4_radius(p, te)
    return te.pred_pp - rad, te.pred_pp + rad


def sigma_model():
    return make_pipeline(SimpleImputer(strategy="median"),
                         ExtraTreesRegressor(n_estimators=300, min_samples_leaf=20, max_features=0.6,
                                             n_jobs=-1, random_state=SEED))


def m5_fit(tr, cols):
    sets = sorted(tr.set.unique())
    folds = [sets[i::5] for i in range(5)]
    sig = np.zeros(len(tr))
    for fs in folds:
        inner_te = tr.set.isin(fs).to_numpy()
        m = sigma_model().fit(tr.loc[~inner_te, cols], tr.r.abs()[~inner_te])
        sig[inner_te] = m.predict(tr.loc[inner_te, cols])
    sig = np.maximum(sig, SIGMA_FLOOR)
    q = conformal_q(tr.r.abs().to_numpy() / sig)
    full = sigma_model().fit(tr[cols], tr.r.abs())
    return {"q": q, "model": full}


def m5_apply(p, te, cols):
    rad = p["q"] * np.maximum(p["model"].predict(te[cols]), SIGMA_FLOOR)
    return te.pred_pp - rad, te.pred_pp + rad


METHODS = {
    "M0_current_fixed": (m0_fit, m0_apply),
    "M1_global": (m1_fit, m1_apply),
    "M2_rarity": (m2_fit, m2_apply),
    "M3_rarity_asym": (m3_fit, m3_apply),
    "M4_rarity_type": (m4_fit, m4_apply),
    "M5_normalized": (m5_fit, m5_apply),
}


def score(y, lo, hi):
    y, lo, hi = map(np.asarray, (y, lo, hi))
    cover = (y >= lo) & (y <= hi)
    width = hi - lo
    winkler = width + (2 / ALPHA) * (np.maximum(lo - y, 0) + np.maximum(y - hi, 0))
    return cover, width, winkler


def main():
    d, cols = load()
    rows = {}
    for name, (fit, apply) in METHODS.items():
        lo = np.zeros(len(d)); hi = np.zeros(len(d))
        for s in sorted(d.set.unique()):
            te = (d.set == s).to_numpy()
            p = fit(d.loc[~te], cols)
            l, h = apply(p, d.loc[te], cols)
            lo[te] = np.asarray(l); hi[te] = np.asarray(h)
        cover, width, wink = score(d.actual_pp, lo, hi)
        d[name + "_lo"] = lo; d[name + "_hi"] = hi
        by = lambda key: {k: round(float(cover[(d[key] == k).to_numpy()].mean()), 4) for k in d[key].unique()}
        per_set = pd.Series(cover).groupby(d.set.to_numpy()).mean()
        rows[name] = {
            "coverage": round(float(cover.mean()), 4),
            "coverage_by_rarity": {k: by("rarity")[k] for k in RARITY.values()},
            "coverage_by_type": {k: by("type_group")[k] for k in TYPES},
            "width_by_rarity": {k: round(float(width[(d.rarity == k).to_numpy()].mean()), 3) for k in RARITY.values()},
            "per_set_coverage_min_max": [round(float(per_set.min()), 4), round(float(per_set.max()), 4)],
            "mean_width": round(float(width.mean()), 4),
            "mean_interval_score": round(float(wink.mean()), 4),
        }
        print(name, json.dumps(rows[name]))

    # Pre-registered decision rule (PLAN.md)
    order = ["M1_global", "M2_rarity", "M3_rarity_asym", "M4_rarity_type", "M5_normalized"]
    for name in METHODS:
        m = rows[name]
        m["rule1_pooled"] = 0.78 <= m["coverage"] <= 0.82
        m["rule2_rarity"] = all(abs(v - TARGET) <= 0.05 for v in m["coverage_by_rarity"].values())
        m["rule3_type"] = all(abs(v - TARGET) <= 0.07 for v in m["coverage_by_type"].values())
    passing = [n for n in order if rows[n]["rule1_pooled"] and rows[n]["rule2_rarity"] and rows[n]["rule3_type"]]
    fallback = False
    if not passing:
        fallback = True
        passing = [n for n in order if rows[n]["rule1_pooled"] and rows[n]["rule2_rarity"]]
    winner = None
    for n in passing:  # simplest first; a more complex one must be >=1% better
        if winner is None or rows[n]["mean_interval_score"] <= 0.99 * rows[winner]["mean_interval_score"]:
            winner = n
    result = {"target": TARGET, "n_cards": int(len(d)), "sets": sorted(d.set.unique()), "fin_used": False, "mh3_used": False,
              "methods": rows, "passing": passing, "used_fallback_rule5": fallback, "winner": winner}
    (OUT / "compare.json").write_text(json.dumps(result, indent=2, ensure_ascii=False))
    keep = ["set", "name", "rarity", "type_group", "pred_pp", "actual_pp"] + [c for c in d.columns if c.endswith("_lo") or c.endswith("_hi")]
    d[keep].round(4).to_csv(OUT / "loso_ranges.csv.gz", index=False)
    print("PASSING", passing, "FALLBACK", fallback, "WINNER", winner)


if __name__ == "__main__":
    main()
