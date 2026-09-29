#!/usr/bin/env python3
"""FIN final holdout check for the GIH WR model (see PLAN.md).

  python fin_final.py c3-build                  # blind C3 queue from data/fin_cards_text.csv.gz (no outcomes)
  python fin_final.py --show N                  # print batch N (blinded)
  python fin_final.py c3-check                  # validate c3_raw/f*.txt coverage
  python fin_final.py c3-features               # -> c3_features_fin.csv.gz
  python fin_final.py score --dry-run --out-dir DIR     # synthetic outcomes; code-path test only
  python fin_final.py score --aggregate data/FIN_case6_28d.csv   # the one real run (Actions)

The model and arms are locked in PLAN.md. The real score refuses to run twice.
"""
import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
EXT = ROOT / "research/gih_llm_extract"
C6 = ROOT / "research/case6"
for p in (ROOT / "scripts", EXT, C6):
    sys.path.insert(0, str(p))
import gih21_research as g  # noqa: E402
import c3_research as c3  # noqa: E402
from build_input import blind, fmt_num  # noqa: E402
import c3_queue as q6  # noqa: E402
import case6_research as c6  # noqa: E402

DATA = HERE / "data"
TEXT = DATA / "fin_cards_text.csv.gz"
FEATS = DATA / "fin_scryfall_features.csv.gz"
CARDS = HERE / "c3_cards_fin.csv.gz"
C3_FIN = HERE / "c3_features_fin.csv.gz"
RAW = HERE / "c3_raw"
QSEED = 20261001
BATCH = 150
START_ID = 20001
SEEDS = c3.SEEDS
BOOT = 2000
BOOT_SEED = 20261001
ARMS = {  # name: (training pool, feature set)
    "P_adopted_21": ("21", "base"),
    "F_c3_28": ("28", "c3"),
    "P28_base_28": ("28", "base"),
    "C21_c3_21": ("21", "c3"),
}


# ---------------- blind C3 extraction ----------------
def sig(btext, type_line, mv, pt):
    return f"{btext}␟{type_line}␟{mv}␟{pt}"


def known():
    """Signature -> extracted values from case 1 and case 6 (extracted rows only; auto rows are rebuilt)."""
    out = {}
    old = pd.read_csv(EXT / "cards.csv.gz", keep_default_na=False)
    r1 = c3.read_raw()
    for r in old.itertuples():
        if int(r.id) in r1:
            out.setdefault(sig(r.btext, r.type_line, str(r.mv), r.pt), ("case1", int(r.id)))
    new = pd.read_csv(C6 / "c3_cards_new.csv.gz", keep_default_na=False)
    r6 = q6.read_raw()
    for r in new.itertuples():
        if int(r.id) in r6:
            out.setdefault(sig(r.btext, r.type_line, str(r.mv), r.pt), ("case6", int(r.id)))
    return out, r1, r6


def c3_build():
    t = pd.read_csv(TEXT, keep_default_na=False)
    if set(t["set"].str.upper()) != {"FIN"}:
        raise SystemExit("text file must be FIN only")
    t["type_line"] = t["type_line"].astype(str)
    t["text"] = t["oracle_text"].astype(str)
    t["mv"] = [fmt_num(x) for x in t["mv"]]
    t["pt"] = [f"{fmt_num(p)}/{fmt_num(q)}" for p, q in zip(t["power"], t["toughness"])]
    t["pt"] = t["pt"].where(t["pt"] != "/", "")
    t["colors"] = ["".join(c for c in "WUBRG" if str(r[f"color_{c}"]) in ("1", "1.0")) for _, r in t.iterrows()]
    t["btext"] = [blind(x, n, ty) for x, n, ty in zip(t["text"], t["name"], t["type_line"])]
    t["key"] = "FIN|" + t["name"]
    t["sig"] = [sig(*v) for v in zip(t["btext"], t["type_line"], t["mv"], t["pt"])]
    kn, _, _ = known()
    u = t.groupby("sig", sort=True).agg(keys=("key", lambda k: ";".join(sorted(k))), type_line=("type_line", "first"),
                                         btext=("btext", "first"), mv=("mv", "first"), colors=("colors", "first"),
                                         pt=("pt", "first")).reset_index()
    u["reuse"] = [f"{kn[s][0]}:{kn[s][1]}" if s in kn else "" for s in u["sig"]]
    u["auto"] = np.where(u["type_line"].str.contains("Basic Land") | (u["btext"].str.strip() == ""), 1, 0)
    u.loc[u["auto"] == 1, "reuse"] = ""
    rng = np.random.default_rng(QSEED)
    u = u.iloc[rng.permutation(len(u))].reset_index(drop=True)
    u["id"] = np.arange(START_ID, START_ID + len(u))
    u.drop(columns=["sig"]).to_csv(CARDS, index=False, compression="gzip")
    todo = u[(u["auto"] == 0) & (u["reuse"] == "")]
    print({"cards": len(t), "unique": len(u), "reused": int((u["reuse"] != "").sum()), "auto": int(u["auto"].sum()),
           "to_extract": len(todo), "batches": int(np.ceil(len(todo) / BATCH))})


def queue():
    u = pd.read_csv(CARDS, keep_default_na=False)
    return u[(u["auto"] == 0) & (u["reuse"] == "")].reset_index(drop=True)


def show(n):
    part = queue().iloc[n * BATCH:(n + 1) * BATCH]
    for r in part.itertuples():
        head = f"#{r.id} | MV {r.mv} {r.colors or 'C'} | {r.type_line}" + (f" | {r.pt}" if r.pt else "")
        print(head + "\n" + r.btext.replace("\n", " / ") + "\n")
    print(f"-- batch {n}: ids {part['id'].min()}..{part['id'].max()}, {len(part)} cards")


def read_raw():
    out = {}
    for f in sorted(RAW.glob("f*.txt")):
        for ln in f.read_text().splitlines():
            if not ln.strip():
                continue
            m = c3.LINE.match(ln.strip())
            if not m:
                raise SystemExit(f"bad line in {f.name}: {ln!r}")
            d = [int(x) for x in m.group(2)]
            if any(v > mx for v, mx in zip(d, c3.MAX)) or m.group(3) not in "-" + "".join(c3.DEPS):
                raise SystemExit(f"out of range in {f.name}: {ln!r}")
            if int(m.group(1)) in out:
                raise SystemExit(f"duplicate {m.group(1)}")
            out[int(m.group(1))] = d + [m.group(3)]
    return out


def c3_check():
    raw = read_raw()
    want = set(queue()["id"])
    rep = {"annotated": len(raw), "want": len(want), "missing": len(want - set(raw)), "extra": len(set(raw) - want)}
    print(rep)
    return rep


def c3_features():
    raw = read_raw()
    _, r1, r6 = known()
    u = pd.read_csv(CARDS, keep_default_na=False)
    if c3_check()["missing"]:
        raise SystemExit("extraction incomplete")
    rows = []
    for r in u.itertuples():
        if r.auto:
            vals = [0] * 10 + ["-"]
            if "Creature" in r.type_line:
                vals[2] = 1
        elif r.reuse:
            src, i = r.reuse.split(":")
            vals = (r1 if src == "case1" else r6)[int(i)]
        else:
            vals = raw[r.id]
        for key in r.keys.split(";"):
            rows.append([key, r.id, r.auto, r.mv] + list(vals))
    x = pd.DataFrame(rows, columns=["key", "id", "auto", "mv"] + c3.FIELDS + ["dep"])
    feats = c3.c3_columns(x, x["mv"])
    out = pd.concat([x[["key", "id", "auto"]], x[c3.FIELDS + ["dep"]], feats], axis=1)
    out.to_csv(C3_FIN, index=False, compression="gzip")
    print({"keys": len(out), "mean_llm_impact": round(float(out["llm_impact"].mean()), 3)})


# ---------------- scoring ----------------
def load_fin(agg, base, cols):
    f = pd.read_csv(FEATS)
    f["set"] = "FIN"
    f["sf_name"] = f["name"]
    f["front"] = f["name"].str.split(" // ").str[0]
    a = agg.rename(columns={"card_name": "name", "gih_wr": "actual_gih"})
    if set(a["set"].astype(str).str.upper()) != {"FIN"}:
        raise SystemExit("aggregate must be FIN only")
    a = a.drop(columns=["set"])
    exact = a.merge(f.drop(columns=["front"]), on="name", how="inner")
    rest = a[~a["name"].isin(exact["name"])]
    f2 = f[~f["name"].isin(exact["name"])].drop_duplicates("front")
    front = rest.merge(f2.drop(columns=["name"]).rename(columns={"front": "name"}), on="name", how="inner")
    m = pd.concat([exact, front], ignore_index=True)
    if m["name"].duplicated().any():
        raise SystemExit("duplicate FIN card after matching")
    report = {"aggregate_cards": len(a), "matched_exact": len(exact), "matched_front_face": len(front),
              "unmatched_n": int(len(a) - len(m)), "unmatched": sorted(set(a["name"]) - set(m["name"]))}
    m["__text"] = g.text_of(m)
    missing = [c for c in base if c not in m.columns]
    if missing:
        raise SystemExit(f"FIN table lacks {missing}")
    x = pd.read_csv(C3_FIN, keep_default_na=False)
    m["key"] = "FIN|" + m["sf_name"]
    m = m.merge(x[["key"] + cols], on="key", how="left", validate="many_to_one")
    if m[cols].isna().any().any():
        raise SystemExit("C3 missing for some FIN cards")
    return m, report


def metrics(fin, p):
    s, _ = g.within_set(fin.assign(set="FIN"), p)
    s["tail_bias_sum"] = abs(s["top10_bias_pp"]) + abs(s["bottom10_bias_pp"])
    s["recall_mean"] = (s["strong_recall"] + s["weak_recall"]) / 2
    return {k: float(v) for k, v in s.items()}


def bootstrap(y, pa, pb):
    rng = np.random.default_rng(BOOT_SEED)
    n = len(y)
    dm, ds = np.empty(BOOT), np.empty(BOOT)
    for i in range(BOOT):
        idx = rng.integers(0, n, n)
        yy, a, b = y[idx], pa[idx], pb[idx]
        dm[i] = (np.mean(np.abs(b - yy)) - np.mean(np.abs(a - yy))) * 100
        ds[i] = spearmanr(yy, b).statistic - spearmanr(yy, a).statistic
    return {"mae_diff_pp_F_minus_P": {"p05": float(np.percentile(dm, 5)), "p50": float(np.percentile(dm, 50)),
                                      "p95": float(np.percentile(dm, 95)), "share_F_better": float((dm < 0).mean())},
            "spearman_diff_F_minus_P": {"p05": float(np.percentile(ds, 5)), "p50": float(np.percentile(ds, 50)),
                                        "p95": float(np.percentile(ds, 95)), "share_F_better": float((ds > 0).mean())},
            "resamples": BOOT, "seed": BOOT_SEED, "basis": "seed-averaged predictions"}


def score(a):
    out_dir = a.out_dir or HERE
    result = out_dir / "fin_result.json"
    if not a.dry_run and result.exists():
        raise SystemExit("FIN has already been scored; the final check runs once")
    d, base, cols = c3.load_with_c3()
    n = c6.load_new(base, cols)
    if a.dry_run:
        f = pd.read_csv(FEATS)
        rng = np.random.default_rng(0)
        agg = pd.DataFrame({"set": "FIN", "card_name": f["name"].str.split(" // ").str[0], "gih_games": 1000, "gih_wins": 0,
                            "gih_wr": 0.55 + rng.normal(0, 0.035, len(f))})
    else:
        agg = pd.read_csv(a.aggregate)
    fin, report = load_fin(agg, base, cols)
    pools = {"21": d, "28": pd.concat([d, n], ignore_index=True)}
    for k, t in pools.items():
        if "FIN" in set(t["set"].str.upper()):
            raise SystemExit("FIN in training")
    y = fin["actual_gih"].to_numpy(float)
    res = {"dry_run": bool(a.dry_run), "fin_used_for_training": False, "mh3_used": False, "fra_used": False,
           "github_sha": os.environ.get("GITHUB_SHA"), "seeds": SEEDS,
           "versions": {"sklearn": __import__("sklearn").__version__, "pandas": pd.__version__, "numpy": np.__version__},
           "train_sets": {k: sorted(set(t["set"])) for k, t in pools.items()}, "fin_cards": len(fin), "match": report,
           "arms": {}}
    preds = fin[["set", "name", "rarity_ord", "actual_gih", "gih_games"]].copy()
    avg = {}
    for name, (pool, feat) in ARMS.items():
        nums = base if feat == "base" else base + cols
        ps = [c3.fit_predict(pools[pool], fin, nums, sd) for sd in SEEDS]
        runs = [metrics(fin, p) for p in ps]
        avg[name] = np.mean(ps, axis=0)
        preds[f"pred_{name}"] = avg[name]
        mean = {k: float(np.mean([r[k] for r in runs])) for k in runs[0]}
        rng_ = {k: float(np.ptp([r[k] for r in runs])) for k in runs[0]}
        by_rarity = {int(r): float(np.mean(np.abs(avg[name][fin["rarity_ord"].to_numpy() == r] - y[fin["rarity_ord"].to_numpy() == r])) * 100)
                     for r in sorted(fin["rarity_ord"].dropna().unique())}
        res["arms"][name] = {"training": pool, "features": feat, "n_features": len(nums), "runs": runs, "mean": mean,
                             "seed_range": rng_, "seed_avg": metrics(fin, avg[name]), "mae_by_rarity_seed_avg": by_rarity}
        print(name, "done", flush=True)
    P, F = res["arms"]["P_adopted_21"]["mean"], res["arms"]["F_c3_28"]["mean"]
    rules = {"mae_improves": F["mae_pp"] < P["mae_pp"], "spearman_not_down": F["spearman"] >= P["spearman"]}
    res["rule_F"] = {"P": {k: P[k] for k in ("mae_pp", "spearman", "bias_pp")}, "F": {k: F[k] for k in ("mae_pp", "spearman", "bias_pp")},
                     "mae_change_pp": F["mae_pp"] - P["mae_pp"], "spearman_change": F["spearman"] - P["spearman"],
                     "P_seed_range": {k: res["arms"]["P_adopted_21"]["seed_range"][k] for k in ("mae_pp", "spearman")},
                     "rules": rules, "confirmed": bool(all(rules.values()))}
    res["bootstrap"] = bootstrap(y, avg["P_adopted_21"], avg["F_c3_28"])
    out_dir.mkdir(parents=True, exist_ok=True)
    result.write_text(json.dumps(res, indent=2, default=float))
    preds.to_csv(out_dir / "fin_predictions.csv.gz", index=False, compression="gzip")
    print(json.dumps({"dry_run": res["dry_run"], "fin_cards": res["fin_cards"], "rule_F_confirmed": res["rule_F"]["confirmed"]}))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", nargs="?", choices=["c3-build", "c3-check", "c3-features", "score"])
    ap.add_argument("--show", type=int)
    ap.add_argument("--aggregate", type=Path)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--out-dir", type=Path)
    a = ap.parse_args()
    if a.show is not None:
        return show(a.show)
    if a.cmd == "score":
        if a.dry_run == bool(a.aggregate):
            raise SystemExit("score needs exactly one of --dry-run or --aggregate")
        if a.dry_run and (a.out_dir is None or a.out_dir.resolve() == HERE):
            raise SystemExit("dry run must write outside the research folder")
        return score(a)
    {"c3-build": c3_build, "c3-check": c3_check, "c3-features": c3_features}[a.cmd]()


if __name__ == "__main__":
    main()
