"""Follow-up checks for the effect analysis (exploratory).
A. outcome = IWD (drawing the card) and GNS (deck level): which features are significant there (BH q)?
B. blue vs non-blue: do "blue-like" effects carry a difference outside blue?
C. robustness: log-odds outcome; control for card strength (other half of the games, linear + square); cards with >= 2000 top games.
Usage: python3 followup.py <cards.csv.gz> <effects_all.csv> <out dir>"""
import sys, warnings
from pathlib import Path
import numpy as np, pandas as pd
from scipy import stats
warnings.filterwarnings("ignore")
E = pd.read_csv(sys.argv[1], low_memory=False); R0 = pd.read_csv(sys.argv[2]); OUT = Path(sys.argv[3])
pd.set_option("display.width", 250); pd.set_option("display.max_rows", 300)
TAU2 = float(np.cov(E.e0_gih_A, E.e1_gih_A)[0, 1]); E["w"] = 1 / (E.v_A + TAU2)
D = E[E.tagged & ~E.is_land.astype(bool)].copy().reset_index(drop=True)
for c in D.columns:
    if D[c].dtype == object and set(D[c].dropna().unique()) <= {"True", "False", True, False}: D[c] = D[c].astype(str).eq("True")
sets = sorted(D.set.unique()); G = len(sets); sidx = D.set.map({s: i for i, s in enumerate(sets)}).to_numpy(); SETFE = np.eye(G)[sidx]
D["type4"] = np.select([D.is_creature, D.is_instant, D.is_sorcery], ["creature", "instant", "sorcery"], "other"); D["rar"] = D.rar.fillna(1).clip(0, 3).astype(int)
dm = lambda col, drop: pd.get_dummies(D[col]).drop(columns=[drop]).to_numpy(float)
CTRL = {"colour": D[["col_W", "col_U", "col_B", "col_R", "col_G"]].to_numpy(float), "type": dm("type4", "creature"), "rarity": dm("rar", 0), "mv": D[["mv"]].fillna(D.mv.median()).clip(0, 8).to_numpy(float)}
W = D.w.to_numpy(float)
def wls(y, f, skip=(), rows=None, extra=None, w=W):
    X = np.column_stack([f] + [v for k, v in CTRL.items() if k not in skip] + ([extra] if extra is not None else []) + [SETFE])
    ok = np.isfinite(y) & np.isfinite(X).all(1)
    if rows is not None: ok &= rows
    y, X, ww, g = y[ok], X[ok], w[ok], sidx[ok]
    keep = X.std(0) > 0; keep[0] = True; X = X[:, keep]
    XtW = X.T * ww; A = np.linalg.pinv(XtW @ X); b = A @ (XtW @ y); u = y - X @ b; meat = np.zeros((X.shape[1],) * 2); gs = np.unique(g)
    for k in gs:
        m = g == k; s = (X[m].T * (ww[m] * u[m])).sum(1); meat += np.outer(s, s)
    V = A @ meat @ A * (len(gs) / (len(gs) - 1)) * ((len(y) - 1) / max(len(y) - X.shape[1], 1)); se = np.sqrt(max(V[0, 0], 1e-12))
    return b[0], se, 2 * stats.t.sf(abs(b[0] / se), len(gs) - 1), int((f[ok] > 0).sum())
def bh(p):
    p = np.asarray(p); o = np.argsort(p); q = np.empty(len(p)); q[o] = np.minimum.accumulate((p[o] * len(p) / np.arange(1, len(p) + 1))[::-1])[::-1]; return np.minimum(q, 1)
SKIP = {"is_creature": ("type",), "is_instant": ("type",), "is_sorcery": ("type",), "is_artifact": ("type",), "is_enchantment": ("type",), "col_W": ("colour",), "col_U": ("colour",), "col_B": ("colour",), "col_R": ("colour",), "col_G": ("colour",), "col_none": ("colour",)}
def feat(name):
    if name.startswith("rarity_"): return (D.rar == ["common", "uncommon", "rare", "mythic"].index(name[7:])).to_numpy(float), ("rarity",)
    if name.startswith("creature ") or name.startswith("noncreature "):
        cr = D.is_creature.to_numpy()
        m = {"creature mv<=2": cr & (D.mv <= 2), "creature mv 3-4": cr & D.mv.between(3, 4), "creature mv>=5": cr & (D.mv >= 5), "creature power>=4": cr & (D.power >= 4),
             "creature tough>=4 & power<=2": cr & (D.tough >= 4) & (D.power <= 2), "creature power>tough": cr & (D.power > D.tough), "noncreature mv<=2": ~cr & (D.mv <= 2), "noncreature mv>=5": ~cr & (D.mv >= 5)}[name]
        return np.asarray(m, float), ("mv",)
    if name.endswith(" (per SD)"):
        v = D[name[:-9]].fillna(0).to_numpy(float); return (v - v.mean()) / v.std(), ()
    if name.endswith("=2 (main)"): return (D[name[:-9]].fillna(0) >= 2).to_numpy(float), ()
    return (D[name].fillna(0).astype(float) > 0).to_numpy(float), SKIP.get(name, ())

# ---------- A. IWD and GNS as outcomes
rows = []
for name in R0.feature:
    f, skip = feat(name)
    a = wls(D.e_iwd_A.to_numpy(float), f, skip); g = wls(D.e_gns_A.to_numpy(float), f, skip)
    a0 = wls(D.e0_iwd_A.to_numpy(float), f, skip); a1 = wls(D.e1_iwd_A.to_numpy(float), f, skip)
    g0 = wls(D.e0_gns_A.to_numpy(float), f, skip); g1 = wls(D.e1_gns_A.to_numpy(float), f, skip)
    rows.append(dict(feature=name, n=a[3], iwd=a[0], iwd_se=a[1], iwd_p=a[2], iwd_h0=a0[0], iwd_h1=a1[0], gns=g[0], gns_se=g[1], gns_p=g[2], gns_h0=g0[0], gns_h1=g1[0]))
A = pd.DataFrame(rows); A["iwd_q"] = bh(A.iwd_p); A["gns_q"] = bh(A.gns_p)
A = A.merge(R0[["feature", "group", "ctrl", "q"]].rename(columns={"ctrl": "gih", "q": "gih_q"}), on="feature"); A.to_csv(OUT / "effects_iwd_gns.csv", index=False)
print("=== A. drawing the card (IWD): q < 0.05:", int((A.iwd_q < .05).sum()), "| deck level (GNS): q < 0.05:", int((A.gns_q < .05).sum()))
c = ["group", "feature", "n", "gih", "gih_q", "iwd", "iwd_se", "iwd_q", "iwd_h0", "iwd_h1", "gns", "gns_se", "gns_q"]
print("IWD, q < 0.05:"); print(A[A.iwd_q < .05].sort_values("iwd", ascending=False)[c].round(3).to_string(index=False))
print("GNS, q < 0.05:"); print(A[A.gns_q < .05].sort_values("gns", ascending=False)[c].round(3).to_string(index=False))

# ---------- B. blue vs non-blue
print("\n=== B. inside blue and outside blue (controls: type, rarity, mana value, other colours; GIH outcome)")
U = D.col_U.to_numpy(bool); y = D.e_gih_A.to_numpy(float); rows = []
for name in ["c5_DR", "c5_DR=2 (main)", "x_draw2", "c5_SC", "x_loot", "x_discard_self", "c5_CS", "c5_BN", "c5_TP", "c5_FH", "c5_FL", "c5_RC", "c5_RE", "x_instant_sorcery_matters", "is_instant", "is_sorcery", "is_creature", "c5_RM", "c5_FX", "c5_EQ", "c5_HS", "c5_IN", "c4_role_A", "c4_role_T", "c4_role_V", "c5_CLK (per SD)", "creature mv>=5", "creature mv<=2", "rarity_common", "rarity_rare"]:
    f, skip = feat(name); skip = tuple(set(skip) | {"colour"}); ex = D[["col_W", "col_B", "col_R", "col_G"]].to_numpy(float)
    if (f[U] > 0).sum() < 15 and "per SD" not in name: continue
    a = wls(y, f, skip, rows=U, extra=ex); b = wls(y, f, skip, rows=~U, extra=ex)
    rows.append(dict(feature=name, n_blue=a[3], blue=a[0], blue_se=a[1], n_other=b[3], other=b[0], other_se=b[1], other_p=b[2]))
B = pd.DataFrame(rows); print(B.round(3).to_string(index=False)); B.to_csv(OUT / "effects_blue_split.csv", index=False)
print("mean difference of blue cards by type (weighted): ", {k: round(float(np.average(v.e_gih_A, weights=v.w)), 2) for k, v in D[U].groupby("type4")}, "| non-blue:", {k: round(float(np.average(v.e_gih_A, weights=v.w)), 2) for k, v in D[~U].groupby("type4")})

# ---------- C. robustness
print("\n=== C. robustness of the q < 0.05 features")
pT = D.T_gih / 100; pA = D.A_gih / 100; lo = np.log(pT / (1 - pT)) - np.log(pA / (1 - pA)); lo = lo - lo.groupby(D.set).transform("mean")
D["e_logit_pp"] = 100 * lo * (pT.groupby(D.set).transform("mean") * (1 - pT.groupby(D.set).transform("mean")))
strength = np.column_stack([D.A0_c, D.A0_c ** 2]); big = (D.T_gih_g >= 2000).to_numpy()
rows = []
for name in R0[R0.q < .05].sort_values("ctrl", ascending=False).feature:
    f, skip = feat(name)
    rows.append(dict(feature=name, main=wls(y, f, skip)[0], logodds=wls(D.e_logit_pp.to_numpy(float), f, skip)[0],
                     strength_ctrl=wls(D.e0_gih_A.to_numpy(float), f, skip, extra=strength)[0], half0=wls(D.e0_gih_A.to_numpy(float), f, skip)[0],
                     games2000=wls(y, f, skip, rows=big)[0], unweighted=wls(y, f, skip, w=np.ones(len(D)))[0], vs_normal=wls(D.e_gih_N.to_numpy(float), f, skip)[0], vs_normal_p=wls(D.e_gih_N.to_numpy(float), f, skip)[2]))
Cc = pd.DataFrame(rows); Cc["all_same_sign"] = (np.sign(Cc[["logodds", "strength_ctrl", "games2000", "unweighted", "vs_normal"]]).T == np.sign(Cc.main)).all()
print(Cc.round(3).to_string(index=False)); Cc.to_csv(OUT / "effects_robustness.csv", index=False)
for name in ("x_clue", "c5_CY", "x_treasure", "x_loot", "c5_LL"):
    f, _ = feat(name); print(name, "sets:", D[f > 0].groupby("set").size().to_dict())
