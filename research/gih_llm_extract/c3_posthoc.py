#!/usr/bin/env python3
"""Post-hoc diagnostics for C3 (NOT decision-grade; run after the pre-registered verdict).

1. Where the C3 gain comes from: MAE change by rarity, type and set (3-seed average OOF from compare_oof.csv.gz).
2. Field ablation (seed 20260922 only): "facts" fields vs the judgement-heavy dependency/drawback fields.
   If the gain came mostly from judgement fields, memorised card quality (leakage) would be the more likely source.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import c3_research as c  # noqa: E402

JUDGEMENT = {"llm_dependency", "llm_drawback", "llm_friction", "llm_net"} | {f"llm_dep_{k}" for k in c.DEPS}


def gain_tables(d):
    o = pd.read_csv(HERE / "compare_oof.csv.gz")
    sb = [x for x in o.columns if x.startswith("pred_baseline_s")]
    sc = [x for x in o.columns if x.startswith("pred_C3_llm_extract_s")]
    o["pb"] = o[sb].mean(axis=1); o["pc"] = o[sc].mean(axis=1)
    o = o.merge(d[["set", "name", "type_creature", "type_instant", "type_sorcery", "type_land"]], on=["set", "name"])
    o["eb"] = (o["pb"] - o["actual_gih"]).abs() * 100; o["ec"] = (o["pc"] - o["actual_gih"]).abs() * 100
    o["rarity"] = o["rarity_ord"].map({0: "common", 1: "uncommon", 2: "rare", 3: "mythic"}).fillna("other")
    o["type"] = np.select([o.type_creature == 1, o.type_instant == 1, o.type_sorcery == 1, o.type_land == 1],
                          ["creature", "instant", "sorcery", "land"], "other")
    o["actual_q"] = o.groupby("set")["actual_gih"].rank(pct=True).mul(5).clip(upper=4.999).astype(int)

    def t(key):
        g = o.groupby(key).agg(n=("eb", "size"), mae_base=("eb", "mean"), mae_c3=("ec", "mean"))
        g["delta"] = g["mae_c3"] - g["mae_base"]
        return g.round(4).reset_index().to_dict(orient="records")
    return {"by_rarity": t("rarity"), "by_type": t("type"), "by_set": t("set"), "by_actual_quintile_within_set": t("actual_q")}


def main():
    d, base, cols = c.load_with_c3()
    out = {"note": "post-hoc, not decision-grade", "gain": gain_tables(d), "ablation_seed": c.g.SEED, "ablation": {}}
    facts = [x for x in cols if x not in JUDGEMENT]
    judge = [x for x in cols if x in JUDGEMENT]
    for name, nums in {"facts_only": base + facts, "judgement_only": base + judge}.items():
        p = c.g.loso(d, nums, seed=c.g.SEED)
        s = c.g.summarize(d, p)
        out["ablation"][name] = {"columns": [x for x in nums if x.startswith("llm_")],
                                 "pooled_mae": s["pooled"]["mae_pp"], "within_spearman": s["within_set_mean"]["spearman"],
                                 "tail_bias_sum": abs(s["within_set_mean"]["top10_bias_pp"]) + abs(s["within_set_mean"]["bottom10_bias_pp"])}
        print(name, out["ablation"][name]["pooled_mae"], out["ablation"][name]["within_spearman"], flush=True)
    (HERE / "posthoc.json").write_text(json.dumps(out, indent=2, default=float))
    print(json.dumps(out["gain"]["by_rarity"], indent=1))


if __name__ == "__main__":
    main()
