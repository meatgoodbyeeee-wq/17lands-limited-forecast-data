"""TP3 stage 2: freeze the top-player forecasts for FRA and TRK (PLAN.md). Reads no top-player outcome of FRA or TRK.
  python3 freeze.py <cards.csv.gz (23 sets)> <oof_B11g.csv.gz> <oof_B10.csv.gz> <fra_frozen_predictions.csv> <trk_cards.csv from trk_tags.py> <out dir>"""
import hashlib, json, sys
from datetime import datetime, timezone
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import tp3  # noqa: E402

cards_p, b11_p, b10_p, fra_p, trk_p, out = sys.argv[1:7]; out = Path(out); out.mkdir(parents=True, exist_ok=True)
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
E, F = tp3.load(cards_p); y = E.e_gih_A.to_numpy(float); w = 1 / (E.v_A.to_numpy(float) + tp3.tau2(E[F.use.to_numpy()]))
models = {a: tp3.fit(E, F, y, w, a) for a in ("TP3", "TP3basic", "TP3all")}

def base_fit(oof_path):
    o = pd.read_csv(oof_path); o["card_name"] = o.name.astype(str).str.split(" // ").str[0]; o = o.drop_duplicates(["set", "card_name"])
    m = E[["set", "card_name", "T_gih"]].merge(o[["set", "card_name", "pred", "actual_gih"]], on=["set", "card_name"], how="inner")
    m["top"] = m.T_gih; m["overall"] = 100 * m.actual_gih; m["pred"] = 100 * m.pred
    k, c = tp3.base_params(m); return k, c, len(m)

def fra_cards():
    """FRA rows are keyed by the gallery id ("FRA|<id>"), the same id as in the frozen B10 file."""
    def ld(f):
        x = pd.read_csv(f); x = x[x.key.str.startswith("FRA|")].copy(); x["gid"] = x.key.str.split("|", n=1).str[1]; return x.drop(columns=["key", "id"], errors="ignore").drop_duplicates("gid")
    c5 = ld("research/c5_atomic_effects/c5_features.csv.gz"); c4 = ld("research/c4_fine_effects/c4_features.csv.gz")
    tx = ld("research/c14_context_power/set_cards.csv.gz")[["gid", "type", "text", "mv", "colors", "rar"]]
    p = pd.read_csv(fra_p).rename(columns={"id": "gid"}).drop_duplicates("gid")
    d = p[["gid", "name", "pred_B10"]].merge(tx, on="gid", how="left").merge(c5, on="gid", how="left").merge(c4, on="gid", how="left")
    d["card_name"] = d.name.astype(str).str.split(" // ").str[0]
    d["pred_overall_pp"] = 100 * d.pred_B10; d.insert(0, "set", "FRA"); return d.drop(columns=["gid", "name"])

meta = {"frozen_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "inputs": {"cards_23sets": sha(cards_p), "oof_B11g": sha(b11_p), "oof_B10": sha(b10_p), "fra_pred": sha(fra_p), "trk_cards": sha(trk_p)},
        "tp3_columns": ["intercept"] + tp3.TP3_COLS, "tp3_beta": [round(float(b), 6) for b in models["TP3"]["beta"]], "sets": {}}
for code, d, oof in (("FRA", fra_cards(), b10_p), ("TRK", pd.read_csv(trk_p, keep_default_na=False, na_values=[""]), b11_p)):
    k, c, n = base_fit(oof); f = tp3.raw_features(d)
    o = pd.DataFrame({"set": code, "card_name": d.card_name, "pred_overall_pp": d.pred_overall_pp.round(4), "tagged_nonland": f.use.to_numpy()})
    for a, m in models.items(): o["corr_" + a] = np.round(tp3.predict(m, d, f), 4)
    pk, pl = tp3.base_predict(o.pred_overall_pp, o.set, k, c)
    o["main_centred"] = np.round(pk + (o.corr_TP3 - o.corr_TP3.mean()), 4)   # TP0K + TP3, centred over the whole card list (scoring re-centres over the scored cards)
    o["top_gih_level_L"] = np.round(100 / (1 + np.exp(-(tp3.logit(o.pred_overall_pp / 100) + c))), 4)
    fn = out / f"{code.lower()}_frozen_top.csv"; o.to_csv(fn, index=False)
    meta["sets"][code] = {"file": fn.name, "sha256": sha(fn), "cards": len(o), "tagged_nonland": int(f.use.sum()), "k": round(k, 6), "c": round(c, 6), "base_fit_cards": n,
                          "base": "pred_B10 (frozen 2026-10)" if code == "FRA" else "published B11g (trk_frozen.csv G)", "corr_TP3_sd": round(float(o.corr_TP3.std()), 4)}
    print(code, meta["sets"][code]); print(o.assign(c=o.corr_TP3 - o.corr_TP3.mean()).nlargest(5, "c")[["card_name", "c"]].round(2).to_string(index=False)); print(o.assign(c=o.corr_TP3 - o.corr_TP3.mean()).nsmallest(5, "c")[["card_name", "c"]].round(2).to_string(index=False))
(out / "frozen.json").write_text(json.dumps(meta, indent=1))
