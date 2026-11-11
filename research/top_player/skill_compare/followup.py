"""Follow-up checks for the reasons (exploratory). Usage: python3 followup.py <data dir> <card_meta.csv.gz> <analyze out dir>"""
import sys, glob
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import spearmanr
D, META, OUT = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
sets = sorted(Path(f).name.split("_")[0] for f in glob.glob(str(D / "*_cards.csv.gz")))
C = pd.concat([pd.read_csv(D / f"{s}_cards.csv.gz", dtype={"half": str, "period": str}) for s in sets], ignore_index=True)
M = ["pool_g", "deck_g", "deck_w", "copies", "oh_g", "oh_w", "gd_g", "gd_w", "gih_g", "gih_w", "gns_g", "gns_w"]
G = {"L": ["L"], "B1": ["B1"], "N": ["B2", "B3"], "T": ["B4", "B5"], "B5": ["B5"]}
INFL = 0.958  # empirical / binomial noise ratio measured with the draft-id halves (top_specific_tail.py)
def agg(grps, half=None, period=None):
    x = C[C.grp.isin(grps)]
    if half: x = x[x.half == half]
    if period: x = x[x.period == period]
    return x.groupby(["set", "card_name"])[M].sum()
A = {g: agg(v) for g, v in G.items()}
site = pd.read_csv(D / "site_groups.csv.gz").rename(columns={"name": "card_name"}).drop_duplicates(["set", "group", "card_name"])
SG = {g: site[site.group == g].set_index(["set", "card_name"]).rename(columns={"ever_drawn_game_count": "gih_g"}).assign(gih_w=lambda z: z.ever_drawn_win_rate * z.gih_g)[["gih_g", "gih_w"]] for g in site.group.unique()}
logit = lambda p: np.log(p / (1 - p))

print("=== A. compression with measurement noise removed (binomial x %.3f), and on the log-odds scale" % INFL)
def comp(Xa, Xb, lab, mn=500):
    rows = []
    for s in sets:
        try: j = Xa.loc[s][["gih_g", "gih_w"]].join(Xb.loc[s][["gih_g", "gih_w"]], lsuffix="_a", rsuffix="_b").dropna()
        except KeyError: continue
        j = j[(j.gih_g_a >= mn) & (j.gih_g_b >= mn)]
        if len(j) < 30: continue
        pa, pb = j.gih_w_a / j.gih_g_a, j.gih_w_b / j.gih_g_b
        na, nb = INFL * pa * (1 - pa) / j.gih_g_a, INFL * pb * (1 - pb) / j.gih_g_b
        va, vb = pa.var() - na.mean(), pb.var() - nb.mean(); cv = np.cov(pa, pb)[0, 1]
        la, lb = logit(pa), logit(pb)
        nla, nlb = na / (pa * (1 - pa)) ** 2, nb / (pb * (1 - pb)) ** 2
        lva, lvb = la.var() - nla.mean(), lb.var() - nlb.mean(); lcv = np.cov(la, lb)[0, 1]
        rows.append(dict(set=s, n=len(j), gap_pp=100 * (pa.mean() - pb.mean()), true_sd_ratio=np.sqrt(va / vb), true_slope=cv / vb, true_corr=cv / np.sqrt(va * vb),
                         logit_true_sd_ratio=np.sqrt(lva / lvb), logit_true_slope=lcv / lvb, rel_a=va / pa.var(), rel_b=vb / pb.var()))
    r = pd.DataFrame(rows); m = r.mean(numeric_only=True)
    print(f"  {lab:38s} sets {len(r)} cards {m.n:.0f} gap {m.gap_pp:+.2f}pp | pp scale: true SD ratio {m.true_sd_ratio:.3f}, true slope {m.true_slope:.3f}, true corr {m.true_corr:.3f}"
          f" | log-odds scale: true SD ratio {m.logit_true_sd_ratio:.3f}, slope {m.logit_true_slope:.3f} (sets with log-odds slope < 1: {(r.logit_true_slope < 1).sum()}/{len(r)}) | reliability a {m.rel_a:.2f} b {m.rel_b:.2f}")
    return r
outA = {}
for lab, a, b in (("public T vs N", A["T"], A["N"]), ("public B5 vs N", A["B5"], A["N"]), ("public B1 vs N", A["B1"], A["N"]), ("public L vs N", A["L"], A["N"]),
                  ("site top vs middle", SG["top"], SG["middle"]), ("site top vs bottom", SG["top"], SG["bottom"]), ("site middle vs bottom", SG["middle"], SG["bottom"])):
    outA[lab] = comp(a, b, lab)
pd.concat({k: v for k, v in outA.items()}).to_csv(OUT / "followup_compression.csv")

print("\n=== B. blue: deck-level or card-level? (2-colour main decks, WR T - N by pair, pp)")
GM = pd.concat([pd.read_csv(D / f"{s}_games.csv.gz", dtype={"val": str}) for s in sets], ignore_index=True)
mc = GM[(GM.dim == "main_colors") & (GM.val.astype(str).str.len() == 2)]
rows = []
for s in sets:
    z = mc[mc.set == s]
    t = z[z.band.isin(G["T"])].groupby("val")[["games", "wins"]].sum(); n = z[z.band.isin(G["N"])].groupby("val")[["games", "wins"]].sum()
    d = (100 * t.wins / t.games - 100 * n.wins / n.games).rename("d").to_frame(); d["U"] = d.index.str.contains("U")
    for col in "WUBRG":
        rows.append(dict(set=s, colour=col, diff_with=d[d.index.str.contains(col)].d.mean(), diff_without=d[~d.index.str.contains(col)].d.mean()))
b = pd.DataFrame(rows); b["excess"] = b.diff_with - b.diff_without
print(b.groupby("colour").apply(lambda y: pd.Series(dict(T_minus_N_with=y.diff_with.mean(), T_minus_N_without=y.diff_without.mean(), excess=y.excess.mean(), sets_positive=int((y.excess > 0).sum()), sets=len(y)))).round(2).to_string())

print("\n=== C. card categories: deck-level part (GNS residual) and drawing part (IWD residual), with set consistency")
E = pd.read_csv(OUT / "card_resid_gih.csv")
rows = []
cats = {"blue": E.blue, "instant": E.is_instant, "sorcery": E.is_sorcery, "creature": E.is_creature, "equipment": E.is_equipment, "aura": E.is_aura, "common": E.rarity == 0, "rare+mythic": E.rarity >= 2}
for k, m in cats.items():
    x = E[m.fillna(False).astype(bool)]
    for col in ("e", "e_gns", "e_iwd"):
        ps = x.groupby("set")[col].mean(); se = ps.std() / np.sqrt(len(ps))
        rows.append(dict(category=k, measure={"e": "GIH", "e_gns": "GNS (deck)", "e_iwd": "IWD (drawing)"}[col], n=x[col].notna().sum(), mean=x[col].mean(), se_over_sets=se, t=x[col].mean() / se, sets_same_sign=int((np.sign(ps) == np.sign(x[col].mean())).sum()), sets=len(ps)))
r = pd.DataFrame(rows); print(r.round(3).to_string(index=False)); r.to_csv(OUT / "followup_categories.csv", index=False)

print("\n=== D. the maindeck-rate link, within blue and non-blue and by card strength")
E["rate_diff"] = E.deck_rate_T - E.deck_rate_N
for lab, m in (("all", E.rate_diff.notna()), ("blue", E.blue.fillna(False).astype(bool) & E.rate_diff.notna()), ("not blue", ~E.blue.fillna(False).astype(bool) & E.rate_diff.notna())):
    x = E[m]; r = x.groupby("set").apply(lambda y: spearmanr(y.e0, y.rate_diff)[0] if len(y) > 20 else np.nan)
    print(f"  {lab:9s} n {len(x)}: Spearman(half-0 residual, T-N maindeck-rate diff) per set mean {r.mean():.3f}, sets positive {(r > 0).sum()}/{r.notna().sum()}")
# does it hold after taking out the card's strength (normal players' GIH from the other half)?
x = E[E.rate_diff.notna()].copy()
x["rd_res"] = x.groupby("set", group_keys=False).apply(lambda y: y.rate_diff - np.polyval(np.polyfit(y.N0_c, y.rate_diff, 1), y.N0_c))
r = x.groupby("set").apply(lambda y: spearmanr(y.e0, y.rd_res)[0]); print(f"  rate diff with N strength (other half) removed: per set mean {r.mean():.3f}, positive {(r > 0).sum()}/{len(r)}")

print("\n=== E. stability over the format with set-specific slopes")
def per(g, p): return agg(G[g], period=p)
rows = []
for s in sets:
    try:
        x = pd.concat({f"{g}{p}": per(g, p).loc[s][["gih_g", "gih_w"]] for g in ("T", "N") for p in ("0", "1")}, axis=1)
    except KeyError: continue
    x.columns = [f"{a}_{b}" for a, b in x.columns]
    x = x[(x[[c for c in x if c.endswith("gih_g")]] >= 250).all(1)]
    r = lambda k: 100 * x[f"{k}_gih_w"] / x[f"{k}_gih_g"]
    out = {}
    for p in ("0", "1"):
        tc, nc = r(f"T{p}") - r(f"T{p}").mean(), r(f"N{p}") - r(f"N{p}").mean(); bb = np.polyfit(nc, tc, 1)[0]; out[p] = tc - bb * nc
    rows.append(dict(set=s, n=len(x), cov=np.cov(out["0"], out["1"])[0, 1]))
r = pd.DataFrame(rows); print(f"  covariance of the top-specific residual between days 0-13 and 14-27 (set-specific slopes): mean {r['cov'].mean():.3f}; positive in {(r['cov'] > 0).sum()}/{len(r)} sets")
