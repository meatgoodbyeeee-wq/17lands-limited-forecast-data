"""L3 analysis per PLAN_L3.md (with amendment 1).

usage: python3 -I analyze_l3.py <DECK_DIR_C> <OUT_BASE> <OUT_PATCH> [JSON_OUT]
Logs as in L2' (START / DRAW|card|player / END|winner / 13-field cast lines), but cast lines cover every spell.
E = the four ETB-attach equipment fixed in the plan. N = every other non-basic card seen in the decks.
"""
import collections
import glob
import json
import os
import re
import sys

import numpy as np

DECKS, OUT_BASE, OUT_PATCH = sys.argv[1:4]
JSON_OUT = sys.argv[4] if len(sys.argv) > 4 else None
E = {"Falcon's Wing Harness", "Super Suit", "Stolen Stark Tech", "Iron Man Armor"}
BASICS = {"Plains", "Island", "Swamp", "Mountain", "Forest"}
deck_names = sorted(os.path.basename(p)[:-4] for p in glob.glob(os.path.join(DECKS, "*.dck")))
idx = {d: i for i, d in enumerate(deck_names)}


def strip_ai(n):
    return re.sub(r"^Ai\(\d+\)-", "", n)


def load(out):
    games, casts, draw_lines = [], [], []
    for path in sorted(glob.glob(os.path.join(out, "g*.log"))):
        cur = None
        for line in open(path, encoding="utf-8"):
            line = line.rstrip("\n")
            if line == "START":
                cur = {"draw": collections.defaultdict(set), "lines": collections.Counter(), "winner": None, "ended": False}
                games.append(cur)
            elif line.startswith("DRAW|") and cur is not None:
                _, c, o = line.split("|")
                cur["draw"][strip_ai(o)].add(c)
                cur["lines"][strip_ai(o)] += 1
            elif line.startswith("END|") and cur is not None:
                w = line.split("|", 1)[1]
                cur["winner"] = None if w in ("null", "None") else strip_ai(w)
                cur["ended"] = True
            else:
                f = line.split("|")
                if len(f) == 13:
                    casts.append({"card": f[0], "phase": f[2], "own": f[4] == "true", "nown": int(f[7])})
    turns, timeouts_txt = [], 0
    for path in sorted(glob.glob(os.path.join(out, "g*.out"))):
        txt = open(path, encoding="utf-8", errors="replace").read()
        turns += [int(t) for t in re.findall(r"Game Outcome: Turn (\d+)", txt)]
        timeouts_txt += txt.count("Stopping slow match")
    return games, casts, turns, timeouts_txt


res, agg = {}, {}
for name, out in (("base", OUT_BASE), ("patch", OUT_PATCH)):
    games, casts, turns, tt = load(out)
    a = np.zeros((len(deck_names), 4))  # E wins, E n, N wins, N n
    per_card = collections.defaultdict(lambda: [0, 0])
    for g in games:
        if not g["ended"] or g["winner"] is None:
            continue
        for deck, cards in g["draw"].items():
            if deck not in idx:
                continue
            won = int(g["winner"] == deck)
            for c in cards:
                if c in BASICS:
                    continue
                if c in E:
                    a[idx[deck], 0] += won
                    a[idx[deck], 1] += 1
                    per_card[c][0] += won
                    per_card[c][1] += 1
                else:
                    a[idx[deck], 2] += won
                    a[idx[deck], 3] += 1
    agg[name] = a
    ec = [c for c in casts if c["card"] in E]
    zero = sum(1 for c in ec if c["nown"] == 0)
    lines = [v for g in games for v in g["lines"].values()]
    unfinished = len(games) - sum(g["ended"] for g in games)
    res[name] = {
        "games": len(games), "timeouts": max(tt, unfinished),
        "mean_turns": float(np.mean(turns)) if turns else None,
        "draw_lines_per_player": float(np.mean(lines)) if lines else None,
        "E_casts": len(ec), "E_zero_creature_casts": zero, "E_zero_creature_rate": zero / len(ec) if ec else None,
        "E_cast_phase": dict(collections.Counter(("自" if c["own"] else "相") + ":" + c["phase"] for c in ec).most_common()),
        "E_gih_n": int(a[:, 1].sum()), "E_gih_wr": float(a[:, 0].sum() / a[:, 1].sum()) if a[:, 1].sum() else None,
        "N_gih_n": int(a[:, 3].sum()), "N_gih_wr": float(a[:, 2].sum() / a[:, 3].sum()) if a[:, 3].sum() else None,
        "per_card_E": {c: v for c, v in sorted(per_card.items())},
    }
    res[name]["E_casts_per_gih_game"] = len(ec) / res[name]["E_gih_n"] if res[name]["E_gih_n"] else None

rng = np.random.default_rng(20261019)
w = rng.multinomial(len(deck_names), [1 / len(deck_names)] * len(deck_names), size=10000)
for key, (wi, ni) in (("E", (0, 1)), ("N", (2, 3))):
    with np.errstate(invalid="ignore", divide="ignore"):
        d = (w @ agg["patch"][:, wi]) / (w @ agg["patch"][:, ni]) - (w @ agg["base"][:, wi]) / (w @ agg["base"][:, ni])
    d = d[np.isfinite(d)]
    res["diff_" + key] = {"point": res["patch"][key + "_gih_wr"] - res["base"][key + "_gih_wr"],
                          "ci95": [float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))], "valid_resamples": int(len(d))}

a_ok = res["patch"]["E_zero_creature_rate"] is not None and res["patch"]["E_zero_creature_rate"] <= 0.02
b_placebo = res["diff_N"]["ci95"][0] <= 0 <= res["diff_N"]["ci95"][1]
b_timeouts = res["patch"]["timeouts"] <= res["base"]["timeouts"] + 2
b_turns = abs(res["patch"]["mean_turns"] - res["base"]["mean_turns"]) <= 1.0
ratio = res["patch"]["E_casts_per_gih_game"] / res["base"]["E_casts_per_gih_game"]
c_ok = ratio >= 0.6
res["verdict"] = {"a_zero_creature_rate_le_2pct": a_ok, "b_placebo_ci_contains_0": b_placebo, "b_timeouts": b_timeouts,
                  "b_turns": b_turns, "c_cast_ratio": ratio, "c_ok": c_ok,
                  "result": "採用候補" if (a_ok and b_placebo and b_timeouts and b_turns and c_ok) else "不採用"}
print(json.dumps(res, ensure_ascii=False, indent=1))
if JSON_OUT:
    json.dump(res, open(JSON_OUT, "w"), ensure_ascii=False, indent=1)
