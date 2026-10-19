"""K2 analysis per PLAN.md. Same definitions as K1's k1.py, computed for both arms.

usage (from this folder): python3 -I analyze_k2.py games [JSON_OUT]
Reads games/<arm>/job?.json (arm = base, patch) and ../c9_power_questions/oof_B10.csv.gz.
"""
import glob
import json
import math
import random
import re
import sys
import unicodedata

import numpy as np
import pandas as pd
from scipy import stats

GD = sys.argv[1]
JSON_OUT = sys.argv[2] if len(sys.argv) > 2 else None
A6 = ["Falcon's Wing Harness", "Iron Man Armor", "Stolen Stark Tech", "Super Suit", "Thirst for Knowledge", "Visions of Villainy"]


def norm(s):
    return re.sub(r"[^a-z0-9]", "", unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower())


o = pd.read_csv("../c9_power_questions/oof_B10.csv.gz")
o = o[o.set == "MSH"].copy()
o["a"] = (o.actual_gih - o.actual_gih.mean()) * 100
o["p"] = (o.pred - o.pred.mean()) * 100
o["res"] = o.a - o.p
o["k"] = o.name.map(norm)
A6K = {norm(n) for n in A6}


def card_table(arm):
    G = []
    jobs = sorted(glob.glob(f"{GD}/{arm}/job?.json"))
    for f in jobs:
        G += json.load(open(f))
    obs = []
    for g in G:
        if g["winner"] is None:
            continue
        for dk, cards in g["draws"].items():
            for c in cards:
                obs.append((norm(c), int(g["winner"] == dk)))
    ob = pd.DataFrame(obs, columns=["k", "w"])
    ob = ob[ob.k.isin(set(o.k))]
    cnt = ob.groupby("k").w.agg(["size", "sum"]).rename(columns={"size": "n", "sum": "wins"})
    cnt["gih"] = cnt.wins / cnt.n
    return cnt, len(G), [f.split("/")[-1] for f in jobs]


tabs = {}
meta = {}
for arm in ("base", "patch"):
    cnt, ng, jobs = card_table(arm)
    tabs[arm] = cnt
    meta[arm] = {"games": ng, "jobs": jobs}
common_jobs = sorted(set(meta["base"]["jobs"]) & set(meta["patch"]["jobs"]))
if meta["base"]["jobs"] != meta["patch"]["jobs"]:
    print("WARNING: arms have different job sets", meta)

# eligibility as in K1: n >= 150 in each arm; use cards eligible in both arms for comparisons
elig = tabs["base"].index[tabs["base"].n >= 150].intersection(tabs["patch"].index[tabs["patch"].n >= 150])
res = {"meta": meta, "eligible_both": int(len(elig))}
E = {}
for arm in ("base", "patch"):
    t = tabs[arm].loc[elig]
    E[arm] = (t.gih - t.gih.mean()) * 100
d = o.set_index("k").loc[elig, ["name", "a", "p", "res"]].copy()
d["e_base"], d["e_patch"] = E["base"], E["patch"]
d["n_base"], d["n_patch"] = tabs["base"].loc[elig].n, tabs["patch"].loc[elig].n


def summary(e):
    r1 = stats.spearmanr(e, d.a)[0]
    r2 = stats.spearmanr(e, d.res)[0]
    X = np.c_[np.ones(len(d)), d.p.values, e.values]
    y = d.a.values
    err = []
    for i in range(len(d)):
        t = np.arange(len(d)) != i
        b = np.linalg.lstsq(X[t], y[t], rcond=None)[0]
        err.append(abs(y[i] - X[i] @ b))
    return {"rho_e_a": float(r1), "rho_e_res": float(r2), "loo_mae_p_plus_e": float(np.mean(err))}


for arm in ("base", "patch"):
    res[arm] = summary(d["e_" + arm])
Xp = np.c_[np.ones(len(d)), d.p.values]
errp = []
for i in range(len(d)):
    t = np.arange(len(d)) != i
    b = np.linalg.lstsq(Xp[t], d.a.values[t], rcond=None)[0]
    errp.append(abs(d.a.values[i] - Xp[i] @ b))
res["loo_mae_p_only"] = float(np.mean(errp))
res["k1_reference"] = {"rho_e_a": 0.4216, "rho_e_res": 0.2852, "loo_mae_p_only": 2.2643, "loo_mae_p_plus_e": 2.1773}

# primary: A6 change in e
rows = []
for k in sorted(A6K & set(elig)):
    nb, npch = d.loc[k, "n_base"], d.loc[k, "n_patch"]
    gb, gp = tabs["base"].loc[k, "gih"], tabs["patch"].loc[k, "gih"]
    se = 100 * math.sqrt(gb * (1 - gb) / nb + gp * (1 - gp) / npch)
    rows.append({"name": d.loc[k, "name"], "e_base": float(d.loc[k, "e_base"]), "e_patch": float(d.loc[k, "e_patch"]),
                 "delta": float(d.loc[k, "e_patch"] - d.loc[k, "e_base"]), "se": se, "a": float(d.loc[k, "a"]),
                 "n_base": int(nb), "n_patch": int(npch)})
missing = sorted(A6K - set(elig))
mean_delta = float(np.mean([r["delta"] for r in rows])) if rows else float("nan")
se_mean = math.sqrt(sum(r["se"] ** 2 for r in rows)) / len(rows) if rows else float("nan")
lo, hi = mean_delta - 1.96 * se_mean, mean_delta + 1.96 * se_mean
verdict = "改善" if lo > 0 else "悪化" if hi < 0 else "判定できず"
res["A6"] = {"cards": rows, "not_eligible": missing, "mean_delta": mean_delta, "ci95": [lo, hi], "verdict": verdict}
others = d.index.difference(list(A6K))
res["noise_mean_abs_delta_others"] = float((d.loc[others, "e_patch"] - d.loc[others, "e_base"]).abs().mean())

# secondary: card bootstrap of the changes
rng = np.random.default_rng(20261019)
idx = np.arange(len(d))
deltas = {"rho_e_a": [], "rho_e_res": []}
for _ in range(2000):
    s = rng.choice(idx, len(idx), replace=True)
    sub = d.iloc[s]
    for key, col in (("rho_e_a", "a"), ("rho_e_res", "res")):
        deltas[key].append(stats.spearmanr(sub.e_patch, sub[col])[0] - stats.spearmanr(sub.e_base, sub[col])[0])
res["secondary"] = {k: {"delta": res["patch"][k] - res["base"][k], "ci95": [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))]}
                    for k, v in deltas.items()}
res["secondary"]["loo_mae_p_plus_e_delta"] = res["patch"]["loo_mae_p_plus_e"] - res["base"]["loo_mae_p_plus_e"]

print(json.dumps(res, ensure_ascii=False, indent=1))
if JSON_OUT:
    json.dump(res, open(JSON_OUT, "w"), ensure_ascii=False, indent=1)
