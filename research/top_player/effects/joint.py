"""Joint model of the main features (do they hold together, or stand in for each other?) and spot checks of the tags (exploratory).
Usage: python3 joint.py <cards.csv.gz>"""
import sys, warnings
import numpy as np, pandas as pd
from scipy import stats
warnings.filterwarnings("ignore")
E = pd.read_csv(sys.argv[1], low_memory=False); pd.set_option("display.width", 250); pd.set_option("display.max_colwidth", 150)
TAU2 = float(np.cov(E.e0_gih_A, E.e1_gih_A)[0, 1]); E["w"] = 1 / (E.v_A + TAU2); E["est"] = E.e_gih_A * TAU2 / (TAU2 + E.v_A)
D = E[E.tagged & ~E.is_land.astype(bool)].copy().reset_index(drop=True)
for c in D.columns:
    if D[c].dtype == object and set(D[c].dropna().unique()) <= {"True", "False", True, False}: D[c] = D[c].astype(str).eq("True")
sets = sorted(D.set.unique()); G = len(sets); sidx = D.set.map({s: i for i, s in enumerate(sets)}).to_numpy(); SETFE = np.eye(G)[sidx]
cr = D.is_creature.to_numpy(bool); D["rar"] = D.rar.fillna(1).clip(0, 3).astype(int)
F = {"blue": D.col_U, "green": D.col_G, "white": D.col_W, "red": D.col_R, "black": D.col_B,
     "instant": D.is_instant, "sorcery": D.is_sorcery, "noncreature permanent": ~cr & ~D.is_instant & ~D.is_sorcery,
     "uncommon": D.rar == 1, "rare": D.rar == 2, "mythic": D.rar == 3,
     "ramp / mana ability (RM)": D.c5_RM > 0, "fixing / land search (FX)": D.c5_FX > 0, "cycling (CY)": D.c5_CY > 0, "treasure": D.x_treasure,
     "loot or discard as a cost": D.x_loot | D.x_discard_self, "selection: scry / surveil / loot (SC)": D.c5_SC > 0, "draw (DR)": D.c5_DR > 0,
     "recursion, main (RC2)": D.c5_RC >= 2, "reuse from graveyard, main (RE2)": D.c5_RE >= 2, "lifelink (LL)": D.c5_LL > 0, "flash (FH)": D.c5_FH > 0,
     "counterspell (CS)": D.c5_CS > 0, "bounce (BN)": D.c5_BN > 0, "kill spell (KD)": D.c5_KD > 0, "damage removal (DM)": D.c5_DM > 0,
     "tap ability {T}:": D.x_tap_ability & ~(D.c5_RM > 0), "optional effect (you may)": D.x_you_may,
     "equipment / aura bonus (EQ)": D.c5_EQ > 0, "haste, main (HS2)": D.c5_HS >= 2, "menace / trample (MN)": D.c5_MN > 0, "flying (FL)": D.c5_FL > 0,
     "hexproof / indestructible / ward (IN)": D.c5_IN > 0, "temporary pump (PT)": D.c5_PT > 0, "role: trick / protection": D.c4_role_T > 0,
     "creature mv<=2": cr & (D.mv <= 2), "creature mv>=5": cr & (D.mv >= 5), "creature power>=4": cr & (D.power >= 4), "clue / investigate (3 sets)": D.x_clue}
names = list(F); X = np.column_stack([np.asarray(F[k], float) for k in names] + [D.c5_CLK.fillna(0).to_numpy(float), SETFE]); names2 = names + ["pressure CLK (per level)"]
def fit(y, w):
    ok = np.isfinite(y); Xo, yo, wo, g = X[ok], y[ok], w[ok], sidx[ok]
    XtW = Xo.T * wo; A = np.linalg.pinv(XtW @ Xo); b = A @ (XtW @ yo); u = yo - Xo @ b; meat = np.zeros((Xo.shape[1],) * 2)
    for k in np.unique(g):
        m = g == k; s = (Xo[m].T * (wo[m] * u[m])).sum(1); meat += np.outer(s, s)
    V = A @ meat @ A * (G / (G - 1)); se = np.sqrt(np.diag(V)); return b, se
W = D.w.to_numpy(float)
b, se = fit(D.e_gih_A.to_numpy(float), W); bi, sei = fit(D.e_iwd_A.to_numpy(float), W); bg, seg = fit(D.e_gns_A.to_numpy(float), W); bn, sen = fit(D.e_gih_N.to_numpy(float), W)
k = len(names2)
T = pd.DataFrame({"feature": names2, "n": [int(np.asarray(F[x]).sum()) for x in names] + [len(D)], "GIH": b[:k], "se": se[:k], "t": b[:k] / se[:k], "IWD": bi[:k], "t_iwd": bi[:k] / sei[:k], "GNS": bg[:k], "t_gns": bg[:k] / seg[:k], "vs normal": bn[:k], "t_n": bn[:k] / sen[:k]})
print("=== joint model (all features together + set fixed effects; baseline = common creature, none of the listed features)")
print(T.round(2).to_string(index=False)); T.to_csv(sys.argv[2], index=False)
print("\n=== spot checks of the text features (random cards)")
rng = np.random.default_rng(1)
for c in ("x_loot", "x_discard_self", "x_tap_ability", "x_you_may"):
    s = D[D[c]].sample(4, random_state=3); print(c, "n", int(D[c].sum()))
    for _, r in s.iterrows(): print("   ", r.set, r.card_name, "|", str(r.text).replace("\n", " / ")[:140])
for c in ("c5_RM", "c5_FX", "c5_EQ", "c5_IN", "c5_RC", "c5_RE"):
    s = D[D[c] >= 2].sample(3, random_state=4); print(c + "=2", "n", int((D[c] >= 2).sum()))
    for _, r in s.iterrows(): print("   ", r.set, r.card_name, "|", str(r.type)[:25], "|", str(r.text).replace("\n", " / ")[:120])
print("agreement: c5_LL vs text lifelink", pd.crosstab(D.c5_LL > 0, D.x_lifelink).to_numpy().tolist(), "| c5_FH vs text flash", pd.crosstab(D.c5_FH > 0, D.x_flash).to_numpy().tolist(), "| c5_FL vs text flying", pd.crosstab(D.c5_FL > 0, D.x_flying).to_numpy().tolist())
print("\n=== cards with the largest estimated difference (shrunk), both directions")
cols = ["set", "card_name", "type", "mv", "colors", "est", "e_gih_A", "T_gih_g"]
print(D.nlargest(25, "est")[cols].round(2).to_string(index=False)); print(D.nsmallest(25, "est")[cols].round(2).to_string(index=False))
