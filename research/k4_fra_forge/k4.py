"""K4 scoring per PLAN.md. usage: python3 -I k4.py <games_dir> <pred_csv> <actual_csv> [JSON_OUT]
games_dir: games_FRA/base (job?.json). pred_csv: columns name,pred_B10 (frozen). actual_csv: columns name,actual_gih,gih_games
(FRA 28-day, only used at scoring time; dry-run uses synthetic data). Prediction = p + 0.1*e (p, e centred, x100)."""
import glob, json, re, random, sys, unicodedata
import numpy as np, pandas as pd
from scipy import stats
W = 0.1
gdir, predf, actf = sys.argv[1:4]; out = sys.argv[4] if len(sys.argv) > 4 else None
norm = lambda s: re.sub(r"[^a-z0-9]", "", unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower())
P = pd.read_csv(predf); A = pd.read_csv(actf)
P["k"] = P.name.map(norm); A["k"] = A.name.map(norm)
G = []
for f in sorted(glob.glob(gdir + "/job?.json")): G += json.load(open(f))
obs = [(norm(c), int(g["winner"] == dk), gi) for gi, g in enumerate(G) if g["winner"] is not None for dk, cs in g["draws"].items() for c in cs]
ob = pd.DataFrame(obs, columns=["k", "w", "gi"])
cnt = ob.groupby("k").w.agg(["size", "mean"]).rename(columns={"size": "n", "mean": "gih"})
cnt = cnt[cnt.n >= 150]
d = A[A.gih_games >= 500].merge(P[["k", "pred_B10"]], on="k").merge(cnt, left_on="k", right_index=True)
d["a"] = (d.actual_gih - d.actual_gih.mean()) * 100
d["p"] = (d.pred_B10 - d.pred_B10.mean()) * 100
d["e"] = (d.gih - d.gih.mean()) * 100
d["res"] = d.a - d.p; d["q"] = d.p + W * d.e
mae = lambda x: float(np.mean(np.abs(d.a - x)))
sp = lambda x: float(stats.spearmanr(x, d.a)[0])
r2 = stats.spearmanr(d.e, d.res); p1 = r2[1] / 2 if r2[0] > 0 else 1 - r2[1] / 2
rng = random.Random(1); gis = sorted(ob.gi.unique()); rs = []
for _ in range(20):
    h = set(rng.sample(gis, len(gis) // 2)); a_ = ob[ob.gi.isin(h)].groupby("k").w.mean(); b_ = ob[~ob.gi.isin(h)].groupby("k").w.mean()
    j = a_.index.intersection(b_.index).intersection(d.k); r = stats.spearmanr(a_[j], b_[j])[0]; rs.append(2 * r / (1 + r))
res = {"cards": len(d), "games": len(G), "mae_p": mae(d.p), "mae_q": mae(d.q), "spearman_p": sp(d.p), "spearman_q": sp(d.q),
       "rho_e_a": float(stats.spearmanr(d.e, d.a)[0]), "rho_e_res": float(r2[0]), "p_one_sided": float(p1), "reliability": float(np.mean(rs)),
       "refit_coef_intercept_p_e": [float(x) for x in np.linalg.lstsq(np.c_[np.ones(len(d)), d.p, d.e], d.a, rcond=None)[0]]}
res["rule_k4_supported"] = bool(res["mae_q"] < res["mae_p"] and res["spearman_q"] > res["spearman_p"])
print(json.dumps(res, ensure_ascii=False, indent=1))
if out: json.dump(res, open(out, "w"), ensure_ascii=False, indent=1)
