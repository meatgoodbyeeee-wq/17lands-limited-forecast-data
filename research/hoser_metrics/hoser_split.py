#!/usr/bin/env python3
"""Colour-hoser metrics from the official 17Lands Public Game Data (Premier Draft, same 28-day window as the model data).

For each historical colour-hoser card (AFR, SNC and MOM uncommon cycles) this measures:
  * GIH games/wins split by whether the opponent's main colours include a target colour ("live") or not ("dead");
  * the same split for the pooled GIH of the other mono-coloured cards of the hoser's colour (baseline: how much any
    card of that colour wins more or less against those colours), and for all games of decks with that colour;
  * maindeck rate: games with the card in the deck / games of decks whose main colours include the hoser's colour,
    compared with the other uncommons of that colour.
Only aggregate counts are written. FIN, MH3 and FRA are refused.
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import case6_aggregate as ca  # noqa: E402

HOSERS = {  # set: {card: (card colour, target colours)}
    "AFR": {"Burning Hands": ("R", "G"), "Divine Smite": ("W", "B"), "Hunter's Mark": ("G", "U"),
            "Ray of Enfeeblement": ("B", "W"), "Ray of Frost": ("U", "R")},
    "SNC": {"Bouncer's Beatdown": ("G", "B"), "Knockout Blow": ("W", "R"), "Out of the Way": ("U", "G"),
            "Torch Breath": ("R", "U"), "Whack": ("B", "W")},
    "MOM": {"Change the Equation": ("U", "RG"), "Glistening Deluge": ("B", "GW"), "Lithomantic Barrage": ("R", "WU"),
            "Sandstalker Moloch": ("G", "UB"), "Surge of Salvation": ("W", "BR")},
}
PREFIXES = ("opening_hand_", "drawn_", "tutored_")


def colours():
    f = pd.read_csv(ROOT / "data/features/dev_feature_22.csv.gz")
    f["set"] = f["set"].str.upper()
    f["col"] = ["".join(c for c in "WUBRG" if r[f"color_{c}"] == 1) for _, r in f.iterrows()]
    return f[["set", "name", "col", "rarity_ord"]]


def has_any(series, letters):
    s = series.fillna("").astype(str)
    return np.logical_or.reduce([s.str.contains(c, regex=False).to_numpy() for c in letters])


def run(s, path, meta):
    h = ca.header(path)
    cards = sorted({c[len(p):] for c in h for p in PREFIXES if c.startswith(p)})
    pos = {c: i for i, c in enumerate(cards)}
    hos = HOSERS[s]
    missing = [c for c in hos if c not in pos]
    if missing:
        raise SystemExit(f"hoser columns missing: {missing}")
    m = meta[meta["set"] == s].set_index("name")
    mono = {k: [pos[c] for c in cards if c in m.index and m.loc[c, "col"] == k and c not in hos] for k in "WUBRG"}
    unc = {k: [pos[c] for c in cards if c in m.index and m.loc[c, "col"] == k and m.loc[c, "rarity_ord"] == 1 and c not in hos]
           for k in "WUBRG"}
    deck_cols = [f"deck_{c}" for c in cards if f"deck_{c}" in h]
    deck_idx = [pos[c] for c in cards if f"deck_{c}" in h]
    usecols = ["draft_time", "won", "main_colors", "opp_colors"] + [f"{p}{c}" for p in PREFIXES for c in cards if f"{p}{c}" in h] + deck_cols
    start, end = ca.first_window(path, 28, 20000)
    combos = {(k, t) for k, t in hos.values()}
    out = {c: {"live": [0, 0], "dead": [0, 0], "deck_games": 0} for c in hos}
    peer = {kt: {"live": [0, 0], "dead": [0, 0]} for kt in combos}
    base = {kt: {"live": [0, 0], "dead": [0, 0]} for kt in combos}
    deck_by_colour = {k: np.zeros(len(cards), np.int64) for k in "WUBRG"}
    games_by_colour = {k: 0 for k in "WUBRG"}
    for c in pd.read_csv(path, usecols=usecols, chunksize=20000, compression="gzip", low_memory=False):
        t = pd.to_datetime(c["draft_time"], errors="coerce", utc=True)
        c = c.loc[((t >= start) & (t < end)).to_numpy()]
        if c.empty:
            continue
        won = c["won"].astype(str).str.strip().str.lower().isin(["true", "1", "1.0"]).to_numpy()
        P = np.zeros((len(c), len(cards)), bool)
        for p in PREFIXES:
            names = [f"{p}{x}" for x in cards if f"{p}{x}" in c.columns]
            idx = [pos[n[len(p):]] for n in names]
            P[:, idx] |= c[names].apply(pd.to_numeric, errors="coerce").fillna(0).to_numpy() != 0
        D = np.zeros((len(c), len(cards)), bool)
        D[:, deck_idx] = c[deck_cols].apply(pd.to_numeric, errors="coerce").fillna(0).to_numpy() > 0
        mine = {k: has_any(c["main_colors"], k) for k in "WUBRG"}
        for k in "WUBRG":
            games_by_colour[k] += int(mine[k].sum())
            deck_by_colour[k] += D[mine[k]].sum(0)
        live_cache = {}
        for card, (k, tgt) in hos.items():
            live = live_cache.setdefault(tgt, has_any(c["opp_colors"], tgt))
            i = pos[card]
            for key, mk in (("live", live), ("dead", ~live)):
                g = P[:, i] & mk
                out[card][key][0] += int(g.sum()); out[card][key][1] += int((g & won).sum())
            out[card]["deck_games"] += int((D[:, i] & mine[k]).sum())
        for (k, tgt) in combos:
            live = live_cache.setdefault(tgt, has_any(c["opp_colors"], tgt))
            cols = mono[k]
            for key, mk in (("live", live), ("dead", ~live)):
                sub = P[mk][:, cols]
                peer[(k, tgt)][key][0] += int(sub.sum()); peer[(k, tgt)][key][1] += int(sub[won[mk]].sum())
                g = mine[k] & mk
                base[(k, tgt)][key][0] += int(g.sum()); base[(k, tgt)][key][1] += int((g & won).sum())
    res = {"set": s, "window_start": start.isoformat(), "window_end": end.isoformat(), "cards": {}}
    for card, (k, tgt) in hos.items():
        r = out[card]
        rate = r["deck_games"] / games_by_colour[k]
        prates = deck_by_colour[k][unc[k]] / games_by_colour[k]
        res["cards"][card] = {"colour": k, "targets": tgt, "gih_live": r["live"], "gih_dead": r["dead"],
                              "peer_gih_live": peer[(k, tgt)]["live"], "peer_gih_dead": peer[(k, tgt)]["dead"],
                              "colour_games_live": base[(k, tgt)]["live"], "colour_games_dead": base[(k, tgt)]["dead"],
                              "maindeck_rate": rate, "peer_uncommon_maindeck_rate_mean": float(prates.mean()),
                              "peer_uncommon_maindeck_rate_median": float(np.median(prates)), "n_peer_uncommons": len(prates)}
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", required=True)
    ap.add_argument("--out-dir", type=Path, required=True)
    a = ap.parse_args()
    s = a.set.upper()
    if s not in HOSERS:
        raise SystemExit("only AFR, SNC, MOM")
    a.out_dir.mkdir(parents=True, exist_ok=True)
    raw = a.out_dir / f"game_data_public.{s}.{ca.FMT}.csv.gz"
    ca.download(s, raw)
    res = run(s, raw, colours())
    raw.unlink(missing_ok=True)
    (a.out_dir / f"{s}_hoser.json").write_text(json.dumps(res, indent=2))
    print(json.dumps({c: (v["gih_live"], v["gih_dead"]) for c, v in res["cards"].items()}))


if __name__ == "__main__":
    main()
