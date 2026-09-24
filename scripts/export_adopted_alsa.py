#!/usr/bin/env python3
"""Export the already adopted FIN-blind ALSA model for Pages inference."""
import argparse
import gzip
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline

from build_dev_features import card_features

DROP = {"actual_gih", "gih_wr", "gih_wr_pct", "gih_games", "gih_wins", "actual_alsa", "collector_number"}
NON_NUMERIC = {"set", "name", "oracle_text", "type_line", "window_start", "window_end", "rarity"}


def features(d, base, rarity_cols):
    rarity = pd.get_dummies(d.get("rarity", pd.Series("unknown", index=d.index)).fillna("unknown").astype(str), prefix="rarity", dtype=float)
    rarity = rarity.reindex(columns=rarity_cols, fill_value=0)
    x = pd.concat([d[base].reset_index(drop=True), rarity.reset_index(drop=True)], axis=1)
    txt = d.get("oracle_text", pd.Series("", index=d.index)).fillna("").astype(str).str.lower()
    typ = d.get("type_line", pd.Series("", index=d.index)).fillna("").astype(str).str.lower()
    sem = pd.DataFrame(index=d.index)
    sem["alsa_sem_removal"] = txt.str.contains(r"destroy target|exile target|target creature gets -").astype(float)
    sem["alsa_sem_draw"] = txt.str.contains(r"draw (a|one|two|three|\\d+) cards?").astype(float)
    sem["alsa_sem_evasion"] = (txt.str.contains(r"flying|menace|trample|can't be blocked") | typ.str.contains("vehicle")).astype(float)
    sem["alsa_sem_sweeper"] = txt.str.contains(r"all creatures|each creature|all other creatures").astype(float)
    sem["alsa_sem_dependency"] = txt.str.contains(r"if you control|for each|as long as|another .* you control|cards? in your graveyard").astype(float)
    sem["alsa_sem_narrow"] = txt.str.contains(r"artifact or enchantment|nonbasic land|creature with flying|from a graveyard").astype(float)
    sem["alsa_sem_creature"] = typ.str.contains("creature").astype(float)
    x = pd.concat([x, sem.reset_index(drop=True)], axis=1)
    for c in sem:
        for r in rarity:
            x[f"{c}_x_{r}"] = x[c].to_numpy() * rarity[r].to_numpy()
    x["alsa_pair_removal_draw"] = sem["alsa_sem_removal"].to_numpy() * sem["alsa_sem_draw"].to_numpy()
    x["alsa_sem_mana_fix"] = txt.str.contains(r"add one mana of any color|search your library for (a|up to one|one) basic land|basic land card").astype(float).to_numpy()
    return x


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--features", type=Path, required=True)
    ap.add_argument("--alsa", type=Path, required=True)
    ap.add_argument("--fra", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    f, y = pd.read_csv(a.features), pd.read_csv(a.alsa)
    if "FIN" in set(f["set"].astype(str).str.upper()) | set(y["set"].astype(str).str.upper()):
        raise SystemExit("FIN cannot be used for training or floor")
    d = f.merge(y, on=["set", "name"], how="inner")
    if len(d) < 1000 or len(set(d["set"])) != 22:
        raise SystemExit("Expected 22 FIN-blind development sets")
    base = [c for c in d.columns if c not in DROP | NON_NUMERIC and pd.api.types.is_numeric_dtype(d[c])]
    rarity = pd.get_dummies(d.get("rarity", pd.Series("unknown", index=d.index)).fillna("unknown").astype(str), prefix="rarity", dtype=float)
    x = features(d, base, rarity.columns.tolist())
    assert not any(c.startswith("alsa_sem_repeatable") for c in x) and "alsa_pair_removal_draw" in x and "alsa_sem_mana_fix" in x
    args = dict(loss="squared_error", max_iter=250, learning_rate=0.06, l2_regularization=2, random_state=20260923)
    model = make_pipeline(SimpleImputer(strategy="median"), HistGradientBoostingRegressor(**args))
    model.fit(x, d["actual_alsa"])
    imputer, hist = model.steps[0][1], model.steps[1][1]
    floor = float(d["actual_alsa"].min()) + 1e-6
    trees = []
    for stage in hist._predictors:
        nodes = stage[0].nodes
        trees.append([[int(n["feature_idx"]), float(n["num_threshold"]), int(n["left"]), int(n["right"]), float(n["value"]), int(n["is_leaf"]), int(n["missing_go_to_left"])] for n in nodes])
    artifact = {"version":"alsa-hist-22set-finfold-20260924", "model":args, "fin_used":False,
                "feature_names":x.columns.tolist(), "base_features":base, "rarity_columns":rarity.columns.tolist(),
                "medians":imputer.statistics_.tolist(), "baseline":float(hist._baseline_prediction[0,0]),
                "floor":floor, "trees":trees}
    fra = json.loads(a.fra.read_text())["cards"]
    f_fra = pd.DataFrame([card_features(c) for c in fra])
    f_fra["is_supplemental_power_set"] = 0
    f_fra["is_premier_set"] = 1
    xf = features(f_fra, base, rarity.columns.tolist())
    pred = np.maximum(model.predict(xf), floor)
    if len(pred) != len(fra) or not np.isfinite(pred).all() or not (pred > 1).all():
        raise SystemExit("Invalid FRA ALSA predictions")
    artifact["fra_predictions"] = {c["id"]:float(value) for c,value in zip(fra,pred)}
    with gzip.open(a.out,"wt",encoding="utf-8",compresslevel=9) as dest: json.dump(artifact,dest,separators=(",",":"),allow_nan=False)
    print(json.dumps({"cards":len(pred),"model":args,"floor":floor,"min":float(pred.min()),"median":float(np.median(pred)),"max":float(pred.max()),"fin_used":False,"trees":len(trees)}))


if __name__ == "__main__":
    main()
