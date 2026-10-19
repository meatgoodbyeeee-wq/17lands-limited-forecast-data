"""L5a analysis per PLAN_L5a.md.

usage: python3 -I analyze_l5a.py <DECK_DIR_E> <OUT_BASE> <OUT_PATCH> [JSON_OUT]
Log lines: START / DRAW|card|player / END|winner / L4|kind|card|api|phase|turn|ownTurn|inCombat|stackBelow|oppOnStack|sacSelf|ownCreatures|player
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
T = {"Artificer's Epiphany", "Catalog", "Enhanced Awareness", "Prying Eyes", "Quick Study", "Rain of Revelation",
     "Succumb to Temptation", "Thirst for Discovery", "Thirst for Identity", "Thirst for Knowledge", "Thirst for Meaning",
     "Tragic Lesson"}
BASICS = {"Plains", "Island", "Swamp", "Mountain", "Forest"}
deck_names = sorted(os.path.basename(p)[:-4] for p in glob.glob(os.path.join(DECKS, "*.dck")))
idx = {d: i for i, d in enumerate(deck_names)}


def strip_ai(n):
    return re.sub(r"^Ai\(\d+\)-", "", n)


def load(out):
    games = []
    for path in sorted(glob.glob(os.path.join(out, "g*.log"))):
        cur = None
        for line in open(path, encoding="utf-8"):
            f = line.rstrip("\n").split("|")
            if f[0] == "START":
                cur = {"draw": collections.defaultdict(set), "lines": collections.Counter(), "winner": None, "ended": False, "casts": []}
                games.append(cur)
            elif cur is None:
                continue
            elif f[0] == "DRAW":
                cur["draw"][strip_ai(f[2])].add(f[1])
                cur["lines"][strip_ai(f[2])] += 1
            elif f[0] == "END":
                cur["winner"] = None if f[1] in ("null", "None") else strip_ai(f[1])
                cur["ended"] = True
            elif f[0] == "L4" and len(f) == 13 and f[1] == "SPELL" and f[2] in T:
                cur["casts"].append({"card": f[2], "phase": f[4], "own": f[6] == "true", "opp": f[9] == "true"})
    turns, tt = [], 0
    for path in sorted(glob.glob(os.path.join(out, "g*.out"))):
        txt = open(path, encoding="utf-8", errors="replace").read()
        turns += [int(t) for t in re.findall(r"Game Outcome: Turn (\d+)", txt)]
        tt += txt.count("Stopping slow match")
    return games, turns, tt


res, agg = {}, {}
for name, out in (("base", OUT_BASE), ("patch", OUT_PATCH)):
    games, turns, tt = load(out)
    a = np.zeros((len(deck_names), 4))  # T wins,n  N wins,n
    per_card = collections.defaultdict(lambda: [0, 0])
    casts = [c for g in games for c in g["casts"]]
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
                k = 0 if c in T else 2
                a[idx[deck], k] += won
                a[idx[deck], k + 1] += 1
                if k == 0:
                    per_card[c][0] += won
                    per_card[c][1] += 1
    agg[name] = a
    eot = sum(1 for c in casts if not c["own"] and c["phase"] == "END_OF_TURN")
    lines = [v for g in games for v in g["lines"].values()]
    unfinished = len(games) - sum(g["ended"] for g in games)
    t_gih = int(a[:, 1].sum())
    res[name] = {
        "games": len(games), "timeouts": max(tt, unfinished), "mean_turns": float(np.mean(turns)) if turns else None,
        "draw_lines_per_player": float(np.mean(lines)) if lines else None,
        "T_casts": len(casts), "T_opp_eot_casts": eot, "T_opp_eot_rate": eot / len(casts) if casts else None,
        "T_cast_phase": dict(collections.Counter(("自" if c["own"] else "相") + ":" + c["phase"] for c in casts).most_common()),
        "T_gih_n": t_gih, "T_gih_wr": float(a[:, 0].sum() / t_gih) if t_gih else None,
        "T_casts_per_gih": len(casts) / t_gih if t_gih else None,
        "N_gih_n": int(a[:, 3].sum()), "N_gih_wr": float(a[:, 2].sum() / a[:, 3].sum()),
        "per_card_T": {c: v for c, v in sorted(per_card.items())},
    }

rng = np.random.default_rng(20261019)
w = rng.multinomial(len(deck_names), [1 / len(deck_names)] * len(deck_names), size=10000)
for key, k in (("T", 0), ("N", 2)):
    with np.errstate(invalid="ignore", divide="ignore"):
        d = (w @ agg["patch"][:, k]) / (w @ agg["patch"][:, k + 1]) - (w @ agg["base"][:, k]) / (w @ agg["base"][:, k + 1])
    d = d[np.isfinite(d)]
    res["diff_" + key] = {"point": res["patch"][key + "_gih_wr"] - res["base"][key + "_gih_wr"],
                          "ci95": [float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))], "valid_resamples": int(len(d))}

a_ok = (res["patch"]["T_opp_eot_rate"] or 0) >= 0.70
ratio = res["patch"]["T_casts_per_gih"] / res["base"]["T_casts_per_gih"]
c_ok = ratio >= 0.6
b_placebo = res["diff_N"]["ci95"][0] <= 0 <= res["diff_N"]["ci95"][1]
b_timeouts = res["patch"]["timeouts"] <= res["base"]["timeouts"] + 2
b_turns = abs(res["patch"]["mean_turns"] - res["base"]["mean_turns"]) <= 1.0
res["verdict"] = {"a_opp_eot_rate_ge_70pct": a_ok, "c_cast_ratio": ratio, "c_ok": c_ok, "b_placebo_ci_contains_0": b_placebo,
                  "b_timeouts": b_timeouts, "b_turns": b_turns,
                  "result": "採用候補" if (a_ok and c_ok and b_placebo and b_timeouts and b_turns) else "不採用"}
print(json.dumps(res, ensure_ascii=False, indent=1))
if JSON_OUT:
    json.dump(res, open(JSON_OUT, "w"), ensure_ascii=False, indent=1)
