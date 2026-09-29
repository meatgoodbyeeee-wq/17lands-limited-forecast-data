#!/usr/bin/env python3
"""Case 6 aggregation: overall and top-player GIH WR from the official 17Lands Public Game Data (Premier Draft).

Same card logic and 28-day window as scripts/aggregate_17lands.py (a card counts once per game if it was in the
opening hand, drawn or tutored; window = earliest draft_time + 28 days). Adds, per card, games/wins for player groups:

  all          every game (reproduces the stored compact_28d numbers)
  top60n50     user_game_win_rate_bucket >= 0.60 and user_n_games_bucket >= 50   (primary top-player target)
  top56n50     >= 0.56 and n >= 50   (sensitivity)
  top64n50     >= 0.64 and n >= 50   (sensitivity)
  top60        >= 0.60, any n        (sensitivity)
  all_h0/h1, top60n50_h0/h1   split halves by a fixed hash of draft_id (reliability)

FIN, MH3 and FRA are refused. Sets without the win-rate bucket column get zero counts for the top groups.
"""
import argparse
import csv
import gzip
import hashlib
import json
from pathlib import Path
from urllib.request import Request, urlopen

import numpy as np
import pandas as pd

BASE = "https://17lands-public.s3.amazonaws.com/analysis_data/game_data"
FMT = "PremierDraft"
REFUSE = {"FIN", "MH3", "FRA"}
PREFIXES = ("opening_hand_", "drawn_", "tutored_")
GROUPS = ["all", "all_h0", "all_h1", "top60n50", "top60n50_h0", "top60n50_h1", "top56n50", "top64n50", "top60"]


def url_for(s):
    return f"{BASE}/game_data_public.{s}.{FMT}.csv.gz"


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def download(s, dest):
    req = Request(url_for(s), headers={"User-Agent": "SakiyomiResearch/1.0"})
    tmp = dest.with_suffix(dest.suffix + ".part")
    with urlopen(req, timeout=300) as r, open(tmp, "wb") as out:
        for b in iter(lambda: r.read(1 << 20), b""):
            out.write(b)
    tmp.replace(dest)


def header(path):
    with gzip.open(path, "rt", encoding="utf-8-sig", newline="") as f:
        return next(csv.reader(f))


def first_window(path, days, chunksize):
    earliest = None
    for c in pd.read_csv(path, usecols=["draft_time"], chunksize=chunksize, compression="gzip"):
        v = pd.to_datetime(c["draft_time"], errors="coerce", utc=True).min()
        if pd.notna(v) and (earliest is None or v < earliest):
            earliest = v
    if earliest is None:
        raise RuntimeError("no valid draft_time")
    return earliest, earliest + pd.Timedelta(days=days)


def aggregate(s, path, days, min_games, chunksize):
    h = header(path)
    if "draft_time" not in h or "won" not in h:
        raise RuntimeError("required columns missing")
    cards = sorted({col[len(p):] for col in h for p in PREFIXES if col.startswith(p)})
    pos = {c: i for i, c in enumerate(cards)}
    percol = {p: [(f"{p}{c}", pos[c]) for c in cards if f"{p}{c}" in h] for p in PREFIXES}
    has_wr = "user_game_win_rate_bucket" in h
    has_n = "user_n_games_bucket" in h
    meta = ["draft_time", "won", "draft_id"] + (["user_game_win_rate_bucket"] if has_wr else []) + (["user_n_games_bucket"] if has_n else [])
    usecols = meta + [c for p in PREFIXES for c, _ in percol[p]]
    start, end = first_window(path, days, chunksize)
    games = {g: np.zeros(len(cards), np.int64) for g in GROUPS}
    wins = {g: np.zeros(len(cards), np.int64) for g in GROUPS}
    grows = {g: 0 for g in GROUPS}
    gwins = {g: 0 for g in GROUPS}
    last = None
    for c in pd.read_csv(path, usecols=usecols, chunksize=chunksize, compression="gzip", low_memory=False):
        t = pd.to_datetime(c["draft_time"], errors="coerce", utc=True)
        m = ((t >= start) & (t < end)).to_numpy()
        if not m.any():
            continue
        c = c.loc[m]
        tmax = t[m].max()
        last = tmax if last is None or tmax > last else last
        won = c["won"].astype(str).str.strip().str.lower().isin(["true", "1", "1.0"]).to_numpy()
        P = np.zeros((len(c), len(cards)), bool)
        for p in PREFIXES:
            if percol[p]:
                names = [n for n, _ in percol[p]]
                idx = [i for _, i in percol[p]]
                P[:, idx] |= c[names].apply(pd.to_numeric, errors="coerce").fillna(0).to_numpy() != 0
        half = (pd.util.hash_pandas_object(c["draft_id"].astype(str), index=False).to_numpy() % 2).astype(int)
        wr = pd.to_numeric(c["user_game_win_rate_bucket"], errors="coerce").to_numpy() if has_wr else np.full(len(c), np.nan)
        ng = pd.to_numeric(c["user_n_games_bucket"], errors="coerce").to_numpy() if has_n else np.full(len(c), np.nan)
        ones = np.ones(len(c), bool)
        t60 = (wr >= 0.5999) & (ng >= 50)
        masks = {"all": ones, "all_h0": half == 0, "all_h1": half == 1,
                 "top60n50": t60, "top60n50_h0": t60 & (half == 0), "top60n50_h1": t60 & (half == 1),
                 "top56n50": (wr >= 0.5599) & (ng >= 50), "top64n50": (wr >= 0.6399) & (ng >= 50), "top60": wr >= 0.5999}
        for g, mk in masks.items():
            if not mk.any():
                continue
            Pg = P[mk]
            games[g] += Pg.sum(0)
            wins[g] += Pg[won[mk]].sum(0)
            grows[g] += int(mk.sum())
            gwins[g] += int((mk & won).sum())
    rows = []
    for i, card in enumerate(cards):
        if games["all"][i] < min_games:
            continue
        r = {"set": s, "card_name": card, "gih_games": int(games["all"][i]), "gih_wins": int(wins["all"][i]),
             "gih_wr": wins["all"][i] / games["all"][i]}
        for g in GROUPS:
            r[f"{g}_games"] = int(games[g][i])
            r[f"{g}_wins"] = int(wins[g][i])
        r["window_start"] = start.isoformat()
        r["window_end"] = end.isoformat()
        rows.append(r)
    man = {"set": s, "source_url": url_for(s), "sha256": sha256_file(path), "format": FMT, "window_days": days,
           "window_start": start.isoformat(), "window_end": end.isoformat(),
           "last_draft_time_in_window": last.isoformat() if last is not None else None,
           "has_user_wr_bucket": has_wr, "has_user_n_games_bucket": has_n,
           "group_games": grows, "group_game_win_rate": {g: (gwins[g] / grows[g] if grows[g] else None) for g in GROUPS},
           "cards_output": len(rows), "min_gih_games": min_games}
    return rows, man


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", required=True)
    ap.add_argument("--days", type=int, default=28)
    ap.add_argument("--min-games", type=int, default=500)
    ap.add_argument("--chunksize", type=int, default=20000)
    ap.add_argument("--out-dir", type=Path, default=Path("out"))
    a = ap.parse_args()
    s = a.set.upper()
    if s in REFUSE:
        raise SystemExit(f"{s} is not allowed in case 6")
    a.out_dir.mkdir(parents=True, exist_ok=True)
    raw = a.out_dir / f"game_data_public.{s}.{FMT}.csv.gz"
    download(s, raw)
    rows, man = aggregate(s, raw, a.days, a.min_games, a.chunksize)
    pd.DataFrame(rows).to_csv(a.out_dir / f"{s}_case6_28d.csv", index=False)
    (a.out_dir / f"{s}_case6_manifest.json").write_text(json.dumps(man, indent=2))
    raw.unlink(missing_ok=True)
    print(json.dumps({k: man[k] for k in ("set", "cards_output", "group_games", "last_draft_time_in_window")}))


if __name__ == "__main__":
    main()
