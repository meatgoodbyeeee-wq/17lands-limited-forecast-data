"""K3 analysis per PLAN.md: K1's per-set analysis for each new set, plus a pooled test across sets.

usage (from this folder): python3 -I k3.py [JSON_OUT]
Reads games_<SET>/base/job?.json for SET in HOB, SOS, TMT, and ../k2_engine_gih_patched/games/base (MSH, reference only).
Actual data: ../c9_power_questions/oof_B10.csv.gz.
"""
import glob
import json
import random
import re
import sys
import unicodedata

import numpy as np
import pandas as pd
from scipy import stats

NEW_SETS = ["HOB", "SOS", "TMT"]
MSH_DIR = "../k2_engine_gih_patched/games/base"
JSON_OUT = sys.argv[1] if len(sys.argv) > 1 else None


def norm(s):
    return re.sub(r"[^a-z0-9]", "", unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower())


O = pd.read_csv("../c9_power_questions/oof_B10.csv.gz")


def per_set(code, gdir):
    o = O[O.set == code].copy()
    o["a"] = (o.actual_gih - o.actual_gih.mean()) * 100
    o["p"] = (o.pred - o.pred.mean()) * 100
    o["res"] = o.a - o.p
    o["k"] = o.name.map(norm)
    G = []
    for f in sorted(glob.glob(gdir + "/job?.json")):
        G += json.load(open(f))
    obs = []
    for gi, g in enumerate(G):
        if g["winner"] is None:
            continue
        for dk, cards in g["draws"].items():
            for c in cards:
                obs.append((norm(c), int(g["winner"] == dk), gi))
    ob = pd.DataFrame(obs, columns=["k", "w", "gi"])
    ob = ob[ob.k.isin(set(o.k))]
    cnt = ob.groupby("k").w.agg(["size", "mean"]).rename(columns={"size": "n", "mean": "gih"})
    elig = cnt[cnt.n >= 150]
    elig = elig.assign(e=(elig.gih - elig.gih.mean()) * 100)
    d = o.merge(elig, left_on="k", right_index=True)
    rng = random.Random(1)
    gis = sorted(ob.gi.unique())
    rs = []
    for _ in range(20):
        half = set(rng.sample(gis, len(gis) // 2))
        A = ob[ob.gi.isin(half)].groupby("k").w.mean()
        B = ob[~ob.gi.isin(half)].groupby("k").w.mean()
        j = A.index.intersection(B.index).intersection(d.k)
        r = stats.spearmanr(A[j], B[j])[0]
        rs.append(2 * r / (1 + r))
    r1 = stats.spearmanr(d.e, d.a)
    r2 = stats.spearmanr(d.e, d.res)
    p_one = r2[1] / 2 if r2[0] > 0 else 1 - r2[1] / 2
    out = {"set": code, "games": len(G), "no_winner": sum(g["winner"] is None for g in G), "cards_in_data": len(o),
           "eligible": int(len(d)), "excluded_lt150": int(len(cnt) - len(elig)), "reliability": float(np.mean(rs)),
           "rho_e_a": float(r1[0]), "p_e_a": float(r1[1]), "rho_e_res": float(r2[0]), "p_e_res_one_sided": float(p_one),
           "mae_p": loo(d, ["p"]), "mae_pe": loo(d, ["p", "e"])}
    b = np.linalg.lstsq(np.c_[np.ones(len(d)), d.p, d.e], d.a, rcond=None)[0]
    out["coef_intercept_p_e"] = [float(x) for x in b]
    d = d.assign(set=code)
    return out, d[["set", "name", "a", "p", "res", "e", "n"]]


def loo(d, cols):
    X = np.c_[np.ones(len(d)), d[cols].values]
    y = d.a.values
    err = []
    for i in range(len(d)):
        t = np.arange(len(d)) != i
        b = np.linalg.lstsq(X[t], y[t], rcond=None)[0]
        err.append(abs(y[i] - X[i] @ b))
    return float(np.mean(err))


res = {"per_set": {}}
frames = []
for code in NEW_SETS:
    r, d = per_set(code, f"games_{code}/base")
    res["per_set"][code] = r
    frames.append(d)
    print(json.dumps(r, ensure_ascii=False))
pooled = pd.concat(frames, ignore_index=True)
res["pooled_new"] = {"cards": int(len(pooled)), "mae_p": loo(pooled, ["p"]), "mae_pe": loo(pooled, ["p", "e"]),
                     "rho_e_res": float(stats.spearmanr(pooled.e, pooled.res)[0]),
                     "coef_intercept_p_e": [float(x) for x in np.linalg.lstsq(np.c_[np.ones(len(pooled)), pooled.p, pooled.e], pooled.a, rcond=None)[0]]}
n_sig = sum(1 for c in NEW_SETS if res["per_set"][c]["rho_e_res"] > 0 and res["per_set"][c]["p_e_res_one_sided"] < 0.05)
res["rule_k3"] = {"sets_with_sig_positive_rho_e_res": n_sig, "pooled_mae_improves": res["pooled_new"]["mae_pe"] < res["pooled_new"]["mae_p"],
                  "supported": bool(n_sig >= 2 and res["pooled_new"]["mae_pe"] < res["pooled_new"]["mae_p"])}
# reference: add MSH (K2 unpatched games)
try:
    r, d = per_set("MSH", MSH_DIR)
    res["msh_reference"] = r
    all4 = pd.concat(frames + [d], ignore_index=True)
    res["pooled_with_msh"] = {"cards": int(len(all4)), "mae_p": loo(all4, ["p"]), "mae_pe": loo(all4, ["p", "e"]),
                              "coef_intercept_p_e": [float(x) for x in np.linalg.lstsq(np.c_[np.ones(len(all4)), all4.p, all4.e], all4.a, rcond=None)[0]]}
except Exception as ex:  # MSH games may be missing in a fresh checkout
    res["msh_reference_error"] = str(ex)
pooled.to_csv("cards_e.csv", index=False)
print(json.dumps({k: v for k, v in res.items() if k != "per_set"}, ensure_ascii=False, indent=1))
if JSON_OUT:
    json.dump(res, open(JSON_OUT, "w"), ensure_ascii=False, indent=1)
