#!/usr/bin/env python3
"""DA1 aggregation: raw and deck / player / colour adjusted GIH from 17Lands Public Game Data (Premier Draft).

Same download, 28-day window (earliest draft_time + 28 d) and card definition (opening_hand / drawn / tutored) as
scripts/case6_aggregate.py and aggregate_17lands.py. Per card (GIH games >= 500):
  gih_games, gih_wins                      raw (must equal data/compact_28d)
  dadj_n, dadj_sum, dadj_sumsq, dadj_wins  games whose draft has >= 1 other game; sum of (won - leave-one-out draft win rate)
  padj_n, padj_sum                         won - user_game_win_rate_bucket (blank column -> 0 games)
  cadj_n, cadj_sum                         won - win rate of the game's main_colors over all window games of the set
FIN, MH3, FRA are refused.
"""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

import case6_aggregate as c6

REFUSE = {"FIN", "MH3", "FRA"}
PREFIXES = c6.PREFIXES


def hash_ids(s):
    return pd.util.hash_pandas_object(s.astype(str), index=False).to_numpy()


def pass1(path, days, chunksize, has_colors):
    start, end = c6.first_window(path, days, chunksize)
    cols = ["draft_time", "draft_id", "won"] + (["main_colors"] if has_colors else [])
    H, W, C = [], [], []
    for c in pd.read_csv(path, usecols=cols, chunksize=chunksize, compression="gzip", low_memory=False):
        t = pd.to_datetime(c["draft_time"], errors="coerce", utc=True)
        m = ((t >= start) & (t < end)).to_numpy()
        if not m.any():
            continue
        c = c.loc[m]
        H.append(hash_ids(c["draft_id"]))
        W.append(c["won"].astype(str).str.strip().str.lower().isin(["true", "1", "1.0"]).to_numpy())
        if has_colors:
            C.append(c["main_colors"].fillna("").astype(str).to_numpy())
    H = np.concatenate(H)
    W = np.concatenate(W)
    uh, inv = np.unique(H, return_inverse=True)
    dn = np.bincount(inv).astype(np.int64)
    dw = np.bincount(inv, weights=W.astype(float)).astype(np.int64)
    colors = {}
    if has_colors:
        Cc = np.concatenate(C)
        df = pd.DataFrame({"c": Cc, "w": W}).groupby("c")["w"].agg(["sum", "count"])
        colors = {k: (int(r["sum"]), int(r["count"])) for k, r in df.iterrows()}
    return start, end, uh, dn, dw, colors, int(len(H))


def aggregate(s, path, days, min_games, chunksize):
    h = c6.header(path)
    for need in ("draft_time", "won", "draft_id"):
        if need not in h:
            raise RuntimeError(f"required column missing: {need}")
    has_wr = "user_game_win_rate_bucket" in h
    has_col = "main_colors" in h
    cards = sorted({col[len(p):] for col in h for p in PREFIXES if col.startswith(p)})
    pos = {c: i for i, c in enumerate(cards)}
    percol = {p: [(f"{p}{c}", pos[c]) for c in cards if f"{p}{c}" in h] for p in PREFIXES}
    start, end, uh, dn, dw, colors, ngames = pass1(path, days, chunksize, has_col)
    cwr = {k: v[0] / v[1] for k, v in colors.items()}
    meta = ["draft_time", "won", "draft_id"] + (["user_game_win_rate_bucket"] if has_wr else []) + (["main_colors"] if has_col else [])
    usecols = meta + [c for p in PREFIXES for c, _ in percol[p]]
    K = len(cards)
    names = ["g", "w", "dn", "dw", "dsum", "dsq", "pn", "psum", "cn", "csum"]
    acc = {n: np.zeros(K, np.float64) for n in names}
    for c in pd.read_csv(path, usecols=usecols, chunksize=chunksize, compression="gzip", low_memory=False):
        t = pd.to_datetime(c["draft_time"], errors="coerce", utc=True)
        m = ((t >= start) & (t < end)).to_numpy()
        if not m.any():
            continue
        c = c.loc[m]
        won = c["won"].astype(str).str.strip().str.lower().isin(["true", "1", "1.0"]).to_numpy()
        P = np.zeros((len(c), K), bool)
        for p in PREFIXES:
            if percol[p]:
                nm = [n for n, _ in percol[p]]
                idx = [i for _, i in percol[p]]
                P[:, idx] |= c[nm].apply(pd.to_numeric, errors="coerce").fillna(0).to_numpy() != 0
        hh = hash_ids(c["draft_id"])
        j = np.searchsorted(uh, hh)
        assert (uh[j] == hh).all()
        n_d, w_d = dn[j], dw[j]
        wf = won.astype(float)
        valid = n_d >= 2
        base = np.where(valid, (w_d - wf) / np.maximum(n_d - 1, 1), 0.0)
        dad = np.where(valid, wf - base, 0.0)
        if has_wr:
            wr = pd.to_numeric(c["user_game_win_rate_bucket"], errors="coerce").to_numpy()
            pv = ~np.isnan(wr)
            pad = np.where(pv, wf - np.nan_to_num(wr), 0.0)
        else:
            pv = np.zeros(len(c), bool)
            pad = np.zeros(len(c))
        if has_col:
            cw = c["main_colors"].fillna("").astype(str).map(cwr).to_numpy(dtype=float)
            cv = ~np.isnan(cw)
            cad = np.where(cv, wf - np.nan_to_num(cw), 0.0)
        else:
            cv = np.zeros(len(c), bool)
            cad = np.zeros(len(c))
        M = np.column_stack([np.ones(len(c)), wf, valid, wf * valid, dad, dad ** 2, pv, pad, cv, cad]).astype(np.float64)
        Pf = P.astype(np.float32)
        R = Pf.T.astype(np.float64) @ M
        acc["g"] += R[:, 0]; acc["w"] += R[:, 1]; acc["dn"] += R[:, 2]; acc["dw"] += R[:, 3]
        acc["dsum"] += R[:, 4]; acc["dsq"] += R[:, 5]; acc["pn"] += R[:, 6]; acc["psum"] += R[:, 7]
        acc["cn"] += R[:, 8]; acc["csum"] += R[:, 9]
    rows = []
    for i, card in enumerate(cards):
        if acc["g"][i] < min_games:
            continue
        rows.append({"set": s, "card_name": card, "gih_games": int(acc["g"][i]), "gih_wins": int(acc["w"][i]),
                     "dadj_n": int(acc["dn"][i]), "dadj_wins": int(acc["dw"][i]), "dadj_sum": acc["dsum"][i], "dadj_sumsq": acc["dsq"][i],
                     "padj_n": int(acc["pn"][i]), "padj_sum": acc["psum"][i], "cadj_n": int(acc["cn"][i]), "cadj_sum": acc["csum"][i]})
    # check against stored aggregate
    chk = {"compared": False}
    ref = Path("data/compact_28d") / f"{s}_gih_28d.csv"
    if ref.exists():
        r = pd.read_csv(ref)[["card_name", "gih_games", "gih_wins"]]
        d = pd.DataFrame(rows)[["card_name", "gih_games", "gih_wins"]].merge(r, on="card_name", how="outer", suffixes=("", "_ref"), indicator=True)
        both = d[d["_merge"] == "both"]
        chk = {"compared": True, "cards_new": int(len(rows)), "cards_ref": int(len(r)), "cards_only_new": int((d["_merge"] == "left_only").sum()),
               "cards_only_ref": int((d["_merge"] == "right_only").sum()),
               "games_mismatch": int((both["gih_games"] != both["gih_games_ref"]).sum()), "wins_mismatch": int((both["gih_wins"] != both["gih_wins_ref"]).sum()),
               "max_abs_games_diff": int((both["gih_games"] - both["gih_games_ref"]).abs().max()) if len(both) else None}
    ndr = int((dn >= 2).sum())
    man = {"set": s, "window_start": start.isoformat(), "window_end": end.isoformat(), "window_days": days, "games_in_window": ngames,
           "drafts_in_window": int(len(uh)), "games_in_drafts_with_other_game": int(dn[dn >= 2].sum()), "has_user_wr_bucket": has_wr,
           "has_main_colors": has_col, "cards_output": len(rows), "raw_check": chk, "n_main_colors": len(colors)}
    return rows, man


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", required=True)
    ap.add_argument("--days", type=int, default=28)
    ap.add_argument("--min-games", type=int, default=500)
    ap.add_argument("--chunksize", type=int, default=20000)
    ap.add_argument("--out-dir", type=Path, default=Path("out"))
    ap.add_argument("--local", type=Path, default=None, help="use this local csv.gz instead of downloading (tests)")
    a = ap.parse_args()
    s = a.set.upper()
    if s in REFUSE:
        raise SystemExit(f"{s} is not allowed")
    a.out_dir.mkdir(parents=True, exist_ok=True)
    raw = a.local or (a.out_dir / f"game_data_public.{s}.{c6.FMT}.csv.gz")
    if a.local is None:
        c6.download(s, raw)
    rows, man = aggregate(s, raw, a.days, a.min_games, a.chunksize)
    pd.DataFrame(rows).to_csv(a.out_dir / f"{s}_da1.csv", index=False)
    (a.out_dir / f"{s}_da1_manifest.json").write_text(json.dumps(man, indent=2))
    if a.local is None:
        raw.unlink(missing_ok=True)
    print(json.dumps(man))


if __name__ == "__main__":
    main()
