#!/usr/bin/env python3
"""Deck colour step 1: pair win rates and per-card GIH by deck pair from 17Lands Public Game Data (Premier Draft).
Window and card logic as scripts/case6_aggregate.py. FIN, MH3 and FRA are refused. See research/deck_pair/PLAN.md."""
import argparse, json, sys
from pathlib import Path
import numpy as np, pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from case6_aggregate import download, header, first_window, sha256_file, url_for, PREFIXES, FMT  # noqa: E402

REFUSE = {"FIN", "MH3", "FRA"}
ORDER = "WUBRG"
PAIRS = ["WU", "WB", "WR", "WG", "UB", "UR", "UG", "BR", "BG", "RG"]
GROUPS = PAIRS + ["other"]


def norm(s):
    s = "" if pd.isna(s) else str(s)
    return "".join(c for c in ORDER if c in s)


def aggregate(s, path, days, chunksize):
    h = header(path)
    for k in ("draft_time", "won", "main_colors", "splash_colors", "draft_id"):
        if k not in h:
            raise RuntimeError(f"missing {k}")
    cards = sorted({col[len(p):] for col in h for p in PREFIXES if col.startswith(p)})
    pos = {c: i for i, c in enumerate(cards)}
    percol = {p: [(f"{p}{c}", pos[c]) for c in cards if f"{p}{c}" in h] for p in PREFIXES}
    usecols = ["draft_time", "won", "main_colors", "splash_colors", "draft_id"] + [c for p in PREFIXES for c, _ in percol[p]]
    start, end = first_window(path, days, chunksize)
    G = np.zeros((len(GROUPS), len(cards)), np.int64)
    W = np.zeros((len(GROUPS), len(cards)), np.int64)
    deck = {}
    for c in pd.read_csv(path, usecols=usecols, chunksize=chunksize, compression="gzip", low_memory=False):
        t = pd.to_datetime(c["draft_time"], errors="coerce", utc=True)
        m = ((t >= start) & (t < end)).to_numpy()
        if not m.any():
            continue
        c = c.loc[m]
        won = c["won"].astype(str).str.strip().str.lower().isin(["true", "1", "1.0"]).to_numpy()
        main = c["main_colors"].map(norm).to_numpy()
        spl = (c["splash_colors"].map(norm) != "").to_numpy()
        half = (pd.util.hash_pandas_object(c["draft_id"].astype(str), index=False).to_numpy() % 2).astype(int)
        key = pd.DataFrame({"main": main, "splash": spl, "half": half, "won": won})
        for (mc, sp, hf), g in key.groupby(["main", "splash", "half"]):
            d = deck.setdefault((mc, bool(sp), int(hf)), [0, 0])
            d[0] += len(g); d[1] += int(g["won"].sum())
        P = np.zeros((len(c), len(cards)), bool)
        for p in PREFIXES:
            if percol[p]:
                names = [n for n, _ in percol[p]]
                idx = [i for _, i in percol[p]]
                P[:, idx] |= c[names].apply(pd.to_numeric, errors="coerce").fillna(0).to_numpy() != 0
        gi = np.array([PAIRS.index(x) if x in PAIRS else len(PAIRS) for x in main])
        for k in range(len(GROUPS)):
            mk = gi == k
            if mk.any():
                G[k] += P[mk].sum(0)
                W[k] += P[mk & won].sum(0)
    pairs = pd.DataFrame([{"set": s, "main_colors": k[0], "splash": k[1], "half": k[2], "games": v[0], "wins": v[1]}
                          for k, v in sorted(deck.items())])
    rows = []
    for i, card in enumerate(cards):
        if G[:, i].sum() == 0:
            continue
        r = {"set": s, "card_name": card}
        for k, g in enumerate(GROUPS):
            r[f"{g}_games"] = int(G[k, i]); r[f"{g}_wins"] = int(W[k, i])
        rows.append(r)
    man = {"set": s, "source_url": url_for(s), "sha256": sha256_file(path), "window_start": start.isoformat(),
           "window_end": end.isoformat(), "games": int(pairs["games"].sum()), "cards": len(rows)}
    return pairs, pd.DataFrame(rows), man


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", required=True)
    ap.add_argument("--days", type=int, default=28)
    ap.add_argument("--chunksize", type=int, default=20000)
    ap.add_argument("--out-dir", type=Path, default=Path("out"))
    a = ap.parse_args()
    s = a.set.upper()
    if s in REFUSE:
        raise SystemExit(f"{s} refused")
    a.out_dir.mkdir(parents=True, exist_ok=True)
    raw = a.out_dir / f"game_data_public.{s}.{FMT}.csv.gz"
    download(s, raw)
    pairs, cp, man = aggregate(s, raw, a.days, a.chunksize)
    pairs.to_csv(a.out_dir / f"{s}_pairs.csv", index=False)
    cp.to_csv(a.out_dir / f"{s}_cardpair.csv.gz", index=False)
    (a.out_dir / f"{s}_pair_manifest.json").write_text(json.dumps(man, indent=2))
    raw.unlink(missing_ok=True)
    print(json.dumps(man))


if __name__ == "__main__":
    main()
