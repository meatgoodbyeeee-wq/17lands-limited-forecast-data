"""Which effects / abilities go with a top-player-specific difference? (exploratory)
Input: build.py output. Outcome: e_gih_A = top players' GIH minus what everyone else's GIH predicts (pp, per-set slope).
For each feature: raw difference (set fixed effects only) and controlled difference (colour, card type, rarity, mana value
and set fixed effects), precision-weighted, with set-clustered standard errors (23 sets), Benjamini-Hochberg q-values,
split-half and split-set replication, and the same coefficient for GNS (deck-level), IWD (drawing the card) and vs normal players.
Usage: python3 analyze.py <cards.csv.gz> <out dir>"""
import sys, warnings
from pathlib import Path
import numpy as np, pandas as pd
from scipy import stats
warnings.filterwarnings("ignore")
E = pd.read_csv(sys.argv[1], low_memory=False); OUT = Path(sys.argv[2]); OUT.mkdir(parents=True, exist_ok=True)
pd.set_option("display.width", 260); pd.set_option("display.max_columns", 40); pd.set_option("display.max_rows", 400)
lines = []
def say(*a):
    s = " ".join(str(x) for x in a); print(s); lines.append(s)
TAU2 = float(np.cov(E.e0_gih_A, E.e1_gih_A)[0, 1])
E["w"] = 1 / (E.v_A + TAU2); E["est"] = E.e_gih_A * TAU2 / (TAU2 + E.v_A)
D = E[E.tagged & ~E.is_land.astype(bool)].copy().reset_index(drop=True)
say(f"cards with tags, nonland: {len(D)} of {len(E)} (true variance of the difference {TAU2:.3f}, SD {np.sqrt(TAU2):.3f}pp)")
for c in D.columns:
    if D[c].dtype == object and set(D[c].dropna().unique()) <= {"True", "False", True, False}: D[c] = D[c].astype(str).eq("True")
G = D.set.nunique(); sets = sorted(D.set.unique()); sidx = D.set.map({s: i for i, s in enumerate(sets)}).to_numpy()
SETFE = np.eye(G)[sidx]
D["type4"] = np.select([D.is_creature, D.is_instant, D.is_sorcery], ["creature", "instant", "sorcery"], "other")
D["rar"] = D.rar.fillna(1).clip(0, 3).astype(int)
def dummies(col, drop): return pd.get_dummies(D[col]).drop(columns=[drop]).to_numpy(float)
CTRL = {"colour": D[["col_W", "col_U", "col_B", "col_R", "col_G"]].to_numpy(float), "type": dummies("type4", "creature"),
        "rarity": dummies("rar", 0), "mv": D[["mv"]].fillna(D.mv.median()).clip(0, 8).to_numpy(float)}
def design(f, skip=()):
    return np.column_stack([f] + [v for k, v in CTRL.items() if k not in skip] + [SETFE])
def wls(y, X, w, rows=None):
    if rows is None: rows = np.isfinite(y)
    else: rows = rows & np.isfinite(y)
    y, X, w, g = y[rows], X[rows], w[rows], sidx[rows]
    keep = X.std(0) > 0; keep[0] = True; X = X[:, keep]
    XtW = X.T * w; A = np.linalg.pinv(XtW @ X); b = A @ (XtW @ y); u = y - X @ b
    meat = np.zeros((X.shape[1], X.shape[1])); gs = np.unique(g)
    for k in gs:
        m = g == k; s = (X[m].T * (w[m] * u[m])).sum(1); meat += np.outer(s, s)
    n, kk, Gk = len(y), X.shape[1], len(gs)
    V = A @ meat @ A * (Gk / (Gk - 1)) * ((n - 1) / max(n - kk, 1))
    se = np.sqrt(max(V[0, 0], 1e-12)); return b[0], se, 2 * stats.t.sf(abs(b[0] / se), Gk - 1)
Y = {k: D[k].to_numpy(float) for k in ("e_gih_A", "e0_gih_A", "e1_gih_A", "e_gns_A", "e_iwd_A", "e_gih_N", "rate_diff_A")}
W = D.w.to_numpy(float); even = (D.set_order % 2 == 0).to_numpy()
def one(name, f, skip=(), kind="binary", group=""):
    f = np.asarray(f, float); n = int((f > 0).sum())
    X0 = np.column_stack([f, SETFE]); X1 = design(f, skip)
    raw = wls(Y["e_gih_A"], X0, W); c = wls(Y["e_gih_A"], X1, W)
    r = dict(group=group, feature=name, kind=kind, n=n, raw=raw[0], raw_se=raw[1], ctrl=c[0], ctrl_se=c[1], p=c[2],
             h0=wls(Y["e0_gih_A"], X1, W)[0], h1=wls(Y["e1_gih_A"], X1, W)[0],
             sets_a=wls(Y["e_gih_A"], X1, W, even)[0], sets_b=wls(Y["e_gih_A"], X1, W, ~even)[0],
             gns=wls(Y["e_gns_A"], X1, W)[0], iwd=wls(Y["e_iwd_A"], X1, W)[0], vsN=wls(Y["e_gih_N"], X1, W)[0], vsN_p=wls(Y["e_gih_N"], X1, W)[2],
             rate_diff=wls(Y["rate_diff_A"], X1, W)[0] * 100)
    if kind == "binary":
        ps = []
        for s in sets:
            m = (D.set == s).to_numpy(); a, b_ = m & (f > 0), m & (f == 0)
            if a.sum() >= 2: ps.append(np.average(Y["e_gih_A"][a], weights=W[a]) - np.average(Y["e_gih_A"][b_], weights=W[b_]))
        r["sets_same_sign"] = int((np.sign(ps) == np.sign(raw[0])).sum()); r["sets"] = len(ps)
        x = D[f > 0].nlargest(3, "est") if c[0] > 0 else D[f > 0].nsmallest(3, "est")
        r["examples"] = "; ".join(f"{a} {b}({e:+.1f})" for a, b, e in zip(x.set, x.card_name, x.est))
    return r
rows = []
C5 = {"removal": ["KD", "KX", "DM", "DA", "MS", "BN", "TP", "FT", "ED", "CS", "PA", "SW"], "card flow": ["DR", "SC", "RC", "TU", "IM", "TK", "CL"],
      "stats": ["PC", "PT", "PP", "AN", "CP", "EQ"], "keywords": ["FL", "MN", "FS", "DT", "LL", "HS", "VG", "RH", "IN", "FH"],
      "opponent": ["DS", "ST", "MI", "DL", "TX"], "mana": ["RM", "FX", "CR", "SK", "CY"],
      "triggers/shape": ["ET", "AT", "DY", "UP", "SP", "LD", "SA", "CH", "KC", "RE"], "risk": ["SE", "DW", "CD", "RN", "SD"]}
for g, tags in C5.items():
    for tname in tags:
        v = D["c5_" + tname].fillna(0)
        if (v > 0).sum() >= 25: rows.append(one("c5_" + tname, v > 0, group="C5 " + g))
        if (v >= 2).sum() >= 25 and (v == 1).sum() >= 25: rows.append(one("c5_" + tname + "=2 (main)", v >= 2, group="C5 " + g + " level2"))
for c in ("c5_RATE", "c5_CLK", "c5_BLK", "c5_ntags", "c4_DMG", "c4_TGT", "c4_SPD", "c4_SWG", "c4_EVA", "c4_TURN", "c4_DEAD", "c4_SCALE", "c4_TEMPO", "c4_VULN", "c4_STACK", "c4_SYNO", "c4_DRAIN", "c4_MANA", "x_words", "x_ntarget"):
    v = D[c].fillna(0).to_numpy(float); rows.append(one(c + " (per SD)", (v - v.mean()) / v.std(), kind="numeric", group="scales"))
for c in [k for k in D.columns if k.startswith("c4_role_")]:
    if (D[c] > 0).sum() >= 25: rows.append(one(c, D[c] > 0, group="C4 role"))
for c, skip in (("is_creature", ("type",)), ("is_instant", ("type",)), ("is_sorcery", ("type",)), ("is_artifact", ("type",)), ("is_enchantment", ("type",)), ("is_aura", ()), ("is_equipment", ()),
                ("is_vehicle", ()), ("is_saga", ()), ("is_legendary", ()), ("col_W", ("colour",)), ("col_U", ("colour",)), ("col_B", ("colour",)), ("col_R", ("colour",)), ("col_G", ("colour",)),
                ("col_multi", ()), ("col_none", ("colour",))):
    if D[c].sum() >= 25: rows.append(one(c, D[c], skip=skip, group="type/colour"))
for r_, lab in ((0, "common"), (1, "uncommon"), (2, "rare"), (3, "mythic")): rows.append(one("rarity_" + lab, D.rar == r_, skip=("rarity",), group="type/colour"))
for c in [k for k in D.columns if k.startswith("x_") and k not in ("x_words", "x_ntarget")]:
    if D[c].sum() >= 25: rows.append(one(c, D[c], group="text"))
cr = D.is_creature.to_numpy()
for lab, m in (("creature mv<=2", cr & (D.mv <= 2)), ("creature mv 3-4", cr & D.mv.between(3, 4)), ("creature mv>=5", cr & (D.mv >= 5)), ("creature power>=4", cr & (D.power >= 4)),
               ("creature tough>=4 & power<=2", cr & (D.tough >= 4) & (D.power <= 2)), ("creature power>tough", cr & (D.power > D.tough)), ("noncreature mv<=2", ~cr & (D.mv <= 2)), ("noncreature mv>=5", ~cr & (D.mv >= 5))):
    rows.append(one(lab, m, skip=("mv",), group="body/cost"))
R = pd.DataFrame(rows)
p = R.p.to_numpy(); o = np.argsort(p); q = np.empty(len(p)); q[o] = np.minimum.accumulate((p[o] * len(p) / np.arange(1, len(p) + 1))[::-1])[::-1]; R["q"] = np.minimum(q, 1)
R["replicates"] = (np.sign(R.h0) == np.sign(R.ctrl)) & (np.sign(R.h1) == np.sign(R.ctrl)) & (np.sign(R.sets_a) == np.sign(R.ctrl)) & (np.sign(R.sets_b) == np.sign(R.ctrl))
R.to_csv(OUT / "effects_all.csv", index=False)
show = ["feature", "n", "raw", "ctrl", "ctrl_se", "q", "h0", "h1", "sets_a", "sets_b", "sets_same_sign", "sets", "gns", "iwd", "vsN", "rate_diff", "replicates"]
say(f"\nfeatures tested: {len(R)}; q < 0.05: {(R.q < .05).sum()}; q < 0.10: {(R.q < .10).sum()}; of q<0.05, replicate in both halves and both set groups: {(R[R.q < .05].replicates).sum()}")
for g, x in R.groupby("group", sort=False):
    say(f"\n--- {g}"); say(x.sort_values("ctrl", ascending=False)[show].round(3).to_string(index=False))
say("\n=== strongest (q < 0.05), sorted by controlled difference; with example cards")
S = R[R.q < .05].sort_values("ctrl", ascending=False)
say(S[["group", "feature", "n", "ctrl", "ctrl_se", "q", "gns", "iwd", "vsN", "replicates", "examples"]].round(3).to_string(index=False))

# ---------- level profiles for the ordinal scales
say("\n=== level profiles (weighted mean of the difference, controlled for nothing; n)")
for c in ("c5_RATE", "c5_CLK", "c5_BLK", "c4_SPD", "c4_DMG", "c4_TGT", "c4_TURN", "c4_DEAD", "c4_SCALE", "c4_TEMPO", "c4_VULN", "c4_STACK", "c4_SYNO", "c4_EVA", "c4_SWG"):
    x = D.groupby(D[c].fillna(0).astype(int)).apply(lambda y: pd.Series({"n": len(y), "mean": np.average(y.e_gih_A, weights=y.w)}))
    say(f"{c}: " + "  ".join(f"{int(k)}: {v['mean']:+.2f} (n {int(v['n'])})" for k, v in x.iterrows()))

# ---------- joint model: how much of the true difference do the tags explain? (leave one set out)
from numpy.linalg import solve
feat_basic = np.column_stack([CTRL["colour"], CTRL["type"], CTRL["rarity"], CTRL["mv"]])
c5cols = [c for c in D.columns if c.startswith("c5_") and c not in ("c5_ntags", "c5_nlvl2", "c5_ngroups")]; c4cols = [c for c in D.columns if c.startswith("c4_")]
xcols = [c for c in D.columns if c.startswith("x_")]
def loso(Xf, lam):
    Xf = np.column_stack([np.ones(len(D)), (Xf - Xf.mean(0)) / (Xf.std(0) + 1e-9)]); pred = np.zeros(len(D))
    for k in range(G):
        tr = sidx != k; A = (Xf[tr].T * W[tr]) @ Xf[tr] + lam * np.eye(Xf.shape[1]); A[0, 0] -= lam
        pred[~tr] = Xf[~tr] @ solve(A, (Xf[tr].T * W[tr]) @ Y["e_gih_A"][tr])
    pc = pred - pd.Series(pred).groupby(sidx).transform("mean").to_numpy()
    cov = np.cov(pc, Y["e_gih_A"])[0, 1]; tv = np.cov(Y["e0_gih_A"], Y["e1_gih_A"])[0, 1]
    per = [np.corrcoef(pc[sidx == k], Y["e_gih_A"][sidx == k])[0, 1] for k in range(G)]
    return cov ** 2 / (pc.var() * tv), np.corrcoef(pc, Y["e_gih_A"])[0, 1], int((np.array(per) > 0).sum())
say("\n=== joint model, leave-one-set-out: share of the TRUE top-specific variance explained (and correlation with the noisy observed difference; sets with positive correlation)")
for lab, Xf, lam in (("colour + type + rarity + mana value", feat_basic, 50), ("+ C5 tags", np.column_stack([feat_basic, D[c5cols].fillna(0)]), 300),
                     ("+ C5 + C4", np.column_stack([feat_basic, D[c5cols].fillna(0), D[c4cols].fillna(0)]), 300),
                     ("+ C5 + C4 + text features", np.column_stack([feat_basic, D[c5cols].fillna(0), D[c4cols].fillna(0), D[xcols].astype(float).fillna(0)]), 500)):
    a, b, c = loso(Xf.astype(float), lam); say(f"  {lab:38s} true variance explained {a:.3f}, observed correlation {b:.3f}, sets positive {c}/{G}")

# ---------- enrichment among the extreme cards
say("\n=== what the extreme cards have in common (top / bottom 5% by shrunk estimate, share with the feature vs all cards)")
hi = D.est >= D.est.quantile(.95); lo = D.est <= D.est.quantile(.05)
en = []
for f in R[R.kind == "binary"].feature:
    col = f.replace("=2 (main)", ""); 
    if col not in D.columns: continue
    v = (D[col].fillna(0) >= 2) if "=2" in f else (D[col].fillna(0) > 0)
    en.append(dict(feature=f, all=v.mean(), top5=v[hi].mean(), bottom5=v[lo].mean()))
en = pd.DataFrame(en); en["lift_top"] = en.top5 / en["all"]; en["lift_bottom"] = en.bottom5 / en["all"]
en = en[en["all"] >= 0.02]; en.to_csv(OUT / "enrichment.csv", index=False)
say("more common among cards top players use better:"); say(en.nlargest(15, "lift_top").round(3).to_string(index=False))
say("more common among cards top players use worse:"); say(en.nlargest(15, "lift_bottom").round(3).to_string(index=False))
(OUT / "report.txt").write_text("\n".join(lines))
D[["set", "card_name", "type", "mv", "colors", "rar", "e_gih_A", "est", "e_gns_A", "e_iwd_A", "e_gih_N", "T_gih_g", "text"]].to_csv(OUT / "cards_est.csv.gz", index=False)
