#!/usr/bin/env python3
"""Case 6 research runs (see PLAN.md). FIN, MH3 and FRA are never read.

  python case6_research.py check        # aggregates reproduce stored compact_28d; coverage report
  python case6_research.py forward      # Part A (A vs B) and Part B (B vs B+C3) on the new sets
  python case6_research.py top          # Part C (top-player target): descriptive + LOSO T0/T1 (+C3) + forward check
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import pearsonr, spearmanr

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(HERE.parent / "gih_llm_extract"))
import gih21_research as g  # noqa: E402
import c3_research as c3  # noqa: E402

DATA = HERE / "data"
NEW = ["EOE", "TLA", "ECL", "TMT", "SOS", "MSH", "HOB"]
DECISION_A = NEW[1:]
CLEAN = ["MSH", "HOB"]
TOP_SETS = ["NEO", "SNC", "DMU", "BRO", "ONE", "MOM", "LTR", "WOE", "LCI", "MKM", "OTJ", "BLB", "DSK", "FDN", "DFT", "TDM"]
SEEDS = c3.SEEDS
FORBIDDEN = {"FIN", "MH3", "FRA"}
MIN_TOP = 500


def agg_frame(sets):
    fs = []
    for s in sets:
        if s in FORBIDDEN:
            raise SystemExit("forbidden set")
        fs.append(pd.read_csv(DATA / f"{s}_case6_28d.csv"))
    return pd.concat(fs, ignore_index=True).rename(columns={"card_name": "name"})


def load_dev():
    d, base, cols = c3.load_with_c3()
    return d, base, cols


def load_new(base, cols):
    n = pd.read_csv(DATA / "new_feature_table.csv.gz")
    n["set"] = n["set"].str.upper()
    if set(n["set"]) & FORBIDDEN or set(n["set"]) != set(NEW):
        raise SystemExit(f"unexpected new sets {sorted(set(n['set']))}")
    n["__text"] = g.text_of(n)
    missing = [c for c in base if c not in n.columns]
    if missing:
        raise SystemExit(f"new table lacks {missing}")
    f = HERE / "c3_features_new.csv.gz"
    if f.exists():
        x = pd.read_csv(f, keep_default_na=False)
        n["key"] = n["set"] + "|" + n["name"]
        n = n.merge(x[["key"] + cols], on="key", how="left", validate="many_to_one")
        if n[cols].isna().any().any():
            raise SystemExit("C3 missing for some new-set cards")
    return n


def cmd_check(_a):
    d, base, cols = load_dev()
    a = agg_frame(sorted(g.RESEARCH_SETS))
    m = d[["set", "name", "gih_games", "gih_wins"]].merge(a[["set", "name", "all_games", "all_wins"]], on=["set", "name"], how="left")
    ok = (m["gih_games"] == m["all_games"]) & (m["gih_wins"] == m["all_wins"])
    rep = {"dev_rows": len(d), "matched": int(m["all_games"].notna().sum()), "exact_games_and_wins": int(ok.sum()),
           "mismatch_by_set": m.loc[~ok].groupby("set").size().to_dict()}
    man = {s: json.loads((DATA / f"{s}_case6_manifest.json").read_text()) for s in sorted(g.RESEARCH_SETS) + NEW}
    rep["windows"] = {s: {"start": v["window_start"], "last": v["last_draft_time_in_window"], "games": v["group_games"]["all"],
                          "top60n50_share": (v["group_games"]["top60n50"] / v["group_games"]["all"]) if v["group_games"]["all"] else None}
                      for s, v in man.items()}
    n = pd.read_csv(DATA / "new_feature_table.csv.gz")
    rep["new_rows"] = n.groupby("set").size().to_dict()
    (HERE / "check.json").write_text(json.dumps(rep, indent=2, default=float))
    print(json.dumps({k: rep[k] for k in ("dev_rows", "matched", "exact_games_and_wins", "mismatch_by_set", "new_rows")}, indent=2))


def set_metrics(df, pcol, ycol="actual_gih"):
    x = df.drop(columns=["actual_gih"], errors="ignore").rename(columns={ycol: "actual_gih"}) if ycol != "actual_gih" else df
    _, per = g.within_set(x, x[pcol].to_numpy())
    return per


def mean_metrics(per):
    return {"mae": float(per["mae_pp"].mean()), "spearman": float(per["spearman"].mean()),
            "tail_bias_sum": float((per["top10_bias_pp"].abs() + per["bottom10_bias_pp"].abs()).mean()),
            "recall_mean": float(((per["strong_recall"] + per["weak_recall"]) / 2).mean()),
            "bias": float(per["bias_pp"].mean())}


def cmd_forward(_a):
    d, base, cols = load_dev()
    n = load_new(base, cols)
    has_c3 = all(c in n.columns for c in cols)
    arms = {"A_21": ("A", base), "B_extended": ("B", base)}
    if has_c3:
        arms["B_extended+C3"] = ("B", base + cols)
    preds = {k: {sd: pd.Series(np.nan, index=n.index) for sd in SEEDS} for k in arms}
    for i, s in enumerate(NEW):
        te = n["set"] == s
        for name, (pool, nums) in arms.items():
            train = d if pool == "A" else pd.concat([d, n[n["set"].isin(NEW[:i])]], ignore_index=True)
            for sd in SEEDS:
                preds[name][sd][te] = c3.fit_predict(train, n[te], nums, sd)
            print(s, name, flush=True)
    out = {"fin_used": False, "mh3_used": False, "fra_used": False, "seeds": SEEDS, "arms": {}, "per_set": {}}
    oof = n[["set", "name", "rarity_ord", "actual_gih"]].copy()
    for name in arms:
        runs = []
        for sd in SEEDS:
            oof[f"pred_{name}_s{sd}"] = preds[name][sd].to_numpy()
            per = set_metrics(oof.assign(_p=preds[name][sd].to_numpy()), "_p").set_index("set")
            runs.append(per)
        out["per_set"][name] = {sd: r.reset_index().to_dict(orient="records") for sd, r in zip(SEEDS, runs)}
        out["arms"][name] = {grp: {"runs": [mean_metrics(r.loc[sets]) for r in runs]}
                             for grp, sets in {"decision_A": DECISION_A, "clean": CLEAN, "pre_cutoff_new": NEW[:5], "all_new": NEW}.items()}
    out["rule_A"] = rule_pair(out, "A_21", "B_extended", "decision_A", need_wins=4)
    if has_c3:
        out["rule_B"] = rule_pair(out, "B_extended", "B_extended+C3", "clean", need_wins=None)
        out["rule_B_pre_cutoff_new_report"] = rule_pair(out, "B_extended", "B_extended+C3", "pre_cutoff_new", need_wins=None)
    (HERE / "forward.json").write_text(json.dumps(out, indent=2, default=float))
    oof.to_csv(HERE / "forward_oof.csv.gz", index=False, compression="gzip")
    print(json.dumps({k: v for k, v in out.items() if k.startswith("rule")}, indent=2, default=float))


def rule_pair(out, base_arm, cand_arm, grp, need_wins):
    b = out["arms"][base_arm][grp]["runs"]; c = out["arms"][cand_arm][grp]["runs"]
    mb = {k: float(np.mean([r[k] for r in b])) for k in b[0]}
    mc = {k: float(np.mean([r[k] for r in c])) for k in c[0]}
    rng_b = {k: float(np.ptp([r[k] for r in b])) for k in b[0]}
    sets = {"decision_A": DECISION_A, "clean": CLEAN, "pre_cutoff_new": NEW[:5]}[grp]
    pb = pd.DataFrame(out["per_set"][base_arm][SEEDS[0]]).set_index("set").loc[sets]
    pc = pd.DataFrame(out["per_set"][cand_arm][SEEDS[0]]).set_index("set").loc[sets]
    per = {s: {"mae_change": float(pc.loc[s, "mae_pp"] - pb.loc[s, "mae_pp"]),
               "spearman_change": float(pc.loc[s, "spearman"] - pb.loc[s, "spearman"])} for s in sets}
    wins = int((pc["mae_pp"] < pb["mae_pp"]).sum())
    res = {"base": mb, "cand": mc, "base_seed_range": rng_b, "per_set_seed0": per, "mae_wins_seed0": wins, "of": len(sets)}
    mae_up = mc["mae"] < mb["mae"]
    if need_wins is not None:  # Rule A
        res["rules"] = {"1_mae_improves": mae_up, "2_spearman_not_down": mc["spearman"] >= mb["spearman"],
                        "3_set_wins": wins >= need_wins, "4_beyond_seed_noise": (mb["mae"] - mc["mae"]) > rng_b["mae"]}
    else:  # Rule B
        res["rules"] = {"mae_improves": mae_up, "spearman_improves": mc["spearman"] > mb["spearman"]}
    res["pass"] = bool(all(res["rules"].values()))
    return res


# ---------------- Part C ----------------
def top_target(a, group="top60n50"):
    gm, wn = a[f"{group}_games"], a[f"{group}_wins"]
    return np.where(gm >= MIN_TOP, wn / gm.replace(0, np.nan), np.nan)


def reliability(x0, x1):
    ok = np.isfinite(x0) & np.isfinite(x1)
    if ok.sum() < 10:
        return np.nan
    r = pearsonr(x0[ok], x1[ok]).statistic
    return 2 * r / (1 + r)


def describe(a, man):
    rows = []
    for s, gdf in a.groupby("set"):
        v = man[s]
        if not v["has_user_wr_bucket"]:
            continue
        top = top_target(gdf)
        ok = np.isfinite(top)
        allw = gdf["all_wins"] / gdf["all_games"]
        ng = gdf["all_games"] - gdf["top60n50_games"]; nw = gdf["all_wins"] - gdf["top60n50_wins"]
        non = nw / ng
        t0 = gdf["top60n50_h0_wins"] / gdf["top60n50_h0_games"].replace(0, np.nan)
        t1 = gdf["top60n50_h1_wins"] / gdf["top60n50_h1_games"].replace(0, np.nan)
        n0 = (gdf["all_h0_wins"] - gdf["top60n50_h0_wins"]) / (gdf["all_h0_games"] - gdf["top60n50_h0_games"]).replace(0, np.nan)
        n1 = (gdf["all_h1_wins"] - gdf["top60n50_h1_wins"]) / (gdf["all_h1_games"] - gdf["top60n50_h1_games"]).replace(0, np.nan)
        rel_t = reliability(t0[ok].to_numpy(float), t1[ok].to_numpy(float))
        rel_n = reliability(n0[ok].to_numpy(float), n1[ok].to_numpy(float))
        r_tn = pearsonr(top[ok], non[ok]).statistic
        rows.append({"set": s, "cards": int(len(gdf)), "cards_with_top_target": int(ok.sum()),
                     "top_game_share": v["group_games"]["top60n50"] / v["group_games"]["all"],
                     "top_game_win_rate": v["group_game_win_rate"]["top60n50"],
                     "mean_top_minus_overall_pp": float(np.nanmean(top[ok] - allw[ok]) * 100),
                     "spearman_top_vs_overall": float(spearmanr(top[ok], allw[ok]).statistic),
                     "pearson_top_vs_nontop": float(r_tn), "reliability_top": float(rel_t), "reliability_nontop": float(rel_n),
                     "disattenuated_top_vs_nontop": float(r_tn / np.sqrt(rel_t * rel_n)) if rel_t > 0 and rel_n > 0 else None,
                     "sd_top_pp": float(np.std(top[ok]) * 100), "sd_overall_pp": float(np.std(allw[ok]) * 100)})
    return pd.DataFrame(rows)


def cmd_top(_a):
    d, base, cols = load_dev()
    a = agg_frame(sorted(g.RESEARCH_SETS))
    man = {s: json.loads((DATA / f"{s}_case6_manifest.json").read_text()) for s in sorted(g.RESEARCH_SETS) + NEW}
    desc = describe(pd.concat([a, agg_frame(NEW)], ignore_index=True), man)
    agg_cols = [c for c in a.columns if c.startswith(("top", "all_"))]
    d = d.merge(a[["set", "name"] + agg_cols], on=["set", "name"], how="left", validate="many_to_one")
    d["top_gih"] = top_target(d.fillna({"top60n50_games": 0, "top60n50_wins": 0}))
    for grp in ("top56n50", "top64n50", "top60"):
        d[f"{grp}_gih"] = top_target(d.fillna({f"{grp}_games": 0, f"{grp}_wins": 0}), grp)
    res = {"fin_used": False, "mh3_used": False, "fra_used": False, "min_top_games": MIN_TOP, "seeds": SEEDS,
           "descriptive": desc.to_dict(orient="records"),
           "descriptive_mean_research16": desc[desc["set"].isin(TOP_SETS)].drop(columns=["set"]).mean(numeric_only=True).to_dict(),
           "descriptive_mean_new": desc[desc["set"].isin(NEW)].drop(columns=["set"]).mean(numeric_only=True).to_dict()}
    arms = {"T0_overall_shift": ("overall", base), "T1_top_direct": ("top", base),
            "T0+C3": ("overall", base + cols), "T1+C3": ("top", base + cols)}
    runs = {k: [] for k in arms}
    oof = d.loc[d["set"].isin(TOP_SETS) & d["top_gih"].notna(), ["set", "name", "rarity_ord", "actual_gih", "top_gih"]].copy()
    for sd in SEEDS:
        preds = {k: pd.Series(np.nan, index=oof.index) for k in arms}
        for hold in TOP_SETS:
            te = oof.index[oof["set"] == hold]
            for name, (target, nums) in arms.items():
                if target == "overall":
                    train = d[d["set"] != hold]
                    shift_rows = train[train["top_gih"].notna()]
                    shift = float((shift_rows["top_gih"] - shift_rows["actual_gih"]).mean())
                    p = c3.fit_predict(train, d.loc[te], nums, sd) + shift
                else:
                    train = d[(d["set"] != hold) & d["top_gih"].notna()].copy()
                    train["actual_gih"] = train["top_gih"]
                    p = c3.fit_predict(train, d.loc[te], nums, sd)
                preds[name][te] = p
        for name in arms:
            oof[f"pred_{name}_s{sd}"] = preds[name].to_numpy()
            per = set_metrics(oof.assign(_p=preds[name].to_numpy()), "_p", ycol="top_gih")
            runs[name].append(per)
        print("seed", sd, {k: round(mean_metrics(runs[k][-1])["mae"], 4) for k in arms}, flush=True)
    res["loso"] = {k: {"runs": [mean_metrics(r) for r in v], "per_set_seed0": v[0].to_dict(orient="records")} for k, v in runs.items()}
    b = res["loso"]["T0_overall_shift"]["runs"]; c = res["loso"]["T1_top_direct"]["runs"]
    mb = {k: float(np.mean([r[k] for r in b])) for k in b[0]}; mc = {k: float(np.mean([r[k] for r in c])) for k in c[0]}
    p0 = runs["T0_overall_shift"][0].set_index("set"); p1 = runs["T1_top_direct"][0].set_index("set")
    wins = int((p1["mae_pp"] < p0["mae_pp"]).sum())
    res["rule_C"] = {"T0": mb, "T1": mc, "mae_wins_T1_seed0": wins, "of": len(TOP_SETS),
                     "rules": {"mae_improves": mc["mae"] < mb["mae"], "spearman_improves": mc["spearman"] > mb["spearman"], "set_wins_9": wins >= 9}}
    res["rule_C"]["pass"] = bool(all(res["rule_C"]["rules"].values()))
    # How well does the plain overall model rank top-player GIH, compared with how well it ranks overall GIH on the same cards?
    ov = oof.assign(_p=oof[f"pred_T0_overall_shift_s{SEEDS[0]}"])
    res["same_cards_overall_target_seed0"] = mean_metrics(set_metrics(ov, "_p", ycol="actual_gih"))
    res["sensitivity_targets_spearman_vs_primary"] = {
        grp: float(d.groupby("set").apply(lambda x: spearmanr(x["top_gih"], x[f"{grp}_gih"], nan_policy="omit").statistic
                                           if x["top_gih"].notna().sum() > 10 else np.nan).mean())
        for grp in ("top56n50", "top64n50", "top60")}
    # Forward check on the new sets (reported only): train on 21 research + earlier new sets.
    n = load_new(base, cols)  # the new-set table already carries the case-6 group counts
    n["top_gih"] = top_target(n.fillna({"top60n50_games": 0, "top60n50_wins": 0}))
    fw = {}
    for name, (target, nums) in arms.items():
        if not all(c in n.columns for c in nums):
            continue
        rows = []
        for i, s in enumerate(NEW[1:], start=1):
            te = n.index[(n["set"] == s) & n["top_gih"].notna()]
            pool = pd.concat([d, n[n["set"].isin(NEW[:i])]], ignore_index=True)
            ps = []
            for sd in SEEDS:
                if target == "overall":
                    sr = pool[pool["top_gih"].notna()]
                    ps.append(c3.fit_predict(pool, n.loc[te], nums, sd) + float((sr["top_gih"] - sr["actual_gih"]).mean()))
                else:
                    tr = pool[pool["top_gih"].notna()].copy(); tr["actual_gih"] = tr["top_gih"]
                    ps.append(c3.fit_predict(tr, n.loc[te], nums, sd))
            x = n.loc[te, ["set", "name", "top_gih"]].assign(_p=np.mean(ps, axis=0))
            rows.append(set_metrics(x, "_p", ycol="top_gih"))
        per = pd.concat(rows, ignore_index=True)
        fw[name] = {"mean": mean_metrics(per), "per_set": per.to_dict(orient="records")}
        print("forward", name, round(fw[name]["mean"]["mae"], 4), flush=True)
    res["forward_new_sets_report"] = fw
    (HERE / "top.json").write_text(json.dumps(res, indent=2, default=float))
    oof.to_csv(HERE / "top_oof.csv.gz", index=False, compression="gzip")
    print(json.dumps(res["rule_C"], indent=2, default=float))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["check", "forward", "top"])
    a = ap.parse_args()
    {"check": cmd_check, "forward": cmd_forward, "top": cmd_top}[a.cmd](a)


if __name__ == "__main__":
    main()
