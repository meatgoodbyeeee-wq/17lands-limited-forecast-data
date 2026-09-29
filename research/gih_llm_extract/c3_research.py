#!/usr/bin/env python3
"""C3 (LLM-extracted card-effect features) vs the adopted 21-set GIH model. See PLAN.md.

  python c3_research.py features                          # raw/*.txt -> c3_features.csv.gz (one row per SET|name key)
  python c3_research.py compare                           # baseline vs baseline+C3, 3 seeds, same LOSO folds
  python c3_research.py freeze --fra <pages>/data/target.json.gz   # frozen FRA predictions (both arms)

FIN and MH3 are never read. No 17Lands API calls. Nothing here touches the Pages repo.
"""
import argparse
import gzip
import hashlib
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import gih21_research as g  # noqa: E402
from build_dev_features import card_features  # noqa: E402
from sklearn.ensemble import ExtraTreesRegressor  # noqa: E402
from sklearn.feature_extraction.text import TfidfVectorizer  # noqa: E402
from sklearn.impute import SimpleImputer  # noqa: E402
from sklearn.linear_model import Ridge  # noqa: E402
from sklearn.pipeline import make_pipeline  # noqa: E402

FEAT = ROOT / "data/features/dev_feature_22.csv.gz"
CARDS = HERE / "cards.csv.gz"
C3_OUT = HERE / "c3_features.csv.gz"
FIELDS = ["removal", "sweeper", "bodies", "cards", "repeat", "modal", "dependency", "drawback", "trick", "sink"]
MAX = [3, 2, 3, 3, 2, 1, 3, 2, 1, 1]
DEPS = list("TGAESKCLXHMO")
LINE = re.compile(r"^(\d+) ([0-9]{10}) (\S)$")
SEEDS = [g.SEED, g.SEED + 1, g.SEED + 2]


def read_raw():
    out = {}
    for f in sorted((HERE / "raw").glob("b*.txt")):
        for ln in f.read_text().splitlines():
            if not ln.strip():
                continue
            m = LINE.match(ln.strip())
            if not m:
                raise SystemExit(f"bad line in {f.name}: {ln!r}")
            i, digits, dep = int(m.group(1)), [int(c) for c in m.group(2)], m.group(3)
            if any(v > mx for v, mx in zip(digits, MAX)) or dep not in "-" + "".join(DEPS):
                raise SystemExit(f"out of range in {f.name}: {ln!r}")
            if i in out:
                raise SystemExit(f"duplicate id {i}")
            out[i] = digits + [dep]
    return out


def c3_columns(raw: pd.DataFrame, mv: pd.Series) -> pd.DataFrame:
    x = pd.DataFrame(index=raw.index)
    for f in FIELDS:
        x[f"llm_{f}"] = raw[f].astype(float)
    for k in DEPS:
        x[f"llm_dep_{k}"] = (raw["dep"] == k).astype(float)
    x["llm_impact"] = (x.llm_removal + 2 * x.llm_sweeper + (x.llm_bodies - 1).clip(lower=0) + x.llm_cards
                       + x.llm_repeat + x.llm_modal)
    x["llm_friction"] = x.llm_dependency + x.llm_drawback
    x["llm_net"] = x.llm_impact - x.llm_friction
    x["llm_impact_per_mv"] = x.llm_impact / np.maximum(pd.to_numeric(mv, errors="coerce").fillna(0), 1)
    return x


def cmd_features(_a):
    raw = read_raw()
    u = pd.read_csv(CARDS, keep_default_na=False)
    todo = set(u.loc[u["auto"] == 0, "id"])
    if set(raw) != todo:
        raise SystemExit(f"coverage mismatch: missing {len(todo - set(raw))}, extra {len(set(raw) - todo)}")
    rows = []
    for r in u.itertuples():
        if r.auto:
            # basic lands and cards with no rules text: zeros, except a vanilla creature is one body
            vals = [0] * 10 + ["-"]
            if "Creature" in r.type_line:
                vals[2] = 1
        else:
            vals = raw[r.id]
        for key in r.keys.split(";"):
            rows.append([key, r.id, r.auto, r.mv] + vals)
    x = pd.DataFrame(rows, columns=["key", "id", "auto", "mv"] + FIELDS + ["dep"])
    if x["key"].duplicated().any():
        raise SystemExit("a key maps to two extraction rows")
    feats = c3_columns(x, x["mv"])
    out = pd.concat([x[["key", "id", "auto"]], x[FIELDS + ["dep"]], feats], axis=1)
    out.to_csv(C3_OUT, index=False, compression="gzip")
    print({"keys": len(out), "unique_rows": int(out["id"].nunique()), "auto_rows": int(out.loc[out.auto == 1, "id"].nunique()),
           "fra_keys": int(out["key"].str.startswith("FRA|").sum())})


def load_with_c3():
    d = g.load(FEAT)
    d["__text"] = g.text_of(d)
    base = g.numeric_cols(d)
    c3 = pd.read_csv(C3_OUT, keep_default_na=False)
    c3 = c3[~c3["key"].str.startswith("FRA|")].copy()
    d["key"] = d["set"] + "|" + d["name"]
    cols = [c for c in c3.columns if c.startswith("llm_")]
    d = d.merge(c3[["key"] + cols], on="key", how="left", validate="many_to_one")
    if d[cols].isna().any().any():
        raise SystemExit("C3 missing for some research cards")
    return d, base, cols


def cmd_compare(a):
    d, base, cols = load_with_c3()
    configs = {"baseline": base, "C3_llm_extract": base + cols}
    res = {"fin_used": False, "mh3_used": False, "seeds": SEEDS, "c3_columns": cols,
           "versions": {"sklearn": __import__("sklearn").__version__, "pandas": pd.__version__, "numpy": np.__version__},
           "configs": {}}
    oof = d[["set", "name", "rarity_ord", "actual_gih"]].copy()
    for name, nums in configs.items():
        runs = []
        for sd in SEEDS:
            p = g.loso(d, nums, seed=sd)
            runs.append(g.summarize(d, p))
            if sd == g.SEED:
                oof[f"pred_{name}"] = p
            oof[f"pred_{name}_s{sd}"] = p
            print(name, sd, round(runs[-1]["pooled"]["mae_pp"], 5), round(runs[-1]["within_set_mean"]["spearman"], 5), flush=True)
        res["configs"][name] = {"n_features": len(nums), "runs": runs}
    res["decision"] = decide(res["configs"]["baseline"]["runs"], res["configs"]["C3_llm_extract"]["runs"])
    res["coverage"] = {c: {"n_nonzero": int((d[c] != 0).sum()), "mean": float(d[c].mean())} for c in cols}
    a.out_dir.mkdir(parents=True, exist_ok=True)
    (a.out_dir / "compare.json").write_text(json.dumps(res, indent=2, default=float))
    oof.to_csv(a.out_dir / "compare_oof.csv.gz", index=False, compression="gzip")
    print(json.dumps(res["decision"], indent=2))


def agg(runs):
    def m(f):
        v = np.array([f(r) for r in runs])
        return {"mean": float(v.mean()), "range": float(v.max() - v.min()), "values": v.tolist()}
    return {
        "pooled_mae": m(lambda r: r["pooled"]["mae_pp"]),
        "pooled_spearman": m(lambda r: r["pooled"]["spearman"]),
        "within_mae": m(lambda r: r["within_set_mean"]["mae_pp"]),
        "within_spearman": m(lambda r: r["within_set_mean"]["spearman"]),
        "recall_mean": m(lambda r: (r["within_set_mean"]["strong_recall"] + r["within_set_mean"]["weak_recall"]) / 2),
        "tail_bias_sum": m(lambda r: abs(r["within_set_mean"]["top10_bias_pp"]) + abs(r["within_set_mean"]["bottom10_bias_pp"])),
        "top10_bias": m(lambda r: r["within_set_mean"]["top10_bias_pp"]),
        "bottom10_bias": m(lambda r: r["within_set_mean"]["bottom10_bias_pp"]),
        "sd_ratio": m(lambda r: r["within_set_mean"]["sd_ratio"]),
    }


def decide(base_runs, cand_runs):
    b, c = agg(base_runs), agg(cand_runs)
    r1 = c["pooled_mae"]["mean"] - b["pooled_mae"]["mean"] <= 0.005
    r2 = c["within_spearman"]["mean"] > b["within_spearman"]["mean"]
    rec_up = c["recall_mean"]["mean"] > b["recall_mean"]["mean"]
    tail_down = c["tail_bias_sum"]["mean"] < b["tail_bias_sum"]["mean"]
    r3 = rec_up or tail_down
    pb = pd.DataFrame(base_runs[0]["per_set"]).set_index("set")
    pc = pd.DataFrame(cand_runs[0]["per_set"]).set_index("set")
    mae_wins = int((pc["mae_pp"] < pb["mae_pp"]).sum())
    rho_wins = int((pc["spearman"] > pb["spearman"]).sum())
    r4 = mae_wins >= 12 or rho_wins >= 12
    gains = {
        "pooled_mae": (b["pooled_mae"]["mean"] - c["pooled_mae"]["mean"], b["pooled_mae"]["range"]),
        "within_spearman": (c["within_spearman"]["mean"] - b["within_spearman"]["mean"], b["within_spearman"]["range"]),
        "recall_mean": (c["recall_mean"]["mean"] - b["recall_mean"]["mean"], b["recall_mean"]["range"]),
        "tail_bias_sum": (b["tail_bias_sum"]["mean"] - c["tail_bias_sum"]["mean"], b["tail_bias_sum"]["range"]),
    }
    # Rule 5: every gain claimed by rules 2-3 must exceed the baseline seed-to-seed range; a claimed MAE gain as well.
    claimed = ["within_spearman"] + (["recall_mean"] if rec_up else []) + (["tail_bias_sum"] if tail_down else [])
    if gains["pooled_mae"][0] > 0:
        claimed.append("pooled_mae")
    r5 = all(gains[k][0] > gains[k][1] for k in claimed) and r2
    return {"baseline": b, "candidate": c,
            "rules": {"1_mae_not_worse": r1, "2_within_spearman_up": r2, "3_tail_improves": r3,
                      "3_detail": {"recall_up": rec_up, "tail_bias_down": tail_down},
                      "4_set_stability": r4, "4_detail": {"mae_wins": mae_wins, "spearman_wins": rho_wins, "of": len(pb)},
                      "5_beyond_seed_noise": r5,
                      "5_detail": {k: {"gain": v[0], "baseline_range": v[1]} for k, v in gains.items()}},
            "promising": bool(r1 and r2 and r3 and r4 and r5)}


# ---------- frozen FRA predictions ----------
def symbols(m):
    return "".join("{" + s.strip("()").upper() + "}" for s in m.group(1).split("o") if s)


def normalize(card):
    c = dict(card)
    for k in ("oracle_text", "type_line", "name"):
        c[k] = re.sub(r"\{o([^}]*)\}", symbols, (c.get(k) or "").replace("’", "'").replace("\r\n", "\n"))
    if c.get("rarity") == "land":
        c["rarity"] = "common"
    return c


def fit_predict(train, test, nums, seed):
    y = train["actual_gih"]
    tree = make_pipeline(SimpleImputer(strategy="median"),
                         ExtraTreesRegressor(n_estimators=600, min_samples_leaf=8, max_features=.6, n_jobs=-1, random_state=seed))
    tree.fit(train[nums], y)
    text = make_pipeline(TfidfVectorizer(ngram_range=(1, 2), min_df=3, max_features=12000, sublinear_tf=True), Ridge(alpha=10))
    text.fit(train["__text"], y)
    raw = .7 * tree.predict(test[nums]) + .3 * text.predict(test["__text"])
    center = float(y.mean())
    return center + 1.25 * (raw - center)


def cmd_freeze(a):
    d, base, cols = load_with_c3()
    fra = json.loads(gzip.open(a.fra, "rt", encoding="utf-8").read())["cards"]
    norm = [normalize(c) for c in fra]
    f = pd.DataFrame([card_features(c) for c in norm])
    f["oracle_text"] = [c["oracle_text"] for c in norm]
    f["type_line"] = [c["type_line"] for c in norm]
    f["__text"] = g.text_of(f)
    # Set-metadata columns kept from the MH3-era table are constant over the 21 sets (trees never split on them).
    for c in ("is_supplemental_power_set", "is_premier_set"):
        if c not in f.columns:
            const = d[c].unique()
            if len(const) != 1:
                raise SystemExit(f"{c} is not constant in training")
            f[c] = const[0]
    missing = [c for c in base if c not in f.columns]
    if missing:
        raise SystemExit(f"FRA feature table lacks {missing}")
    c3 = pd.read_csv(C3_OUT, keep_default_na=False).set_index("key")
    keys = [f"FRA|{c['id']}" for c in fra]
    if any(k not in c3.index for k in keys):
        raise SystemExit("C3 missing for some FRA cards")
    for c in cols:
        f[c] = c3.loc[keys, c].to_numpy(dtype=float)
    pb = np.mean([fit_predict(d, f, base, sd) for sd in SEEDS], axis=0)
    pc = np.mean([fit_predict(d, f, base + cols, sd) for sd in SEEDS], axis=0)
    out = pd.DataFrame({"id": [c["id"] for c in fra], "name": [c["name"] for c in fra],
                        "rarity": [c.get("rarity") for c in fra],
                        "pred_baseline21_pp": np.round(pb * 100, 3), "pred_c3_pp": np.round(pc * 100, 3)})
    for c in ["llm_removal", "llm_sweeper", "llm_bodies", "llm_cards", "llm_dependency", "llm_drawback", "llm_impact"]:
        out[c] = f[c].to_numpy()
    path = HERE / "fra_frozen_predictions.csv"
    out.to_csv(path, index=False)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    meta = {"frozen_at_utc": pd.Timestamp.utcnow().isoformat(), "fin_used": False, "mh3_used": False,
            "fra_outcomes_used": False, "train_sets": sorted(set(d["set"])), "seeds": SEEDS, "n_cards": len(out),
            "file": path.name, "sha256": digest,
            "note": "Both arms fit on all 21 research sets; seed-averaged. Compare against FRA 28-day Public Data when available."}
    (HERE / "fra_frozen_predictions.json").write_text(json.dumps(meta, indent=2))
    print(json.dumps(meta, indent=2))
    print(out[["pred_baseline21_pp", "pred_c3_pp"]].describe().round(3))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("features")
    c = sub.add_parser("compare"); c.add_argument("--out-dir", type=Path, default=HERE)
    z = sub.add_parser("freeze"); z.add_argument("--fra", type=Path, required=True)
    a = ap.parse_args()
    {"features": cmd_features, "compare": cmd_compare, "freeze": cmd_freeze}[a.cmd](a)


if __name__ == "__main__":
    main()
