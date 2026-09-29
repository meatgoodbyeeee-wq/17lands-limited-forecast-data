#!/usr/bin/env python3
"""Production export of the confirmed final GIH candidate (research/fin_final, Rule F confirmed; adopted by the user 2026-09-29).

Model: the adopted GIH model unchanged (ET 70% + TF-IDF/Ridge 30%, x1.25 around the training mean), features baseline + C3,
trained on the 21 research sets + EOE, TLA, ECL, TMT, SOS, MSH, HOB. Seeds 20260922-24, averaged. FIN, MH3 and FRA outcomes are not used.

  python export_gih_c3_28set.py oof                                   # 28-set LOSO OOF (for the range) -> oof_28set.csv.gz, oof_metrics.json
  python export_gih_c3_28set.py adopted --fra <pages>/data/target.json.gz --out <pages>/data/adopted-gih-fra.json.gz
  python export_gih_c3_28set.py range --fra <pages>/data/target.json.gz --adopted <pages>/data/adopted-gih-fra.json.gz \
      --out <pages>/data/gih-range-fra.json                           # M5 (unchanged method) refit on the new OOF residuals
"""
import argparse
import gzip
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
for p in (ROOT / "scripts", ROOT / "research/gih_llm_extract", ROOT / "research/case6", ROOT / "research/gih_interval"):
    sys.path.insert(0, str(p))
import gih21_research as g  # noqa: E402
import c3_research as c3  # noqa: E402
import case6_research as c6  # noqa: E402
import gih_interval_research as gi  # noqa: E402
from build_dev_features import card_features  # noqa: E402
from sklearn.ensemble import ExtraTreesRegressor  # noqa: E402
from sklearn.feature_extraction.text import TfidfVectorizer  # noqa: E402
from sklearn.impute import SimpleImputer  # noqa: E402
from sklearn.linear_model import Ridge  # noqa: E402
from sklearn.pipeline import make_pipeline  # noqa: E402

VERSION = "gih-c3-28set-20260929"
RANGE_VERSION = "gih-range-m5-c3-28set-20260929"
SEEDS = c3.SEEDS
OOF = HERE / "oof_28set.csv.gz"
FORBIDDEN = {"FIN", "MH3", "FRA"}


def training():
    d, base, cols = c3.load_with_c3()
    n = c6.load_new(base, cols)
    pool = pd.concat([d, n], ignore_index=True)
    sets = set(pool["set"])
    if sets & FORBIDDEN or len(sets) != 28:
        raise SystemExit(f"unexpected training sets {sorted(sets)}")
    return pool, base, cols


def parts(train, test, nums, seed):
    """Same model as c3_research.fit_predict, returning the centre and both component predictions."""
    y = train["actual_gih"]
    tree = make_pipeline(SimpleImputer(strategy="median"),
                         ExtraTreesRegressor(n_estimators=600, min_samples_leaf=8, max_features=.6, n_jobs=-1, random_state=seed))
    tree.fit(train[nums], y)
    text = make_pipeline(TfidfVectorizer(ngram_range=(1, 2), min_df=3, max_features=12000, sublinear_tf=True), Ridge(alpha=10))
    text.fit(train["__text"], y)
    return float(y.mean()), tree.predict(test[nums]), text.predict(test["__text"])


def predict(train, test, nums):
    out = []
    for sd in SEEDS:
        c, t, x = parts(train, test, nums, sd)
        out.append((c, t, x, c + 1.25 * (.7 * t + .3 * x - c)))
    c = out[0][0]
    t = np.mean([o[1] for o in out], axis=0)
    x = np.mean([o[2] for o in out], axis=0)
    p = np.mean([o[3] for o in out], axis=0)
    return c, t, x, p


def cmd_oof(_a):
    pool, base, cols = training()
    nums = base + cols
    pred = np.full(len(pool), np.nan)
    for s in sorted(set(pool["set"])):
        te = (pool["set"] == s).to_numpy()
        pred[te] = predict(pool[~te], pool[te], nums)[3]
        print(s, flush=True)
    out = pool[["set", "name", "rarity_ord", "type_line", "actual_gih"]].assign(pred=pred)
    out.to_csv(OOF, index=False, compression="gzip")
    summ, per = g.within_set(out, pred)
    res = {"version": VERSION, "sets": sorted(set(pool["set"])), "n_cards": len(out), "within_set_mean": summ,
           "per_set": per.to_dict(orient="records"), "fin_used": False, "mh3_used": False}
    (HERE / "oof_metrics.json").write_text(json.dumps(res, indent=2, default=float))
    print(json.dumps({"mae_pp": summ["mae_pp"], "spearman": summ["spearman"]}))


def fra_frame(fra_path, base, cols, train):
    fra = json.loads(gzip.open(fra_path, "rt", encoding="utf-8").read())["cards"]
    norm = [c3.normalize(c) for c in fra]
    f = pd.DataFrame([card_features(c) for c in norm])
    f["oracle_text"] = [c["oracle_text"] for c in norm]
    f["type_line"] = [c["type_line"] for c in norm]
    f["__text"] = g.text_of(f)
    for c in ("is_supplemental_power_set", "is_premier_set"):
        if c not in f.columns:
            const = train[c].dropna().unique()
            if len(const) != 1:
                raise SystemExit(f"{c} is not constant in training")
            f[c] = const[0]
    missing = [c for c in base if c not in f.columns]
    if missing:
        raise SystemExit(f"FRA feature table lacks {missing}")
    x = pd.read_csv(c3.C3_OUT, keep_default_na=False).set_index("key")
    keys = [f"FRA|{c['id']}" for c in fra]
    if any(k not in x.index for k in keys):
        raise SystemExit("C3 missing for some FRA cards")
    for c in cols:
        f[c] = x.loc[keys, c].to_numpy(dtype=float)
    return fra, f


def head():
    return subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()


def cmd_adopted(a):
    pool, base, cols = training()
    fra, f = fra_frame(a.fra, base, cols, pool)
    nums = base + cols
    c, t, x, p = predict(pool, f, nums)
    # Check that the component reconstruction matches the research model exactly.
    ref = np.mean([c3.fit_predict(pool, f, nums, sd) for sd in SEEDS], axis=0)
    if not np.allclose(ref, p, atol=1e-10):
        raise SystemExit("component reconstruction does not match c3_research.fit_predict")
    sd_ = 1.25 * .7 * (t - c) * 100
    td_ = 1.25 * .3 * (x - c) * 100
    out = {
        "version": VERSION,
        "source_repository": "meatgoodbyeeee-wq/17lands-limited-forecast-data",
        "source_head": head(),
        "fin_used": False,
        "fin_final_check": "research/fin_final (Rule F confirmed: FIN MAE 2.611 -> 2.425pp, Spearman 0.407 -> 0.514)",
        "mh3_used": False,
        "training_sets": sorted(set(pool["set"])),
        "method": "ExtraTrees 600 leaf 8 max_features 0.6 on baseline + C3 features + word TF-IDF Ridge alpha 10; 70:30; fixed 1.25; seeds 20260922-24 averaged",
        "features": "baseline pre-release card features + C3 (LLM-extracted card-effect features, research/gih_llm_extract/RUBRIC.md)",
        "seeds": SEEDS,
        "base": round(c * 100, 5),
        "cards": [{"id": card["id"], "name": card["name"], "oracle_text": card.get("oracle_text") or "",
                   "type_line": card.get("type_line") or "", "mana_cost": card.get("mana_cost") or "",
                   "gih": round(float(pp * 100), 6), "structured_delta": round(float(s), 6), "text_delta": round(float(tt), 6)}
                  for card, pp, s, tt in zip(fra, p, sd_, td_)],
    }
    a.out.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(a.out, "wt", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False)
    s = pd.Series(p * 100)
    print(json.dumps({"cards": len(fra), "base": out["base"], "gih_min": round(s.min(), 3), "gih_median": round(s.median(), 3),
                      "gih_max": round(s.max(), 3), "gih_sd": round(s.std(), 3)}))


def range_frame(pool, base):
    o = pd.read_csv(OOF)
    feat = pd.read_csv(gi.FEAT, nrows=5)
    nums = [c for c in feat.columns if c not in gi.DROP and not c.startswith("color_") and pd.api.types.is_numeric_dtype(feat[c])]
    nums = [c for c in nums if c not in {"rarity_ord", "mv", "is_supplemental_power_set", "is_premier_set"}]
    d = o.merge(pool[["set", "name", "mv"] + nums], on=["set", "name"], how="left", validate="one_to_one")
    d["pred_pp"] = d["pred"] * 100
    d["actual_pp"] = d["actual_gih"] * 100
    d["r"] = d["actual_pp"] - d["pred_pp"]
    d["rarity"] = d["rarity_ord"].map(gi.RARITY)
    d["type_group"] = d["type_line"].map(gi.type_group)
    return d, ["pred_pp", "rarity_ord", "mv"] + nums


def cmd_range(a):
    pool, base, cols = training()
    d, rcols = range_frame(pool, base)
    rep = {}
    for name, fit, apply in (("M5_normalized", gi.m5_fit, gi.m5_apply), ("M4_rarity_type", gi.m4_fit, gi.m4_apply)):
        lo = np.zeros(len(d)); hi = np.zeros(len(d))
        for s in sorted(d.set.unique()):
            te = (d.set == s).to_numpy()
            p = fit(d.loc[~te], rcols)
            l, h = apply(p, d.loc[te], rcols)
            lo[te] = np.asarray(l); hi[te] = np.asarray(h)
        cover, width, wink = gi.score(d.actual_pp, lo, hi)
        by = lambda key: {k: round(float(cover[(d[key] == k).to_numpy()].mean()), 4) for k in d[key].unique()}
        per_set = pd.Series(cover).groupby(d.set.to_numpy()).mean()
        rep[name] = {"coverage": round(float(cover.mean()), 4),
                     "coverage_by_rarity": {k: by("rarity")[k] for k in gi.RARITY.values()},
                     "coverage_by_type": {k: by("type_group")[k] for k in gi.TYPES},
                     "per_set_coverage_min_max": [round(float(per_set.min()), 4), round(float(per_set.max()), 4)],
                     "mean_width": round(float(width.mean()), 4), "mean_interval_score": round(float(wink.mean()), 4)}
        print(name, json.dumps(rep[name]), flush=True)
    m5 = gi.m5_fit(d, rcols)
    m4 = gi.m4_fit(d, rcols)
    fra, f = fra_frame(a.fra, base, cols, pool)
    adopted = {c["id"]: c for c in json.loads(gzip.open(a.adopted, "rt", encoding="utf-8").read())["cards"]}
    if json.loads(gzip.open(a.adopted, "rt", encoding="utf-8").read())["version"] != VERSION:
        raise SystemExit("adopted file is not the final-candidate export")
    f["pred_pp"] = [adopted[c["id"]]["gih"] for c in fra]
    sigma = np.maximum(m5["model"].predict(f[rcols]), gi.SIGMA_FLOOR)
    radius = m5["q"] * sigma
    if not np.isfinite(radius).all() or not (radius > 0).all():
        raise SystemExit("invalid FRA radii")
    fallback = {rar: {t: round(float(m4["cell"].get((rar, t), m4["rarity"][rar])), 4) for t in gi.TYPES} for rar in gi.RARITY.values()}
    out = {
        "version": RANGE_VERSION,
        "method": "M5 normalized conformal (method unchanged from research/gih_interval): ExtraTrees predicts |residual| of the final GIH model; range = pred ± q·sigma",
        "target_coverage": gi.TARGET, "fin_used": False, "mh3_used": False,
        "gih_model_version": VERSION,
        "training_sets": sorted(d.set.unique()),
        "q": round(float(m5["q"]), 6), "sigma_floor": gi.SIGMA_FLOOR,
        "loso": rep["M5_normalized"], "loso_fallback_m4": rep["M4_rarity_type"],
        "fallback_note": "M4 rarity x type radius (FRA 'land' rarity counts as common); used when a card's text no longer matches this file",
        "fallback": fallback,
        "cards": [{"id": c["id"], "name": c["name"], "oracle_text": c.get("oracle_text") or "", "type_line": c.get("type_line") or "",
                   "mana_cost": c.get("mana_cost") or "", "radius": round(float(r), 4)} for c, r in zip(fra, radius)],
    }
    a.out.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
    (HERE / "range_loso.json").write_text(json.dumps({"version": RANGE_VERSION, **rep, "q": out["q"]}, indent=2))
    s = pd.Series(radius)
    print(json.dumps({"cards": len(radius), "q": out["q"], "radius_min": round(s.min(), 3), "radius_median": round(s.median(), 3),
                      "radius_max": round(s.max(), 3)}))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["oof", "adopted", "range"])
    ap.add_argument("--fra", type=Path)
    ap.add_argument("--adopted", type=Path)
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    {"oof": cmd_oof, "adopted": cmd_adopted, "range": cmd_range}[a.cmd](a)


if __name__ == "__main__":
    main()
