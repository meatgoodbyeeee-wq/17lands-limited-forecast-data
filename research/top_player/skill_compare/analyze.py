"""How do top players' results differ from everyone else's? Exploratory comparison on 23 past sets.
Inputs: research/top_player/skill_compare/data/ (<SET>_cards.csv.gz, <SET>_games.csv.gz, <SET>_sums.csv,
site_groups.csv.gz, card_scryfall.csv.gz) and card_meta.csv.gz. Writes CSVs to an output folder and prints a report.
Groups (public data, player win-rate bucket in this set, n >= 50 games unless L):
  N = "normal" = B2 + B3 (win rate 0.48-0.60), T = top = B4 + B5 (>= 0.60), B5 (>= 0.64), B1 (< 0.48), L (< 50 games).
Usage: python3 analyze.py <data dir> <card_meta.csv.gz> <out dir>"""
import sys, glob, json
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import pearsonr, spearmanr

D, META, OUT = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3]); OUT.mkdir(parents=True, exist_ok=True)
G = {"L": ["L"], "B1": ["B1"], "N": ["B2", "B3"], "B2": ["B2"], "B3": ["B3"], "T": ["B4", "B5"], "B4": ["B4"], "B5": ["B5"]}
ORDER = ["L", "B1", "B2", "B3", "B4", "B5"]
MIN = 500
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 40)
report_lines = []
def say(*a):
    s = " ".join(str(x) for x in a); print(s); report_lines.append(s)
def table(df, name, floatfmt=3):
    df.to_csv(OUT / f"{name}.csv", index=False); say(df.round(floatfmt).to_string(index=False))
def mean_sets(df, col):
    """mean over sets and the number of sets with the same sign as the mean"""
    v = df[col].dropna(); m = v.mean()
    return m, int((np.sign(v) == np.sign(m)).sum()), len(v)

sets = sorted(Path(f).name.split("_")[0] for f in glob.glob(str(D / "*_cards.csv.gz")))
say(f"sets with data: {len(sets)} {sets}")

# ---------------------------------------------------------------- card attributes
meta = pd.read_csv(META)
scry = pd.read_csv(D / "card_scryfall.csv.gz") if (D / "card_scryfall.csv.gz").exists() else pd.DataFrame(columns=["set", "name", "mv", "type_line", "colors"])
site = pd.read_csv(D / "site_groups.csv.gz") if (D / "site_groups.csv.gz").exists() else None
attr = meta.rename(columns={"name": "card_name"}).merge(scry.rename(columns={"name": "card_name", "mv": "mv_s", "type_line": "type_s", "colors": "col_s"})[["set", "card_name", "mv_s", "type_s", "col_s"]], on=["set", "card_name"], how="outer")
attr["type_line"] = attr.type_s.fillna(attr.type_line); attr["mv"] = attr.mv_s.fillna(attr.mv); attr["colors"] = attr.col_s.fillna(attr.colors)
if site is not None and "rarity" in site:
    rr = site[site.group == "all"][["set", "name", "rarity"]].rename(columns={"name": "card_name", "rarity": "rar_s"}).drop_duplicates(["set", "card_name"])
    attr = attr.merge(rr, on=["set", "card_name"], how="left")
    attr["rarity"] = attr.rar_s.map({"common": 0, "uncommon": 1, "rare": 2, "mythic": 3}).fillna(attr.rarity)
attr = attr.drop_duplicates(["set", "card_name"])
t = attr.type_line.fillna("")
attr["is_land"] = t.str.contains("Land") & ~t.str.contains("Creature")
attr["is_basic"] = t.str.contains("Basic")
attr["is_creature"] = t.str.contains("Creature")
attr["is_instant"] = t.str.contains("Instant"); attr["is_sorcery"] = t.str.contains("Sorcery")
attr["is_other"] = ~attr.is_land & ~attr.is_creature & ~attr.is_instant & ~attr.is_sorcery & t.ne("")
attr["is_equipment"] = t.str.contains("Equipment"); attr["is_aura"] = t.str.contains("Aura")
attr["known_type"] = t.ne("")
attr["blue"] = attr.colors.fillna("").astype(str).str.contains("U")

# ---------------------------------------------------------------- load card tables
C = pd.concat([pd.read_csv(D / f"{s}_cards.csv.gz", dtype={"half": str, "period": str}) for s in sets], ignore_index=True)
M = ["pool_g", "deck_g", "deck_w", "copies", "oh_g", "oh_w", "gd_g", "gd_w", "gih_g", "gih_w", "gns_g", "gns_w"]
def by_group(C, grp_list, half=None, period=None):
    x = C[C.grp.isin(grp_list)]
    if half is not None: x = x[x.half == half]
    if period is not None: x = x[x.period == period]
    return x.groupby(["set", "card_name"])[M].sum()
def rates(x):
    r = pd.DataFrame(index=x.index)
    with np.errstate(divide="ignore", invalid="ignore"):
        r["gih"] = 100 * x.gih_w / x.gih_g; r["oh"] = 100 * x.oh_w / x.oh_g; r["gd"] = 100 * x.gd_w / x.gd_g
        r["gns"] = 100 * x.gns_w / x.gns_g; r["gp"] = 100 * x.deck_w / x.deck_g; r["iwd"] = r.gih - r.gns
        r["deck_rate"] = x.deck_g / x.pool_g; r["copies_per_deck"] = x.copies / x.deck_g
    for k in ("gih_g", "gns_g", "oh_g", "gd_g", "pool_g", "deck_g"):
        r[k] = x[k]
    return r.replace([np.inf, -np.inf], np.nan)
R = {g: rates(by_group(C, v)) for g, v in G.items()}
Rh = {(g, h): rates(by_group(C, G[g], half=h)) for g in ("N", "T") for h in ("0", "1")}
Rp = {(g, p): rates(by_group(C, G[g], period=p)) for g in ("N", "T") for p in ("0", "1")}
for k in ("T500", "N500", "T50", "N50"):
    R[k] = rates(C[C.grp == k].groupby(["set", "card_name"])[M].sum())

# ---------------------------------------------------------------- 0. consistency with Case 6
say("\n=== 0. checks")
chk = []
for s in sets:
    f = Path("research/case6/data") / f"{s}_case6_28d.csv"
    if not f.exists(): continue
    c6 = pd.read_csv(f).set_index("card_name")
    tt = by_group(C[C.set == s], G["T"]).droplevel(0)
    j = c6.join(tt[["gih_g", "gih_w"]], how="inner")
    chk.append(dict(set=s, cards=len(j), top_games_equal=int((j.top60n50_games == j.gih_g).sum()), top_wins_equal=int((j.top60n50_wins == j.gih_w).sum())))
if chk: table(pd.DataFrame(chk), "check_case6", 0)
cov = attr[attr.set.isin(sets)]
say("type known for %.1f%% of cards in the attribute table" % (100 * cov.known_type.mean()))

# ---------------------------------------------------------------- 1. game-level outcomes by band
say("\n=== 1. games and win rate by group (mean over sets)")
GM = pd.concat([pd.read_csv(D / f"{s}_games.csv.gz", dtype={"val": str}) for s in sets], ignore_index=True)
def gsum(dim, val=None):
    x = GM[GM.dim == dim]
    if val is not None: x = x[x.val.astype(str) == str(val)]
    out = []
    for g, b in G.items():
        y = x[x.band.isin(b)].groupby("set")[["games", "wins"]].sum(); y["grp"] = g; out.append(y.reset_index())
    return pd.concat(out, ignore_index=True)
a = gsum("all")
tot = a[a.grp.isin(ORDER)].groupby("set").games.sum()
a["share"] = a.games / a.set.map(tot); a["wr"] = 100 * a.wins / a.games
table(a.groupby("grp")[["share", "wr"]].mean().reindex(list(G)).reset_index(), "games_by_group")
na = GM[(GM.dim == "all") & (GM.band == "NA")].games.sum()
say(f"games with n >= 50 but no win-rate bucket (excluded): {na}")

# ---------------------------------------------------------------- 2. selection on outcome and scale
say("\n=== 2. how much of the top-normal difference is built into the definition?")
def pair_stats(A, B, metric="gih", minA=MIN, minB=MIN, cnt="gih_g"):
    rows = []
    for s in sets:
        try:
            x = A.loc[s][[metric, cnt]].join(B.loc[s][[metric, cnt]], lsuffix="_a", rsuffix="_b").dropna()
        except KeyError:
            continue
        x = x[(x[cnt + "_a"] >= minA) & (x[cnt + "_b"] >= minB)]
        if len(x) < 30: continue
        ac, bc = x[metric + "_a"] - x[metric + "_a"].mean(), x[metric + "_b"] - x[metric + "_b"].mean()
        rows.append(dict(set=s, n=len(x), gap=x[metric + "_a"].mean() - x[metric + "_b"].mean(), slope=np.polyfit(bc, ac, 1)[0],
                         sd_ratio=ac.std() / bc.std(), spearman=spearmanr(x[metric + "_a"], x[metric + "_b"])[0]))
    return pd.DataFrame(rows)
rows = []
for lab, A, B in (("public: T vs N", R["T"], R["N"]), ("public: B5 vs N", R["B5"], R["N"]), ("public: B1 vs N", R["B1"], R["N"]),
                  ("public: L (<50 games) vs N", R["L"], R["N"]),
                  ("public heavy players (n>=500): T500 vs N500", R["T500"], R["N500"]), ("public light players (n 50-100): T50 vs N50", R["T50"], R["N50"])):
    p = pair_stats(A, B)
    if len(p): rows.append(dict(comparison=lab, sets=len(p), cards=p.n.mean(), gap=p.gap.mean(), slope=p.slope.mean(), sd_ratio=p.sd_ratio.mean(), spearman=p.spearman.mean()))
SG = {}
if site is not None:
    S = site.copy(); S["gih"] = 100 * S.ever_drawn_win_rate; S["gih_g"] = S.ever_drawn_game_count
    S = S.rename(columns={"name": "card_name"}).drop_duplicates(["set", "group", "card_name"]).set_index(["set", "card_name"])
    SG = {g: S[S.group == g][["gih", "gih_g"]] for g in S.group.unique()}
    for a_, b_ in (("top", "middle"), ("bottom", "middle"), ("top", "bottom"), ("top", "all")):
        if a_ in SG and b_ in SG:
            p = pair_stats(SG[a_], SG[b_])
            if len(p): rows.append(dict(comparison=f"site (all time): {a_} vs {b_}", sets=len(p), cards=p.n.mean(), gap=p.gap.mean(), slope=p.slope.mean(), sd_ratio=p.sd_ratio.mean(), spearman=p.spearman.mean()))
table(pd.DataFrame(rows), "selection_and_scale")
lg = []
for s in sets:
    wT = a[(a.set == s) & (a.grp == "T")].wr.iloc[0] / 100; wN = a[(a.set == s) & (a.grp == "N")].wr.iloc[0] / 100
    lg.append(dict(set=s, wr_T=wT, wr_N=wN, expected_slope=(wT * (1 - wT)) / (wN * (1 - wN))))
lg = pd.DataFrame(lg)
say("if a card's effect were the same in log-odds for everyone, the slope T on N would be p(1-p) ratio: mean %.3f (range %.3f-%.3f)" % (lg.expected_slope.mean(), lg.expected_slope.min(), lg.expected_slope.max()))
lg.to_csv(OUT / "logit_expectation.csv", index=False)

# ---------------------------------------------------------------- 3. game characteristics
say("\n=== 3. game characteristics by group (mean over sets)")
def share_wr(dim, vals, label):
    x = GM[GM.dim == dim]; out = []
    for g, b in G.items():
        y = x[x.band.isin(b)]
        for s, z in y.groupby("set"):
            tot_ = z.games.sum(); m = z.val.astype(str).isin([str(v) for v in vals])
            g1, g0 = z[m].games.sum(), z[~m].games.sum()
            out.append(dict(grp=g, set=s, share=g1 / tot_ if tot_ else np.nan, wr=100 * z[m].wins.sum() / g1 if g1 else np.nan,
                            wr_other=100 * z[~m].wins.sum() / g0 if g0 else np.nan))
    o = pd.DataFrame(out); o["wr_diff"] = o.wr - o.wr_other
    r = o.groupby("grp")[["share", "wr", "wr_other", "wr_diff"]].mean().reindex(list(G)).reset_index(); r.insert(0, "what", label)
    return r
parts = []
for dim, vals, lab in (("on_play", ["1"], "on the play"), ("mull", ["1", "2"], "mulliganed (me)"), ("opp_mull", ["1", "2"], "opponent mulliganed"),
                       ("n_main", ["1"], "mono-colour main"), ("n_main", ["3", "4", "5"], "3+ main colours"), ("splash", ["1"], "splash"),
                       ("turns", [str(i) for i in range(0, 8)], "game ends by turn 7"), ("turns", [str(i) for i in range(12, 21)], "game lasts 12+ turns")):
    if (GM.dim == dim).any():
        parts.append(share_wr(dim, vals, lab))
table(pd.concat(parts), "game_characteristics")
pd_rows = []
for s in sets:
    for g in ("N", "T"):
        row = dict(set=s, grp=g)
        x = GM[(GM.set == s) & (GM.dim == "on_play") & GM.band.isin(G[g])].groupby("val")[["games", "wins"]].sum(); x.index = x.index.astype(str)
        if {"0", "1"} <= set(x.index):
            row["play_adv"] = 100 * (x.loc["1", "wins"] / x.loc["1", "games"] - x.loc["0", "wins"] / x.loc["0", "games"])
        y = GM[(GM.set == s) & (GM.dim == "mull") & GM.band.isin(G[g])].groupby("val")[["games", "wins"]].sum(); y.index = y.index.astype(str)
        if {"0", "1"} <= set(y.index):
            row["mull_penalty"] = 100 * (y.loc["1", "wins"] / y.loc["1", "games"] - y.loc["0", "wins"] / y.loc["0", "games"])
        pd_rows.append(row)
pdr = pd.DataFrame(pd_rows).pivot(index="set", columns="grp")
for k, lab in (("play_adv", "play advantage (pp, WR on play - on draw)"), ("mull_penalty", "mulligan penalty (pp, WR after 1 mulligan - no mulligan)")):
    if k in pdr:
        d = pd.DataFrame({"d": pdr[k]["T"] - pdr[k]["N"]})
        say("%s: N %.2f, T %.2f; T-N %+.2f (same sign in %d/%d sets)" % (lab, pdr[k]["N"].mean(), pdr[k]["T"].mean(), *mean_sets(d, "d")))
SM = pd.concat([pd.read_csv(D / f"{s}_sums.csv") for s in sets], ignore_index=True)
sm = []
for g, b in G.items():
    y = SM[SM.band.isin(b)].groupby("set")[["n", "deck_size", "sb_size", "oh_cards", "drawn_cards", "turns_n"]].sum()
    for k in ("deck_size", "sb_size", "oh_cards", "drawn_cards", "turns_n"): y[k] = y[k] / y.n
    y["grp"] = g; sm.append(y.reset_index())
sm = pd.concat(sm); table(sm.groupby("grp")[["deck_size", "sb_size", "oh_cards", "drawn_cards", "turns_n"]].mean().reindex(list(G)).reset_index(), "game_sums")
x = GM[GM.dim == "turns"].copy(); x["t"] = pd.to_numeric(x.val, errors="coerce")
x["bucket"] = pd.cut(x.t, [-1, 6, 8, 10, 12, 99], labels=["<=6", "7-8", "9-10", "11-12", "13+"])
tw = []
for g in ("B1", "N", "T", "B5"):
    y = x[x.band.isin(G[g])].groupby(["set", "bucket"], observed=True)[["games", "wins"]].sum().reset_index()
    y["share"] = y.games / y.groupby("set").games.transform("sum"); y["wr"] = 100 * y.wins / y.games; y["grp"] = g; tw.append(y)
tw = pd.concat(tw).groupby(["grp", "bucket"], observed=True)[["share", "wr"]].mean().reset_index(); table(tw, "turns_by_group")
rk = GM[GM.dim.isin(["rank", "opp_rank"])].copy()
rk["tier"] = rk.val.astype(str).str.lower().str.extract(r"(bronze|silver|gold|platinum|diamond|mythic)", expand=False).fillna("unknown")
rr_ = []
for g in ("L", "B1", "N", "T", "B5"):
    for dim in ("rank", "opp_rank"):
        y = rk[(rk.dim == dim) & rk.band.isin(G[g])].groupby(["set", "tier"]).games.sum().unstack(fill_value=0)
        y = y.div(y.sum(1), axis=0).mean(); y["grp"] = g; y["dim"] = dim; rr_.append(y)
rr_ = pd.DataFrame(rr_).fillna(0); cols = ["grp", "dim"] + [c for c in ["bronze", "silver", "gold", "platinum", "diamond", "mythic", "unknown"] if c in rr_]
table(rr_[cols], "rank_distribution")
mt = GM[GM.dim == "match_number"].copy(); mt["m"] = pd.to_numeric(mt.val, errors="coerce")
say("mean match number within a draft run (games-weighted): " + ", ".join(f"{g} {(mt[mt.band.isin(G[g])].m * mt[mt.band.isin(G[g])].games).sum() / mt[mt.band.isin(G[g])].games.sum():.2f}" for g in ("L", "B1", "N", "T", "B5")))

# ---------------------------------------------------------------- 4. deck building
say("\n=== 4. deck building by group (mean over sets; per game)")
games_g = {g: GM[(GM.dim == "all") & GM.band.isin(b)].groupby("set").games.sum() for g, b in G.items()}
cc = C.groupby(["set", "card_name", "grp"])[["copies"]].sum().reset_index().merge(attr, on=["set", "card_name"], how="left")
for k in ("is_land", "is_creature", "is_instant", "is_sorcery", "is_other", "known_type", "blue"):
    cc[k] = cc[k].fillna(False).astype(bool)
comp = []
for g, b in G.items():
    y = cc[cc.grp.isin(b)].copy(); nl = ~y.is_land
    per = lambda mask: y[mask].groupby("set").copies.sum() / games_g[g]
    q = y[y.q_c.notna() & nl]; mvk = y[nl & y.mv.notna()]
    comp.append(pd.DataFrame({"lands": per(y.is_land), "creatures": per(y.is_creature), "instants": per(y.is_instant & ~y.is_creature),
                              "sorceries": per(y.is_sorcery), "other_spells": per(y.is_other), "unknown_type": per(~y.known_type),
                              "commons": per((y.rarity == 0) & nl), "uncommons": per((y.rarity == 1) & nl), "rares": per((y.rarity == 2) & nl), "mythics": per((y.rarity == 3) & nl),
                              "mv_nonland": (mvk.copies * mvk.mv).groupby(mvk.set).sum() / mvk.groupby("set").copies.sum(),
                              "deck_quality": (q.copies * q.q_c).groupby(q.set).sum() / q.groupby("set").copies.sum(),
                              "blue_cards": per(y.blue & nl)}).assign(grp=g).rename_axis("set").reset_index())
comp = pd.concat(comp); table(comp.groupby("grp").mean(numeric_only=True).reindex(list(G)).reset_index(), "deck_composition")
dq = comp.pivot(index="set", columns="grp", values="deck_quality")
say("deck quality index (copies-weighted mean of the cards' overall GIH, centred in the set): T - N %+.2fpp (same sign %d/%d); B5 - N %+.2f; B1 - N %+.2f; L - N %+.2f" % (
    *mean_sets(pd.DataFrame({"d": dq["T"] - dq["N"]}), "d"), (dq["B5"] - dq["N"]).mean(), (dq["B1"] - dq["N"]).mean(), (dq["L"] - dq["N"]).mean()))
mc = GM[GM.dim == "main_colors"].copy(); mc = mc[mc.val.astype(str).str.len() == 2]
colr = []
for s in sets:
    z = mc[mc.set == s]
    allp = z.groupby("val")[["games", "wins"]].sum(); allp["wr_all"] = 100 * allp.wins / allp.games
    for g in ("N", "T"):
        y = z[z.band.isin(G[g])].groupby("val")[["games", "wins"]].sum(); y["share"] = y.games / y.games.sum(); y["wr"] = 100 * y.wins / y.games
        allp["share_" + g] = y.share; allp["wr_" + g] = y.wr
    allp["set"] = s; colr.append(allp.reset_index())
colr = pd.concat(colr); colr["share_diff"] = colr.share_T - colr.share_N
cs = colr.groupby("set").apply(lambda y: pd.Series(dict(r_diff=spearmanr(y.share_diff, y.wr_all)[0], r_N=spearmanr(y.share_N, y.wr_all)[0], r_T=spearmanr(y.share_T, y.wr_all)[0])))
say("colour pairs (2-colour decks, 10 pairs, Spearman with the pair's all-player WR, mean over sets): share(N) %.2f, share(T) %.2f, share(T)-share(N) %.2f" % (cs.r_N.mean(), cs.r_T.mean(), cs.r_diff.mean()))
colr["has_U"] = colr.val.str.contains("U")
say("share of 2-colour games with blue: N %.3f, T %.3f" % (colr[colr.has_U].groupby("set").share_N.sum().mean(), colr[colr.has_U].groupby("set").share_T.sum().mean()))
colr.to_csv(OUT / "colour_pairs.csv", index=False)
spc = colr.groupby("set").apply(lambda y: pd.Series(dict(sd_N=y.wr_N.std(), sd_T=y.wr_T.std(), slope=np.polyfit(y.wr_N - y.wr_N.mean(), y.wr_T - y.wr_T.mean(), 1)[0])))
say("colour-pair WR spread across the 10 pairs: SD N %.2f, T %.2f; slope of T on N %.2f" % (spc.sd_N.mean(), spc.sd_T.mean(), spc.slope.mean()))

# ---------------------------------------------------------------- 5. card choice
say("\n=== 5. which cards make the deck (maindeck rate when the card is in the pool, game-weighted)")
dr = R["N"][["deck_rate", "pool_g"]].join(R["T"][["deck_rate", "pool_g"]], lsuffix="_N", rsuffix="_T").join(R["B1"][["deck_rate"]].rename(columns={"deck_rate": "deck_rate_B1"}))
dr = dr[(dr.pool_g_N >= 1000) & (dr.pool_g_T >= 1000)].reset_index().merge(attr[["set", "card_name", "q_c", "rarity", "is_land", "is_creature", "is_instant", "is_sorcery", "is_equipment", "is_aura", "blue"]], on=["set", "card_name"], how="left")
dr = dr[~dr.is_land.fillna(False).astype(bool)]
r5 = []
for s, y in dr.groupby("set"):
    y = y.dropna(subset=["q_c"])
    if len(y) < 30: continue
    r5.append(dict(set=s, n=len(y), corr_q_rate_B1=spearmanr(y.q_c, y.deck_rate_B1, nan_policy="omit")[0], corr_q_rate_N=spearmanr(y.q_c, y.deck_rate_N)[0], corr_q_rate_T=spearmanr(y.q_c, y.deck_rate_T)[0],
                   mean_rate_N=y.deck_rate_N.mean(), mean_rate_T=y.deck_rate_T.mean(), corr_q_rate_diff=spearmanr(y.q_c, y.deck_rate_T - y.deck_rate_N)[0]))
r5 = pd.DataFrame(r5); table(r5.mean(numeric_only=True).to_frame("mean").T, "deck_rate_vs_quality")
say("sets where top players' maindeck choices follow card strength more closely than N's: %d/%d" % (int((r5.corr_q_rate_T > r5.corr_q_rate_N).sum()), len(r5)))
dr.to_csv(OUT / "deck_rate_by_card.csv", index=False)

# ---------------------------------------------------------------- 6. card performance: GIH, OH, GD, GNS, IWD
say("\n=== 6. card performance by group: where does the top-normal difference come from?")
rows = []
for metric, cnt, mn in (("gih", "gih_g", MIN), ("oh", "oh_g", 300), ("gd", "gd_g", 300), ("gns", "gns_g", 300), ("iwd", "gih_g", MIN), ("gp", "deck_g", MIN)):
    p = pair_stats(R["T"], R["N"], metric=metric, cnt=cnt, minA=mn, minB=mn)
    if len(p): rows.append(dict(metric=metric, sets=len(p), cards=p.n.mean(), gap_T_minus_N=p.gap.mean(), slope=p.slope.mean(), sd_ratio=p.sd_ratio.mean(), spearman=p.spearman.mean()))
table(pd.DataFrame(rows), "card_metrics_T_vs_N")
def resid(metric, cnt, minc=MIN):
    out = []
    for s in sets:
        parts = {}
        try:
            for (g, h), r in Rh.items():
                parts[f"{g}{h}"] = r.loc[s][metric]; parts[f"{g}{h}_n"] = r.loc[s][cnt]
            for g in ("T", "N"):
                parts[g] = R[g].loc[s][metric]; parts[g + "_n"] = R[g].loc[s][cnt]
        except KeyError:
            continue
        x = pd.DataFrame(parts).dropna()
        x = x[(x["T_n"] >= minc) & (x["N_n"] >= minc) & (x["T0_n"] >= minc / 4) & (x["T1_n"] >= minc / 4)]
        if len(x) < 30: continue
        f = lambda col: x[col] - x[col].mean()
        Tc, Nc = f("T"), f("N")
        b = np.polyfit(Nc, Tc, 1)[0]
        e = Tc - b * Nc
        e0 = f("T0") - b * f("N1"); e1 = f("T1") - b * f("N0")
        out.append(pd.DataFrame({"set": s, "card_name": x.index, "e": e.values, "e0": e0.values, "e1": e1.values, "N_c": Nc.values, "T_c": Tc.values,
                                 "N0_c": f("N0").values, "N1_c": f("N1").values, "slope": b}))
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame()
res = {}
for metric, cnt, mn in (("gih", "gih_g", MIN), ("gns", "gns_g", 300), ("iwd", "gih_g", MIN), ("oh", "oh_g", 300), ("gd", "gd_g", 300)):
    E = resid(metric, cnt, mn)
    if len(E):
        tv = np.cov(E.e0, E.e1)[0, 1]; res[metric] = E
        say(f"  top-specific residual on {metric}: cards {len(E)}, slope {E.groupby('set').slope.first().mean():.3f}, observed SD {E.e.std():.3f}, true SD (independent halves) {np.sqrt(max(tv, 0)):.3f}, true share {tv / E.e.var():.3f}")
def cross(a_, b_):
    j = res[a_].merge(res[b_], on=["set", "card_name"], suffixes=("_a", "_b"))
    cv = (np.cov(j.e0_a, j.e1_b)[0, 1] + np.cov(j.e1_a, j.e0_b)[0, 1]) / 2
    va = np.cov(j.e0_a, j.e1_a)[0, 1]; vb = np.cov(j.e0_b, j.e1_b)[0, 1]
    return len(j), cv, va, vb, cv / np.sqrt(va * vb) if va > 0 and vb > 0 else np.nan
for a_, b_, lab in (("gih", "gns", "GIH vs GNS (the deck wins more even when the card is not drawn)"), ("gih", "iwd", "GIH vs IWD (drawing the card matters more)"),
                    ("oh", "gd", "opening hand vs drawn later")):
    if a_ in res and b_ in res:
        n, cv, va, vb, r = cross(a_, b_)
        say(f"  true covariance {lab}: {cv:.3f} (true var {a_} {va:.3f}, {b_} {vb:.3f}); true correlation {r:.2f}; cards {n}")

# ---------------------------------------------------------------- 7. what goes with the top-specific GIH difference
say("\n=== 7. what goes with the top-specific GIH difference (cards pooled)")
if "gih" in res:
    E = res["gih"].merge(attr, on=["set", "card_name"], how="left").merge(dr[["set", "card_name", "deck_rate_N", "deck_rate_T"]], on=["set", "card_name"], how="left")
    E["rate_diff"] = E.deck_rate_T - E.deck_rate_N
    if "gns" in res: E = E.merge(res["gns"][["set", "card_name", "e", "e0", "e1"]].rename(columns={"e": "e_gns", "e0": "e0_gns", "e1": "e1_gns"}), on=["set", "card_name"], how="left")
    if "iwd" in res: E = E.merge(res["iwd"][["set", "card_name", "e", "e0", "e1"]].rename(columns={"e": "e_iwd", "e0": "e0_iwd", "e1": "e1_iwd"}), on=["set", "card_name"], how="left")
    ok = E.rate_diff.notna()
    if ok.sum() > 30:
        say("  Spearman(top-specific GIH residual, T-N maindeck-rate difference): %.3f (n %d); half-0 residual vs rate diff %.3f" % (spearmanr(E[ok].e, E[ok].rate_diff)[0], ok.sum(), spearmanr(E[ok].e0, E[ok].rate_diff)[0]))
    # strength measured on games independent of the residual: e0 = T(half 0) - b N(half 1) against N(half 0), and vice versa
    say("  Spearman(top-specific GIH residual, normal players' GIH from the other half of the games): %.3f / %.3f" % (spearmanr(E.e0, E.N0_c)[0], spearmanr(E.e1, E.N1_c)[0]))
    cats = {"blue": E.blue, "instant": E.is_instant, "sorcery": E.is_sorcery, "creature": E.is_creature, "equipment": E.is_equipment, "aura": E.is_aura,
            "common": E.rarity == 0, "uncommon": E.rarity == 1, "rare": E.rarity == 2, "mythic": E.rarity == 3,
            "maindecked more by T (rate diff top quarter)": E.rate_diff >= E.rate_diff.quantile(.75), "maindecked less by T (rate diff bottom quarter)": E.rate_diff <= E.rate_diff.quantile(.25)}
    rows = []
    for k, m in cats.items():
        m = m.fillna(False).astype(bool); x = E[m]
        if len(x) < 30: continue
        ps = x.groupby("set").e.mean()
        rows.append(dict(category=k, n=len(x), gih=x.e.mean(), gih_h0=x.e0.mean(), gih_h1=x.e1.mean(),
                         gns=x.e_gns.mean() if "e_gns" in x else np.nan, iwd=x.e_iwd.mean() if "e_iwd" in x else np.nan,
                         sets_same_sign=int((np.sign(ps) == np.sign(x.e.mean())).sum()), sets=len(ps), rate_diff=x.rate_diff.mean()))
    table(pd.DataFrame(rows), "categories")
    E.to_csv(OUT / "card_resid_gih.csv", index=False)

# ---------------------------------------------------------------- 8. over the format
say("\n=== 8. over the format (days 0-13 vs 14-27)")
rows = []
for p_ in ("0", "1"):
    q = pair_stats(Rp[("T", p_)], Rp[("N", p_)], minA=250, minB=250)
    if len(q): rows.append(dict(period=p_, sets=len(q), gap=q.gap.mean(), slope=q.slope.mean(), spearman=q.spearman.mean()))
table(pd.DataFrame(rows), "period")
Rhp = {(g, h, p_): rates(by_group(C, G[g], half=h, period=p_)) for g in ("N", "T") for h in ("0", "1") for p_ in ("0", "1")}
ep = []
for s in sets:
    parts = {}
    try:
        for (g, p_), r in Rp.items():
            parts[f"{g}{p_}"] = r.loc[s]["gih"]; parts[f"{g}{p_}_n"] = r.loc[s]["gih_g"]
        for (g, h, p_), r in Rhp.items():
            parts[f"{g}h{h}p{p_}"] = r.loc[s]["gih"]
    except KeyError:
        continue
    x = pd.DataFrame(parts).dropna()
    x = x[(x["T0_n"] >= 250) & (x["T1_n"] >= 250) & (x["N0_n"] >= 250) & (x["N1_n"] >= 250)]
    if len(x) < 30: continue
    f = lambda col: x[col] - x[col].mean()
    e0 = f("T0") - 0.83 * f("N0"); e1 = f("T1") - 0.83 * f("N1")
    # learning check with independent games: residual from draft-half 0 in period 0, change measured on draft-half 1
    e0h = f("Th0p0") - 0.83 * f("Nh0p0")
    ep.append(pd.DataFrame({"set": s, "e_first": e0.values, "e_second": e1.values, "e_first_h0": e0h.values,
                            "normal_change_h1": (f("Nh1p1") - f("Nh1p0")).values, "top_change_h1": (f("Th1p1") - f("Th1p0")).values}))
if ep:
    ep = pd.concat(ep)
    say("top-specific residual, first vs second period: covariance %.3f (true variance within the full window is about 0.19), Spearman %.3f" % (np.cov(ep.e_first, ep.e_second)[0, 1], spearmanr(ep.e_first, ep.e_second)[0]))
    say("do normal players move toward the top players' view? Spearman(first-period residual from draft-half 0, change in N's GIH measured on draft-half 1) %.3f; same for T %.3f" % (spearmanr(ep.e_first_h0, ep.normal_change_h1)[0], spearmanr(ep.e_first_h0, ep.top_change_h1)[0]))

# ---------------------------------------------------------------- 9. draft picks (site groups)
if site is not None and "avg_pick" in site:
    say("\n=== 9. draft picks and play by site group (17Lands site, all time)")
    S = site.rename(columns={"name": "card_name"}).drop_duplicates(["set", "group", "card_name"])
    allg = S[S.group == "all"].set_index(["set", "card_name"]).ever_drawn_win_rate.rename("gih_all")
    S = S.join(allg, on=["set", "card_name"])
    rows = []
    for g in [x for x in ("bottom", "middle", "top", "all") if x in set(S.group)]:
        y = S[(S.group == g) & S.avg_pick.notna() & S.gih_all.notna() & (S.ever_drawn_game_count >= 200)]
        r = y.groupby("set").apply(lambda z: spearmanr(-z.avg_pick, z.gih_all)[0] if len(z) > 30 else np.nan)
        rows.append(dict(group=g, sets=int(r.notna().sum()), spearman_pick_order_vs_all_GIH=r.mean(), mean_ATA=y.avg_pick.mean(),
                         gih_wr=(100 * (y.ever_drawn_win_rate * y.ever_drawn_game_count).sum() / y.ever_drawn_game_count.sum())))
    table(pd.DataFrame(rows), "site_picks")
    share = S.groupby("group").ever_drawn_game_count.sum() / S[S.group == "all"].ever_drawn_game_count.sum()
    say("share of all-user GIH games by site group: " + json.dumps({k: round(float(v), 3) for k, v in share.items()}))

(OUT / "report.txt").write_text("\n".join(report_lines))
