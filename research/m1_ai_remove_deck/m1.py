"""M1 scoring per PLAN.md. usage: python3 -I m1.py <oof_B10.csv.gz> <marks.csv> <fra_frozen.csv> [JSON_OUT]
marks.csv: set,name,...,mark_all_release,mark_random_release,mark_all_today,mark_random_today (one row per OOF row + FRA rows)."""
import json, sys
import numpy as np, pandas as pd
from scipy import stats
oof, mk, fra = sys.argv[1:4]; out = sys.argv[4] if len(sys.argv) > 4 else None
D = pd.read_csv(oof); M = pd.read_csv(mk)
M = M.drop_duplicates(["set", "name"])
D = D.merge(M, on=["set", "name"], how="left")
for c in ["mark_all_release", "mark_random_release", "mark_all_today", "mark_random_today", "found_release", "found_today"]:
    D[c] = D[c].fillna(0).astype(int)
D["a"] = D.actual_gih * 100; D["p"] = D.pred * 100
D["r"] = D.a - D.p; D["r"] -= D.groupby("set").r.transform("mean")
sets = sorted(D.set.unique())

def perm_p(col, n=10000, seed=1):
    rng = np.random.default_rng(seed); obs = D.loc[D[col] == 1, "r"].mean(); cnt = 0
    groups = [(g.r.values, int(g[col].sum())) for _, g in D.groupby("set")]
    tot = D[col].sum()
    for _ in range(n):
        s = sum(rng.choice(v, k, replace=False).sum() for v, k in groups if k)
        cnt += s / tot <= obs
    return float((cnt + 1) / (n + 1))

def boot_ci(col, n=10000, seed=2):
    rng = np.random.default_rng(seed); by = {s: D.loc[(D.set == s) & (D[col] == 1), "r"].values for s in sets}; vals = []
    for _ in range(n):
        pick = np.concatenate([by[s] for s in rng.choice(sets, len(sets))])
        if len(pick): vals.append(pick.mean())
    return [float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))]

def correct(col):
    q = D.p.copy(); delta = {}
    for s in sets:
        o = D[(D.set != s) & (D[col] == 1)]
        delta[s] = float(o.r.mean()) if len(o) else 0.0
        q[(D.set == s) & (D[col] == 1)] += delta[s]   # delta is negative when marked cards are over-predicted
    return q, delta

def summary(col):
    n = int(D[col].sum()); res = {"marked": n}
    if n == 0: return res
    q, delta = correct(col)
    mae = lambda x: float(np.mean(np.abs(D.a - x)))
    sp = lambda x: float(np.mean([stats.spearmanr(x[D.set == s], D.a[D.set == s])[0] for s in sets]))
    better = sum(np.mean(np.abs(D.a[D.set == s] - q[D.set == s])) < np.mean(np.abs(D.a[D.set == s] - D.p[D.set == s])) for s in sets)
    worse = sum(np.mean(np.abs(D.a[D.set == s] - q[D.set == s])) > np.mean(np.abs(D.a[D.set == s] - D.p[D.set == s])) for s in sets)
    res.update({"mean_r": float(D.loc[D[col] == 1, "r"].mean()), "ci95_set_boot": boot_ci(col), "p_one_sided_perm": perm_p(col),
                "mae_b10": mae(D.p), "mae_corrected": mae(q), "spearman_b10": sp(D.p), "spearman_corrected": sp(q),
                "sets_mae_lower": int(better), "sets_mae_higher": int(worse), "delta_all28": float(D.loc[D[col] == 1, "r"].mean()),
                "by_set": {s: int(D.loc[D.set == s, col].sum()) for s in sets},
                "by_rarity": {int(k): [int(len(g)), float(g.r.mean())] for k, g in D[D[col] == 1].groupby("rarity_ord")},
                "pred_pct_mean": float(D.groupby("set").p.rank(pct=True)[D[col] == 1].mean()),
                "cards": D.loc[D[col] == 1, ["set", "name", "rarity_ord", "a", "p", "r"]].round(2).values.tolist()})
    return res

R = {"cards": len(D), "found_release": int(D.found_release.sum()), "found_today": int(D.found_today.sum())}
for c in ["mark_all_release", "mark_all_today", "mark_random_release", "mark_random_today"]: R[c] = summary(c)
m = R["mark_all_release"]
if m["marked"] < 20: R["rule_m1"] = "判定できず(印のカード 20 枚未満)"
else:
    ok = m["mean_r"] < 0 and m["p_one_sided_perm"] < 0.05 and m["mae_corrected"] < m["mae_b10"] and m["spearman_corrected"] >= m["spearman_b10"]
    R["rule_m1"] = "支持" if ok else "不支持"
# FRA (report only)
F = pd.read_csv(fra); FM = M[M.set == "FRA"]
R["fra_marked_release"] = FM.loc[FM.mark_all_release == 1, "name"].tolist(); R["fra_marked_today"] = FM.loc[FM.mark_all_today == 1, "name"].tolist()
print(json.dumps({k: v for k, v in R.items()}, ensure_ascii=False, indent=1, default=str)[:6000])
if out: json.dump(R, open(out, "w"), ensure_ascii=False, indent=1)
