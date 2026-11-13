"""TP3: skill correction for top-player GIH WR. Pre-registered in PLAN.md (rules S1-S3, B).
  python3 tp3.py loso <cards.csv.gz from effects/build.py> <oof_B11g.csv.gz> <out dir>
Library functions (features, fit, base) are reused by freeze.py and score.py."""
import json, re, sys, warnings
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import spearmanr
warnings.filterwarnings("ignore")

LOOT = r"draw (?:a|two|\w+) cards?,? then discard|discard a card, then draw|discard a card\. If you do, draw"
DISCARD = r"discard (?:a|two|your)"
C5_SCALES = ["c5_RATE", "c5_CLK", "c5_BLK"]


def raw_features(df):
    """Derived columns from the raw card columns (type, text, mv, colors, rar, c5_*, c4_*). Same definitions for every set."""
    t = df["type"].fillna("").astype(str); txt = df["text"].fillna("").astype(str); col = df["colors"].fillna("").astype(str).replace("nan", "")
    f = pd.DataFrame(index=df.index)
    f["tagged"] = df["c5_RATE"].notna() & df["type"].notna()
    f["land"] = t.str.contains("Land") & ~t.str.contains("Creature")
    f["use"] = f.tagged & ~f.land
    for k in "WUBRG": f["col_" + k] = col.str.contains(k).astype(float)
    f["creature"] = t.str.contains("Creature").astype(float); f["instant"] = t.str.contains("Instant").astype(float); f["sorcery"] = t.str.contains("Sorcery").astype(float)
    f["mv"] = pd.to_numeric(df["mv"], errors="coerce").clip(0, 8)
    f["rar"] = pd.to_numeric(df["rar"], errors="coerce").fillna(1).clip(0, 3).astype(int)
    c5 = lambda k: pd.to_numeric(df["c5_" + k], errors="coerce").fillna(0)
    f["RM"] = (c5("RM") > 0).astype(float); f["FX"] = (c5("FX") > 0).astype(float)
    f["LOOT"] = (txt.str.contains(LOOT, case=False, regex=True) | txt.str.contains(DISCARD, case=False, regex=True)).astype(float)
    f["RC2"] = (c5("RC") >= 2).astype(float); f["RE2"] = (c5("RE") >= 2).astype(float); f["EQ"] = (c5("EQ") > 0).astype(float)
    f["HS2"] = (c5("HS") >= 2).astype(float); f["IN"] = (c5("IN") > 0).astype(float); f["BIG"] = ((f.creature > 0) & (f.mv >= 5)).astype(float)
    return f


TP3_COLS = ["col_U", "col_G", "creature", "instant", "sorcery", "RM", "FX", "LOOT", "RC2", "RE2", "EQ", "HS2", "IN", "BIG"]


def tag_columns(df):
    c5 = sorted(c for c in df.columns if re.fullmatch(r"c5_[A-Z]{2}", c)) + C5_SCALES
    c4 = sorted(c for c in df.columns if c.startswith("c4_"))
    return c5, c4


def design(df, f, arm, ref=None):
    """Feature matrix for an arm. ref = dict of training statistics (mv median, tag columns, mean/sd) made on the training rows."""
    if arm == "TP3":
        return f[TP3_COLS].to_numpy(float), ref or {}
    ref = dict(ref or {})
    if "mv_med" not in ref: ref["mv_med"] = float(f.mv.median())
    base = np.column_stack([f[["col_W", "col_U", "col_B", "col_R", "col_G", "creature", "instant", "sorcery"]].to_numpy(float),
                            (f.rar == 1).to_numpy(float), (f.rar == 2).to_numpy(float), (f.rar == 3).to_numpy(float), f.mv.fillna(ref["mv_med"]).to_numpy(float)])
    if arm == "TP3basic":
        return base, ref
    if "tagcols" not in ref: ref["tagcols"] = sum(tag_columns(df), [])
    tags = np.column_stack([pd.to_numeric(df[c], errors="coerce").fillna(0).to_numpy(float) if c in df.columns else np.zeros(len(df)) for c in ref["tagcols"]])
    X = np.column_stack([base, tags])
    if "mu" not in ref: ref["mu"] = X.mean(0); ref["sd"] = X.std(0) + 1e-9
    return (X - ref["mu"]) / ref["sd"], ref


RIDGE = {"TP3": 0.0, "TP3basic": 0.0, "TP3all": 300.0}


def fit(df, f, y, w, arm):
    """Weighted least squares (ridge for TP3all) on tagged nonland cards. Returns a model dict."""
    m = f.use.to_numpy() & np.isfinite(y)
    X, ref = design(df[m], f[m], arm)
    X1 = np.column_stack([np.ones(len(X)), X]); ww = w[m]
    A = (X1.T * ww) @ X1; lam = RIDGE[arm]
    if lam: P = lam * np.eye(X1.shape[1]); P[0, 0] = 0; A = A + P
    beta = np.linalg.solve(A, (X1.T * ww) @ y[m])
    return {"arm": arm, "beta": beta, "ref": ref}


def predict(model, df, f):
    """Correction (pp) per card: model value for tagged nonland cards, 0 for the rest; not yet centred."""
    X, _ = design(df, f, model["arm"], model["ref"])
    p = np.column_stack([np.ones(len(X)), X]) @ model["beta"]
    return np.where(f.use.to_numpy(), p, 0.0)


def tau2(df):
    z = df.dropna(subset=["e0_gih_A", "e1_gih_A"]); return float(np.cov(z.e0_gih_A, z.e1_gih_A)[0, 1])


def centre(x, g): return x - pd.Series(x).groupby(np.asarray(g)).transform("mean").to_numpy()


def logit(p): return np.log(p / (1 - p))


def base_params(tr):
    """k (linear) and c (log-odds shift) from training cards that have an overall prediction. tr: set, top (pp), overall actual (pp), pred (pp)."""
    pc = centre(tr.pred.to_numpy(), tr.set); tc = centre(tr.top.to_numpy(), tr.set)
    k = float((pc * tc).sum() / (pc ** 2).sum()); c = float((logit(tr.top / 100) - logit(tr.overall / 100)).mean())
    return k, c


def base_predict(pred_pp, sets, k, c):
    pk = k * centre(np.asarray(pred_pp, float), sets)
    pl = centre(100 / (1 + np.exp(-(logit(np.asarray(pred_pp, float) / 100) + c))), sets)
    return pk, pl


def load(cards_path):
    E = pd.read_csv(cards_path, low_memory=False)
    return E, raw_features(E)


def share(pred_c, r, t2):
    c = np.cov(pred_c, r)[0, 1]; v = pred_c.var()
    return float(np.sign(c) * c * c / (v * t2)) if v > 0 else 0.0


def loso(cards_path, oof_path, out):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    E, F = load(cards_path); sets = sorted(E.set.unique()); y = E.e_gih_A.to_numpy(float); v = E.v_A.to_numpy(float)
    arms = ["TP3", "TP3basic", "TP3all"]; P = {a: np.zeros(len(E)) for a in arms}
    for s in sets:
        tr = (E.set != s).to_numpy(); te = ~tr
        t2 = tau2(E[tr & F.use.to_numpy()]); w = 1 / (v + t2)
        for a in arms:
            m = fit(E[tr], F[tr], y[tr], w[tr], a); P[a][te] = predict(m, E[te], F[te])
    for a in arms: P[a] = centre(P[a], E.set)
    use = F.use.to_numpy()
    def metrics(p, mask):
        t2 = tau2(E[mask]); pc = centre(p[mask], E.set[mask]); r = y[mask]
        per = [np.corrcoef(pc[(E.set[mask] == s).to_numpy()], r[(E.set[mask] == s).to_numpy()])[0, 1] for s in sets]
        slope = float(np.cov(pc, r)[0, 1] / pc.var()) if pc.var() > 0 else float("nan")
        return {"share": share(pc, r, t2), "obs_corr": float(np.corrcoef(pc, r)[0, 1]), "sets_positive": int(np.sum(np.array(per) > 0)), "sets": len(sets),
                "min_set_corr": float(np.min(per)), "calibration_slope": slope, "pred_sd": float(pc.std()), "tau2": t2, "cards": int(mask.sum()),
                "share_half0": share(pc, E.e0_gih_A.to_numpy(float)[mask], t2), "share_half1": share(pc, E.e1_gih_A.to_numpy(float)[mask], t2), "per_set_corr": dict(zip(sets, np.round(per, 4).tolist()))}
    allm = np.ones(len(E), bool)
    res = {"population_all": {a: metrics(P[a], allm) for a in arms}, "population_tagged_nonland": {a: metrics(P[a], use) for a in arms}}
    # shuffled control (TP3): permute r within set in the training data
    sh = []
    for seed in range(20261113, 20261133):
        rng = np.random.default_rng(seed); ys = y.copy()
        for s in sets:
            idx = np.where((E.set == s).to_numpy() & use)[0]; ys[idx] = ys[rng.permutation(idx)]
        p = np.zeros(len(E))
        for s in sets:
            tr = (E.set != s).to_numpy(); te = ~tr; t2 = tau2(E[tr & use]); w = 1 / (v + t2)
            p[te] = predict(fit(E[tr], F[tr], ys[tr], w[tr], "TP3"), E[te], F[te])
        p = centre(p, E.set); sh.append(share(p, y, tau2(E)))
    res["shuffled_TP3_share"] = {"max": float(np.max(sh)), "mean": float(np.mean(sh)), "values": np.round(sh, 4).tolist()}
    # ---- combination with the base (cards matched to the overall OOF prediction)
    o = pd.read_csv(oof_path); o["card_name"] = o.name.astype(str).str.split(" // ").str[0]; o = o.drop_duplicates(["set", "card_name"])
    Mx = E[["set", "card_name", "T_gih"]].assign(row=np.arange(len(E))).merge(o[["set", "card_name", "pred", "actual_gih"]], on=["set", "card_name"], how="inner")
    Mx["top"] = Mx.T_gih; Mx["overall"] = 100 * Mx.actual_gih; Mx["pred"] = 100 * Mx.pred
    tc = centre(Mx.top.to_numpy(), Mx.set); rows = []
    PK = np.zeros(len(Mx)); PL = np.zeros(len(Mx)); ks = {}
    for s in sets:
        tr = (Mx.set != s).to_numpy(); te = ~tr; k, c = base_params(Mx[tr]); ks[s] = (k, c)
        pk, pl = base_predict(Mx.pred[te], Mx.set[te], k, c); PK[te] = pk; PL[te] = pl
    C = {a: centre(P[a][Mx.row.to_numpy()], Mx.set) for a in arms}
    combos = {"TP0K": PK, "TP0L": PL, "TP0K+TP3": PK + C["TP3"], "TP0L+TP3": PL + C["TP3"], "TP0K+TP3basic": PK + C["TP3basic"], "TP0K+TP3all": PK + C["TP3all"]}
    per = {n: {"mae": [], "sp": []} for n in combos}
    for s in sets:
        m = (Mx.set == s).to_numpy()
        for n, p in combos.items():
            per[n]["mae"].append(float(np.abs(p[m] - tc[m]).mean())); per[n]["sp"].append(float(spearmanr(p[m], tc[m])[0]))
    res["base"] = {"matched_cards": len(Mx), "k_mean": float(np.mean([a for a, _ in ks.values()])), "c_mean": float(np.mean([b for _, b in ks.values()])),
                   "arms": {n: {"mae": float(np.mean(d["mae"])), "spearman": float(np.mean(d["sp"])), "sets_better_than_TP0K": int(np.sum(np.array(d["mae"]) < np.array(per["TP0K"]["mae"])))} for n, d in per.items()},
                   "per_set_mae": {n: dict(zip(sets, np.round(d["mae"], 4).tolist())) for n, d in per.items()}}
    a = res["population_all"]["TP3"]
    res["rules"] = {"S1": {"share>=0.15": a["share"] >= 0.15, "sets_positive>=17": a["sets_positive"] >= 17, "above_shuffled_max": a["share"] > res["shuffled_TP3_share"]["max"]},
                    "S2_TP3_minus_basic": a["share"] - res["population_all"]["TP3basic"]["share"], "S2_TP3_minus_all": a["share"] - res["population_all"]["TP3all"]["share"],
                    "S3": {"mae_lower": res["base"]["arms"]["TP0K+TP3"]["mae"] < res["base"]["arms"]["TP0K"]["mae"], "sets>=14": res["base"]["arms"]["TP0K+TP3"]["sets_better_than_TP0K"] >= 14}}
    res["rules"]["S1_supported"] = bool(all(res["rules"]["S1"].values())); res["rules"]["S3_supported"] = bool(all(res["rules"]["S3"].values()))
    (out / "loso.json").write_text(json.dumps(res, indent=1, default=lambda x: bool(x) if isinstance(x, np.bool_) else float(x)))
    pd.DataFrame({"set": E.set, "card_name": E.card_name, "r": y, "TP3": P["TP3"], "TP3basic": P["TP3basic"], "TP3all": P["TP3all"], "use": use}).to_csv(out / "loso_oof.csv.gz", index=False)
    full = fit(E, F, y, 1 / (v + tau2(E[use])), "TP3")
    print(json.dumps({k: res[k] for k in ("rules", "shuffled_TP3_share")}, indent=1, default=str))
    for pop in ("population_all", "population_tagged_nonland"):
        print(pop); print(pd.DataFrame(res[pop]).T.drop(columns="per_set_corr").round(3).to_string())
    print("base"); print(pd.DataFrame(res["base"]["arms"]).T.round(4).to_string(), "| matched", len(Mx), "k", round(res["base"]["k_mean"], 3), "c", round(res["base"]["c_mean"], 3))
    print("TP3 coefficients on all 23 sets (pp):"); print(pd.Series(full["beta"], index=["intercept"] + TP3_COLS).round(3).to_string())


if __name__ == "__main__":
    if sys.argv[1] == "loso": loso(*sys.argv[2:5])
