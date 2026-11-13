"""TP3 stage 2 scoring (PLAN.md rules F1-F3). One run per set, after the freeze.
  python3 score.py <frozen csv> <frozen.json> <SET> <actual dir with <SET>_cards.csv.gz and <SET>_skill_manifest.json> <out json>"""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import spearmanr
sys.path.insert(0, str(Path(__file__).resolve().parent))
import tp3  # noqa: E402

def actual(dirp, code):
    C = pd.read_csv(Path(dirp) / f"{code}_cards.csv.gz", dtype={"half": str, "period": str})
    def agg(grps, half=None):
        x = C[C.grp.isin(grps)]
        if half is not None: x = x[x.half == half]
        x = x.groupby("card_name")[["gih_g", "gih_w"]].sum(); x["gih"] = 100 * x.gih_w / x.gih_g; return x
    T, A = ["B4", "B5"], ["L", "B1", "B2", "B3"]
    d = pd.DataFrame({"T_g": agg(T).gih_g, "A_g": agg(A).gih_g, "T": agg(T).gih, "A": agg(A).gih, "T0": agg(T, "0").gih, "T1": agg(T, "1").gih, "A0": agg(A, "0").gih, "A1": agg(A, "1").gih})
    d = d[(d.T_g >= 500) & (d.A_g >= 500)].dropna(); c = d[["T", "A", "T0", "T1", "A0", "A1"]] - d[["T", "A", "T0", "T1", "A0", "A1"]].mean()
    b = float(np.polyfit(c.A, c["T"], 1)[0]); d["r"] = c["T"] - b * c.A; d["r0"] = c.T0 - b * c.A1; d["r1"] = c.T1 - b * c.A0
    return d.reset_index(), b

def main(frozen_csv, frozen_json, code, actual_dir, out_json):
    fz = pd.read_csv(frozen_csv); meta = json.loads(Path(frozen_json).read_text())["sets"][code]; k, c = meta["k"], meta["c"]
    man = json.loads((Path(actual_dir) / f"{code}_skill_manifest.json").read_text())
    act, b = actual(actual_dir, code); act["card_name"] = act.card_name.astype(str).str.split(" // ").str[0]
    fz["card_name"] = fz.card_name.astype(str).str.split(" // ").str[0]
    m = act.merge(fz.drop_duplicates("card_name"), on="card_name", how="inner")
    res = {"set": code, "window": [man["window_start"], man["window_end"]], "last_draft_time_in_window": man["last_draft_time_in_window"], "games": man["games"], "band_games": man["band_games"],
           "scored_cards_actual": len(act), "matched": len(m), "unmatched_actual": sorted(set(act.card_name) - set(m.card_name))[:40], "slope_b": b, "k": k, "c": c}
    cen = lambda x: np.asarray(x, float) - np.mean(x)
    r = m.r.to_numpy(float); top_c = cen(m["T"]); pk = k * cen(m.pred_overall_pp); pl = cen(100 / (1 + np.exp(-(tp3.logit(m.pred_overall_pp / 100) + c))))
    tau2 = float(np.cov(m.r0, m.r1)[0, 1]); res["true_variance_tau2"] = tau2; res["r_sd"] = float(r.std())
    rng = np.random.default_rng(20261113); arms = {}
    for a in ("TP3", "TP3basic", "TP3all"):
        pc = cen(m["corr_" + a]); obs = float(np.corrcoef(pc, r)[0, 1])
        perm = np.array([np.corrcoef(pc, rng.permutation(r))[0, 1] for _ in range(10000)])
        mae0 = float(np.abs(pk - top_c).mean()); mae1 = float(np.abs(pk + pc - top_c).mean())
        bs = []
        for _ in range(2000):
            i = rng.integers(0, len(m), len(m)); bs.append(np.abs(pk[i] + pc[i] - top_c[i]).mean() - np.abs(pk[i] - top_c[i]).mean())
        arms[a] = {"pearson": obs, "perm_p_one_sided": float((np.sum(perm >= obs) + 1) / (len(perm) + 1)), "spearman": float(spearmanr(pc, r)[0]), "pred_sd": float(pc.std()),
                   "calibration_slope": float(np.cov(pc, r)[0, 1] / pc.var()), "share_of_true_variance": float(np.sign(obs) * np.cov(pc, r)[0, 1] ** 2 / (pc.var() * tau2)) if tau2 > 0 else None,
                   "mae_base_K": mae0, "mae_base_K_plus_corr": mae1, "mae_diff": mae1 - mae0, "mae_diff_ci95": [float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))],
                   "spearman_top_base_K": float(spearmanr(pk, top_c)[0]), "spearman_top_base_K_plus_corr": float(spearmanr(pk + pc, top_c)[0]),
                   "mae_base_L": float(np.abs(pl - top_c).mean()), "mae_base_L_plus_corr": float(np.abs(pl + pc - top_c).mean())}
    res["arms"] = arms
    res["rules"] = {"F1_supported": bool(arms["TP3"]["pearson"] > 0 and arms["TP3"]["perm_p_one_sided"] < 0.05), "F2_mae_lower": bool(arms["TP3"]["mae_diff"] < 0)}
    res["window_closed"] = bool(pd.Timestamp(man["last_draft_time_in_window"]) >= pd.Timestamp(man["window_end"]) - pd.Timedelta(days=1))
    Path(out_json).write_text(json.dumps(res, indent=1)); print(json.dumps(res, indent=1))
    m.assign(pred_main=pk + cen(m.corr_TP3), top_c=top_c)[["card_name", "T_g", "T", "A", "r", "pred_overall_pp", "corr_TP3", "corr_TP3basic", "corr_TP3all", "pred_main", "top_c"]].round(4).to_csv(str(out_json).replace(".json", "_cards.csv"), index=False)

if __name__ == "__main__":
    main(*sys.argv[1:6])
