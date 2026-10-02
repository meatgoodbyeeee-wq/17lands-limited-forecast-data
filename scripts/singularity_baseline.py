#!/usr/bin/env python3
"""Descriptive baseline from the official 17Lands Public Game Data (Premier Draft).

Purpose: raw counters for comparing a new set (FRA) with past Standard sets in an article. Descriptive only.
Nothing produced here feeds any model, and FRA / MH3 are refused.

Pass 1 (narrow columns, whole file): per UTC date of draft_time, game counters, the num_turns histogram, mulligans
and per (main colours, splash) deck-category counters. Windows are whole UTC dates counted from "day 0", the first
date with at least --min-start-games games:
    D1 / D3 / D7 / D28 = first 1 / 3 / 7 / 28 dates from day 0,  ALL = every row in the file.
Pass 2 (card columns, only the chunks that can hold D28 rows): per card, windows D3 and D28:
    deck (card in the 40-card deck), OH (opening hand), GD (drawn or tutored, not in the opening hand),
    GIH = OH + GD, GND = in deck and never in hand. Same "in hand" logic as scripts/case6_aggregate.py.
Rarity / colour / type come from the public 17Lands cards.csv when it can be fetched.

Outputs in --out-dir: {SET}_sets.json and {SET}_cards.csv. If the dataset is not published the manifest says so
and the script exits 0, so one missing set never fails the whole matrix.
"""
import argparse
import csv
import gzip
import json
import math
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import numpy as np
import pandas as pd

BASE = "https://17lands-public.s3.amazonaws.com/analysis_data/game_data"
CARDS_URL = "https://17lands-public.s3.amazonaws.com/analysis_data/cards/cards.csv"
FMT = "PremierDraft"
REFUSE = {"FRA", "MH3"}
WUBRG = "WUBRG"
MAXTURN = 40
TRUE = ["true", "1", "1.0"]
P1_COLS = ["draft_time", "won", "on_play", "num_turns", "num_mulligans", "opp_num_mulligans",
           "main_colors", "splash_colors"]
CARD_PREFIXES = ("deck_", "opening_hand_", "drawn_", "tutored_")
BASICS = {"Plains", "Island", "Swamp", "Mountain", "Forest"}
WINDOWS = {"D1": 1, "D3": 3, "D7": 7, "D28": 28, "ALL": None}
CARD_WINDOWS = ("D3", "D28")
UA = {"User-Agent": "SakiyomiResearch/1.0"}


def url_for(s):
    return f"{BASE}/game_data_public.{s}.{FMT}.csv.gz"


def download(url, dest, tries=3):
    for k in range(tries):
        try:
            tmp = dest.with_suffix(dest.suffix + ".part")
            with urlopen(Request(url, headers=UA), timeout=300) as r, open(tmp, "wb") as out:
                for b in iter(lambda: r.read(1 << 20), b""):
                    out.write(b)
            tmp.replace(dest)
            return
        except HTTPError as e:
            if e.code in (403, 404):
                raise
            err = e
        except URLError as e:
            err = e
        if k == tries - 1:
            raise err
        time.sleep(10 * (k + 1))


def header_of(path):
    with gzip.open(path, "rt", encoding="utf-8-sig", newline="") as f:
        return next(csv.reader(f))


def norm_colors(x):
    x = "" if x is None or (isinstance(x, float) and math.isnan(x)) else str(x).upper()
    return "".join(ch for ch in WUBRG if ch in x)


def norm_series(s):
    s = s.fillna("")
    cache = {u: norm_colors(u) for u in s.unique()}
    return s.map(cache)


def pass1(path, header, chunksize):
    cols = [c for c in P1_COLS if c in header]
    for need in ("draft_time", "won", "num_turns", "main_colors"):
        if need not in cols:
            raise RuntimeError(f"required column missing: {need}")
    flags = {c: (c in header) for c in P1_COLS}
    mains, hists, cats, spans = [], [], [], []
    rows = 0
    for c in pd.read_csv(path, usecols=cols, chunksize=chunksize, compression="gzip", low_memory=False, dtype=str):
        date = c["draft_time"].fillna("").str.slice(0, 10)
        good = date.str.match(r"^\d{4}-\d{2}-\d{2}$").to_numpy()
        if not good.all():
            c, date = c.loc[good], date[good]
        if len(c) == 0:
            spans.append((None, None))
            continue
        rows += len(c)
        spans.append((date.min(), date.max()))
        won = c["won"].str.strip().str.lower().isin(TRUE).astype(np.int64)
        if flags["on_play"]:
            onp = c["on_play"].str.strip().str.lower().isin(TRUE).astype(np.int64)
        else:
            onp = pd.Series(0, index=c.index, dtype=np.int64)
        turns = pd.to_numeric(c["num_turns"], errors="coerce")
        tn = turns.notna().astype(np.int64)
        t = turns.fillna(0.0)
        if flags["num_mulligans"]:
            mu = pd.to_numeric(c["num_mulligans"], errors="coerce").fillna(0.0)
        else:
            mu = pd.Series(0.0, index=c.index)
        if flags["opp_num_mulligans"]:
            omu = pd.to_numeric(c["opp_num_mulligans"], errors="coerce").fillna(0.0)
        else:
            omu = pd.Series(0.0, index=c.index)
        main = norm_series(c["main_colors"])
        spl = (c["splash_colors"].fillna("").str.strip().str.len() > 0).astype(int) if flags["splash_colors"] \
            else pd.Series(0, index=c.index)
        pw, pl, dw, dl = onp * won, onp * (1 - won), (1 - onp) * won, (1 - onp) * (1 - won)
        df = pd.DataFrame({
            "date": date.to_numpy(), "games": 1, "wins": won.to_numpy(), "onp_games": onp.to_numpy(),
            "onp_wins": (onp * won).to_numpy(), "turns_sum": t.to_numpy(), "turns_sq": (t * t).to_numpy(),
            "tn": tn.to_numpy(), "mull_games": (mu > 0).astype(int).to_numpy(), "mulls_sum": mu.to_numpy(),
            "omull_games": (omu > 0).astype(int).to_numpy(),
            "t_pw": (t * pw).to_numpy(), "n_pw": (tn * pw).to_numpy(), "t_pl": (t * pl).to_numpy(),
            "n_pl": (tn * pl).to_numpy(), "t_dw": (t * dw).to_numpy(), "n_dw": (tn * dw).to_numpy(),
            "t_dl": (t * dl).to_numpy(), "n_dl": (tn * dl).to_numpy(),
        })
        mains.append(df.groupby("date").sum())
        hh = pd.DataFrame({"date": date.to_numpy(), "tb": np.clip(t.to_numpy(), 0, MAXTURN).astype(int),
                           "k": 1})[tn.to_numpy() == 1]
        hists.append(hh.groupby(["date", "tb"]).sum())
        cc = pd.DataFrame({"date": date.to_numpy(), "cat": (main + "|" + spl.astype(str)).to_numpy(),
                           "n": 1, "w": won.to_numpy(), "t": t.to_numpy(), "tn": tn.to_numpy()})
        cats.append(cc.groupby(["date", "cat"]).sum())
    if not mains:
        raise RuntimeError("no valid rows")
    return (pd.concat(mains).groupby(level=0).sum(), pd.concat(hists).groupby(level=[0, 1]).sum(),
            pd.concat(cats).groupby(level=[0, 1]).sum(), spans, rows, flags)


def window_dates(daily_games, min_start_games):
    dates = sorted(daily_games.index)
    day0 = next((d for d in dates if daily_games[d] >= min_start_games), dates[0])
    d0 = pd.Timestamp(day0)
    out = {}
    for name, k in WINDOWS.items():
        out[name] = list(dates) if k is None else [d for d in dates if 0 <= (pd.Timestamp(d) - d0).days < k]
    return day0, out


def summarise_windows(main, hist, cat, wdates):
    res = {}
    for name, ds in wdates.items():
        if not ds:
            continue
        m = main.loc[ds].sum()
        h = hist.loc[hist.index.get_level_values(0).isin(ds)].groupby(level=1)["k"].sum()
        ct = cat.loc[cat.index.get_level_values(0).isin(ds)].groupby(level=1).sum()
        res[name] = {
            "first_date": ds[0], "last_date": ds[-1], "n_dates": len(ds),
            "main": {k: float(v) for k, v in m.items()},
            "hist": {int(k): int(v) for k, v in h.items()},
            "cats": {k: {"n": int(r.n), "w": int(r.w), "t": float(r.t), "tn": int(r.tn)} for k, r in ct.iterrows()},
        }
    return res


def pass2(path, header, wdates, last_chunk, chunksize, meta):
    names = sorted({col[len(p):] for col in header for p in CARD_PREFIXES if col.startswith(p)})
    idx = {n: i for i, n in enumerate(names)}
    per = {}
    for p in CARD_PREFIXES:
        pairs = [(f"{p}{n}", idx[n]) for n in names if f"{p}{n}" in header]
        per[p] = ([a for a, _ in pairs], [b for _, b in pairs])
    usecols = ["draft_time", "won"] + [a for p in CARD_PREFIXES for a in per[p][0]]
    dtypes = {a: np.float32 for p in CARD_PREFIXES for a in per[p][0]}
    dtypes.update({"draft_time": str, "won": str})
    wsets = {w: set(wdates[w]) for w in CARD_WINDOWS if w in wdates}
    keys = ["deck_n", "deck_w", "oh_n", "oh_w", "gd_n", "gd_w", "gnd_n", "gnd_w", "gih_n", "gih_w"]
    acc = {w: {k: np.zeros(len(names), np.int64) for k in keys} for w in wsets}
    C = len(names)
    for i, c in enumerate(pd.read_csv(path, usecols=usecols, dtype=dtypes, chunksize=chunksize,
                                       compression="gzip", low_memory=False)):
        if i > last_chunk:
            break
        date = c["draft_time"].fillna("").str.slice(0, 10)
        won = c["won"].str.strip().str.lower().isin(TRUE).to_numpy()

        def mat(p):
            M = np.zeros((len(c), C), np.float32)
            cols, ix = per[p]
            if cols:
                M[:, ix] = c[cols].fillna(0).to_numpy(np.float32)
            return M

        deck, oh, dr, tu = mat("deck_") > 0, mat("opening_hand_") > 0, mat("drawn_") > 0, mat("tutored_") > 0
        for w, ds in wsets.items():
            m = date.isin(ds).to_numpy()
            if not m.any():
                continue
            D, O = deck[m], oh[m]
            G = (dr[m] | tu[m]) & ~O
            H = O | G
            N = D & ~H
            ww = won[m].astype(np.float32)
            for key, M in (("deck", D), ("oh", O), ("gd", G), ("gnd", N), ("gih", H)):
                acc[w][key + "_n"] += M.sum(0, dtype=np.int64)
                acc[w][key + "_w"] += np.rint(ww @ M.astype(np.float32)).astype(np.int64)
    rows = []
    for w in wsets:
        a = acc[w]
        for n, i in idx.items():
            if n in BASICS or a["gih_n"][i] == 0:
                continue
            r = {"window": w, "card": n}
            r.update(meta.get(n, meta.get(n.split(" // ")[0], {})))
            r.update({k: int(a[k][i]) for k in keys})
            rows.append(r)
    return rows


def load_meta(s, out_dir):
    try:
        p = out_dir / "cards.csv"
        download(CARDS_URL, p)
        df = pd.read_csv(p)
        df = df[df["expansion"].astype(str).str.upper() == s]
        meta = {}
        for _, r in df.iterrows():
            d = {"rarity": r.get("rarity"), "colors": r.get("color_identity"), "mana_value": r.get("mana_value"),
                 "types": r.get("types")}
            meta[str(r["name"])] = d
            meta.setdefault(str(r["name"]).split(" // ")[0], d)
        p.unlink(missing_ok=True)
        return meta
    except Exception as e:  # metadata is optional
        print("cards.csv unavailable:", repr(e))
        return {}


def run(s, path, args, out_dir):
    header = header_of(path)
    t0 = time.time()
    main, hist, cat, spans, rows, flags = pass1(path, header, args.chunksize)
    day0, wdates = window_dates(main["games"], args.min_start_games)
    windows = summarise_windows(main, hist, cat, wdates)
    d28_last = max(wdates["D28"]) if wdates.get("D28") else None
    last_chunk = max((i for i, (lo, _) in enumerate(spans) if lo is not None and d28_last and lo <= d28_last),
                     default=-1)
    meta = {} if args.no_card_meta else load_meta(s, out_dir)
    card_rows = pass2(path, header, wdates, last_chunk, args.chunksize, meta)
    pd.DataFrame(card_rows).to_csv(out_dir / f"{s}_cards.csv", index=False)
    man = {"set": s, "status": "ok", "source_url": url_for(s), "format": FMT, "rows": rows, "day0": day0,
           "chunksize": args.chunksize, "min_start_games": args.min_start_games, "columns_present": flags,
           "n_card_rows": len(card_rows), "seconds": round(time.time() - t0), "windows": windows}
    (out_dir / f"{s}_sets.json").write_text(json.dumps(man))
    print(json.dumps({"set": s, "rows": rows, "day0": day0, "cards": len(card_rows), "seconds": man["seconds"]}))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", required=True)
    ap.add_argument("--out-dir", type=Path, default=Path("out"))
    ap.add_argument("--chunksize", type=int, default=20000)
    ap.add_argument("--min-start-games", type=int, default=5000)
    ap.add_argument("--input-file", type=Path, help="local .csv.gz for tests (skips the download)")
    ap.add_argument("--no-card-meta", action="store_true")
    a = ap.parse_args()
    s = a.set.upper()
    if s in REFUSE:
        raise SystemExit(f"{s} is not allowed")
    a.out_dir.mkdir(parents=True, exist_ok=True)
    if a.input_file:
        run(s, a.input_file, a, a.out_dir)
        return
    raw = a.out_dir / f"game_data_public.{s}.{FMT}.csv.gz"
    try:
        download(url_for(s), raw)
    except HTTPError as e:
        (a.out_dir / f"{s}_sets.json").write_text(json.dumps({"set": s, "status": "unavailable", "http_status": e.code}))
        print(f"{s}: unavailable (HTTP {e.code})")
        return
    try:
        run(s, raw, a, a.out_dir)
    finally:
        raw.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
