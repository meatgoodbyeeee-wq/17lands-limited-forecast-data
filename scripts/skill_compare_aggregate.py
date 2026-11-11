#!/usr/bin/env python3
"""Skill comparison: how do top players' games differ from everyone else's? (17Lands Public Game Data, Premier Draft)

Same 28-day window as Case 6 (earliest draft_time + 28 days). Player groups come from the two bucket columns:
  L   user_n_games_bucket < 50 (few games; win-rate bucket is noisy)
  B1  n >= 50 and user_game_win_rate_bucket < 0.48
  B2  0.48 - 0.54      B3  0.54 - 0.60      B4  0.60 - 0.64      B5  >= 0.64
Top = B4 + B5 (= Case 6 top60n50). The bucket is the player's win rate in this set, so it includes the games counted here.

Outputs (per set):
  <SET>_cards.csv.gz   per card x key: games in pool, maindeck, copies, opening hand, drawn (not in opening hand),
                       in hand (GIH, same rule as Case 6), not seen (GNS); games and wins.
                       Keys: band x half (draft_id hash) x period (days 0-13 / 14-27), plus T500/N500 (n >= 500,
                       win rate >= 0.60 / < 0.60) and T50/N50 (n 50-100).
  <SET>_games.csv.gz   per band x n-bucket x week x dimension value: games and wins. Dimensions: on_play, mulligans,
                       opponent mulligans, turns, rank, opponent rank, rank pair, main colours, splash, number of main
                       colours, opponent colours, match number.
  <SET>_sums.csv       per band x n-bucket x week: sums and sums of squares of deck size, sideboard size,
                       cards in opening hand, cards drawn, turns.
  <SET>_skill_manifest.json
FRA, TRK, FIN and MH3 are refused.
"""
import argparse, csv, gzip, hashlib, json
from pathlib import Path
from urllib.request import Request, urlopen
import numpy as np
import pandas as pd

BASE = "https://17lands-public.s3.amazonaws.com/analysis_data/game_data"
FMT = "PremierDraft"
REFUSE = {"FIN", "MH3", "FRA", "TRK"}
PREF = ("deck_", "sideboard_", "opening_hand_", "drawn_", "tutored_")
BANDS = ["L", "B1", "B2", "B3", "B4", "B5"]
METRICS = ["pool_g", "deck_g", "deck_w", "copies", "oh_g", "oh_w", "gd_g", "gd_w", "gih_g", "gih_w", "gns_g", "gns_w"]
DIMS = ["on_play", "mull", "opp_mull", "turns", "rank", "opp_rank", "rank_pair", "main_colors", "splash", "n_main", "opp_colors", "match_number"]
SUMS = ["deck_size", "sb_size", "oh_cards", "drawn_cards", "turns_n"]


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


def colours(x):
    s = "" if pd.isna(x) else str(x).strip()
    return "".join(k for k in "WUBRG" if k in s.upper())


def band_of(wr, ng):
    b = np.full(len(wr), "L", dtype=object)
    ok = ng >= 50
    b[ok & (wr < 0.4799)] = "B1"
    b[ok & (wr >= 0.4799) & (wr < 0.5399)] = "B2"
    b[ok & (wr >= 0.5399) & (wr < 0.5999)] = "B3"
    b[ok & (wr >= 0.5999) & (wr < 0.6399)] = "B4"
    b[ok & (wr >= 0.6399)] = "B5"
    b[ok & np.isnan(wr)] = "NA"
    return b


def card_keys():
    keys = [(b, h, p) for b in BANDS for h in ("0", "1") for p in ("0", "1")]
    keys += [("T500", "all", "all"), ("N500", "all", "all"), ("T50", "all", "all"), ("N50", "all", "all")]
    return keys


def aggregate(s, path, days, chunksize):
    h = header(path)
    need = ["draft_time", "won", "draft_id", "user_game_win_rate_bucket", "user_n_games_bucket"]
    miss = [k for k in need if k not in h]
    if miss:
        raise RuntimeError(f"required columns missing: {miss}")
    cards = sorted({col[len(p):] for col in h for p in PREF if col.startswith(p)})
    pos = {c: i for i, c in enumerate(cards)}
    percol = {p: [(f"{p}{c}", pos[c]) for c in cards if f"{p}{c}" in h] for p in PREF}
    meta_opt = [k for k in ("on_play", "num_mulligans", "opp_num_mulligans", "num_turns", "rank", "opp_rank",
                            "main_colors", "splash_colors", "opp_colors", "match_number") if k in h]
    usecols = need + meta_opt + [c for p in PREF for c, _ in percol[p]]
    start, end = first_window(path, days, chunksize)
    keys = card_keys(); kidx = {k: i for i, k in enumerate(keys)}
    acc = {m: np.zeros((len(keys), len(cards)), np.float64) for m in METRICS}
    gparts, sparts = [], []
    n_rows = 0; n_wins = 0; last = None; band_counts = {}
    C = len(cards)
    for c in pd.read_csv(path, usecols=usecols, chunksize=chunksize, compression="gzip", low_memory=False):
        t = pd.to_datetime(c["draft_time"], errors="coerce", utc=True)
        m = ((t >= start) & (t < end)).to_numpy()
        if not m.any():
            continue
        c = c.loc[m].reset_index(drop=True); t = t[m].reset_index(drop=True)
        last = t.max() if last is None or t.max() > last else last
        n = len(c)
        won = c["won"].astype(str).str.strip().str.lower().isin(["true", "1", "1.0"]).to_numpy()
        wr = pd.to_numeric(c["user_game_win_rate_bucket"], errors="coerce").to_numpy(dtype=float)
        ng = pd.to_numeric(c["user_n_games_bucket"], errors="coerce").to_numpy(dtype=float)
        band = band_of(wr, np.nan_to_num(ng, nan=-1))
        half = (pd.util.hash_pandas_object(c["draft_id"].astype(str), index=False).to_numpy() % 2).astype(int).astype(str)
        days_in = ((t - start).dt.total_seconds() / 86400).to_numpy()
        week = np.clip((days_in // 7).astype(int), 0, 3)
        period = np.where(days_in < 14, "0", "1")
        n_rows += n; n_wins += int(won.sum())
        for b, k in zip(*np.unique(band, return_counts=True)):
            band_counts[b] = band_counts.get(b, 0) + int(k)
        # ---- card matrices
        def mat(p):
            X = np.zeros((n, C), np.float32)
            if percol[p]:
                names = [a for a, _ in percol[p]]; idx = [i for _, i in percol[p]]
                X[:, idx] = c[names].apply(pd.to_numeric, errors="coerce").fillna(0).to_numpy(np.float32)
            return X
        D, S, OH, DR, TU = (mat(p) for p in PREF)
        deck = D > 0; ohb = OH > 0; drb = DR > 0; gih = ohb | drb | (TU > 0)
        X = {"pool_g": ((D + S) > 0), "deck_g": deck, "copies": D, "oh_g": ohb, "gd_g": drb & ~ohb, "gih_g": gih, "gns_g": deck & ~gih}
        # ---- key matrix (a game can belong to several keys)
        K = np.zeros((n, len(keys)), np.float32)
        ks = pd.Series(list(zip(band, half, period))).map(kidx).to_numpy()
        ok = ~pd.isna(ks)
        K[np.nonzero(ok)[0], ks[ok].astype(int)] = 1
        topn = (ng >= 50) & (wr >= 0.5999); nontopn = (ng >= 50) & (wr < 0.5999)
        K[:, kidx[("T500", "all", "all")]] = topn & (ng >= 500)
        K[:, kidx[("N500", "all", "all")]] = nontopn & (ng >= 500)
        K[:, kidx[("T50", "all", "all")]] = topn & (ng <= 100)
        K[:, kidx[("N50", "all", "all")]] = nontopn & (ng <= 100)
        Kw = K * won[:, None].astype(np.float32)
        for name, Xm in X.items():
            Xm = Xm.astype(np.float32)
            acc[name] += K.T @ Xm
            w = name[:-2] + "_w"
            if w in acc:
                acc[w] += Kw.T @ Xm
        # ---- game-level dimensions
        g = pd.DataFrame({"band": band, "nb": np.nan_to_num(ng, nan=-1).astype(int), "week": week, "won": won.astype(int)})
        if "on_play" in c: g["on_play"] = c["on_play"].astype(str).str.strip().str.lower().map({"true": "1", "1": "1", "1.0": "1", "false": "0", "0": "0", "0.0": "0"}).fillna("NA")
        if "num_mulligans" in c: g["mull"] = pd.to_numeric(c["num_mulligans"], errors="coerce").clip(upper=2).fillna(-1).astype(int).astype(str)
        if "opp_num_mulligans" in c: g["opp_mull"] = pd.to_numeric(c["opp_num_mulligans"], errors="coerce").clip(upper=2).fillna(-1).astype(int).astype(str)
        if "num_turns" in c: g["turns"] = pd.to_numeric(c["num_turns"], errors="coerce").clip(upper=20).fillna(-1).astype(int).astype(str)
        if "rank" in c: g["rank"] = c["rank"].fillna("NA").astype(str).str.lower()
        if "opp_rank" in c: g["opp_rank"] = c["opp_rank"].fillna("NA").astype(str).str.lower()
        if "rank" in c and "opp_rank" in c: g["rank_pair"] = g["rank"] + "|" + g["opp_rank"]
        if "main_colors" in c:
            g["main_colors"] = c["main_colors"].map(colours); g["n_main"] = g["main_colors"].str.len().astype(str)
        if "splash_colors" in c: g["splash"] = (c["splash_colors"].map(colours).str.len() > 0).astype(int).astype(str)
        if "opp_colors" in c: g["opp_colors"] = c["opp_colors"].map(colours)
        if "match_number" in c: g["match_number"] = pd.to_numeric(c["match_number"], errors="coerce").clip(upper=10).fillna(-1).astype(int).astype(str)
        for d in DIMS:
            if d in g:
                x = g.groupby(["band", "nb", "week", d], observed=True).won.agg(["size", "sum"]).reset_index().rename(columns={d: "val", "size": "games", "sum": "wins"})
                x.insert(3, "dim", d); gparts.append(x)
        x = g.groupby(["band", "nb", "week"]).won.agg(["size", "sum"]).reset_index().rename(columns={"size": "games", "sum": "wins"})
        x.insert(3, "dim", "all"); x.insert(4, "val", "all"); gparts.append(x)
        sm = pd.DataFrame({"band": band, "nb": g["nb"], "week": week, "deck_size": D.sum(1), "sb_size": S.sum(1), "oh_cards": OH.sum(1), "drawn_cards": DR.sum(1),
                           "turns_n": pd.to_numeric(c["num_turns"], errors="coerce").to_numpy() if "num_turns" in c else np.nan})
        for k in SUMS:
            sm[k + "_sq"] = sm[k] ** 2
        sm["n"] = 1
        sparts.append(sm.groupby(["band", "nb", "week"]).sum(min_count=1).reset_index())
        # compact partial results to bound memory
        if len(gparts) > 400:
            gparts = [pd.concat(gparts).groupby(["band", "nb", "week", "dim", "val"], as_index=False)[["games", "wins"]].sum()]
    games = pd.concat(gparts).groupby(["band", "nb", "week", "dim", "val"], as_index=False)[["games", "wins"]].sum()
    games.insert(0, "set", s)
    sums = pd.concat(sparts).groupby(["band", "nb", "week"], as_index=False).sum(min_count=1)
    sums.insert(0, "set", s)
    rows = []
    for ki, (b, hh, p) in enumerate(keys):
        for ci, card in enumerate(cards):
            if acc["pool_g"][ki, ci] == 0 and acc["gih_g"][ki, ci] == 0:
                continue
            r = {"set": s, "card_name": card, "grp": b, "half": hh, "period": p}
            r.update({mm: int(round(acc[mm][ki, ci])) for mm in METRICS})
            rows.append(r)
    man = {"set": s, "source_url": url_for(s), "sha256": sha256_file(path), "format": FMT, "window_days": days,
           "window_start": start.isoformat(), "window_end": end.isoformat(),
           "last_draft_time_in_window": last.isoformat() if last is not None else None,
           "games": n_rows, "wins": n_wins, "band_games": band_counts, "meta_columns_used": meta_opt, "cards": len(cards)}
    return pd.DataFrame(rows), games, sums, man


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", required=True)
    ap.add_argument("--days", type=int, default=28)
    ap.add_argument("--chunksize", type=int, default=10000)
    ap.add_argument("--out-dir", type=Path, default=Path("out"))
    ap.add_argument("--local-file", type=Path, help="use this game-data file instead of downloading (tests)")
    a = ap.parse_args()
    s = a.set.upper()
    if s in REFUSE:
        raise SystemExit(f"{s} is not allowed")
    a.out_dir.mkdir(parents=True, exist_ok=True)
    if a.local_file:
        raw = a.local_file
    else:
        raw = a.out_dir / f"game_data_public.{s}.{FMT}.csv.gz"; download(s, raw)
    cards, games, sums, man = aggregate(s, raw, a.days, a.chunksize)
    cards.to_csv(a.out_dir / f"{s}_cards.csv.gz", index=False)
    games.to_csv(a.out_dir / f"{s}_games.csv.gz", index=False)
    sums.to_csv(a.out_dir / f"{s}_sums.csv", index=False)
    (a.out_dir / f"{s}_skill_manifest.json").write_text(json.dumps(man, indent=2))
    if not a.local_file:
        raw.unlink(missing_ok=True)
    print(json.dumps({k: man[k] for k in ("set", "games", "band_games", "last_draft_time_in_window")}))


if __name__ == "__main__":
    main()
