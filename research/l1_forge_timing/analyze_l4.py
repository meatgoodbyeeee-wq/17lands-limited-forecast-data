"""L4 analysis per PLAN_L4.md.

usage: python3 -I analyze_l4.py <DECK_DIR_D> <OUT_BASE> <OUT_PATCH> [JSON_OUT]
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
F = {"Plumecreed Escort", "Fang Guardian"}
S = {"Zack Fair", "Selfless Samurai", "Spectacular Spider-Man", "Alseid of Life's Bounty", "Hakoda, Selfless Commander"}
BASICS = {"Plains", "Island", "Swamp", "Mountain", "Forest"}
deck_names = sorted(os.path.basename(p)[:-4] for p in glob.glob(os.path.join(DECKS, "*.dck")))
idx = {d: i for i, d in enumerate(deck_names)}


def strip_ai(n):
    return re.sub(r"^Ai\(\d+\)-", "", n)


def f_meaningful(e):
    # response to an opposing object, any combat step, or an end step
    return e["opp"] or e["phase"].startswith("COMBAT_") or e["phase"] == "END_OF_TURN"


def s_meaningful(e):
    return e["opp"] or e["phase"] in ("COMBAT_DECLARE_BLOCKERS", "COMBAT_FIRST_STRIKE_DAMAGE", "COMBAT_DAMAGE")


def load(out):
    games = []
    for path in sorted(glob.glob(os.path.join(out, "g*.log"))):
        cur = None
        for line in open(path, encoding="utf-8"):
            f = line.rstrip("\n").split("|")
            if f[0] == "START":
                cur = {"draw": collections.defaultdict(set), "lines": collections.Counter(), "winner": None, "ended": False, "ev": []}
                games.append(cur)
            elif cur is None:
                continue
            elif f[0] == "DRAW":
                cur["draw"][strip_ai(f[2])].add(f[1])
                cur["lines"][strip_ai(f[2])] += 1
            elif f[0] == "END":
                cur["winner"] = None if f[1] in ("null", "None") else strip_ai(f[1])
                cur["ended"] = True
            elif f[0] == "L4" and len(f) == 13:
                cur["ev"].append({"kind": f[1], "card": f[2], "api": f[3], "phase": f[4], "own": f[6] == "true",
                                  "opp": f[9] == "true", "sac": f[10] == "true", "player": strip_ai(f[12])})
    turns, tt = [], 0
    for path in sorted(glob.glob(os.path.join(out, "g*.out"))):
        txt = open(path, encoding="utf-8", errors="replace").read()
        turns += [int(t) for t in re.findall(r"Game Outcome: Turn (\d+)", txt)]
        tt += txt.count("Stopping slow match")
    return games, turns, tt


res, agg = {}, {}
for name, out in (("base", OUT_BASE), ("patch", OUT_PATCH)):
    games, turns, tt = load(out)
    a = np.zeros((len(deck_names), 6))  # F wins,n  S wins,n  N wins,n
    per_card = collections.defaultdict(lambda: [0, 0])
    f_casts, s_uses = [], []
    f_drawn = f_drawn_cast = 0
    s_gih = 0
    for g in games:
        evs = g["ev"]
        f_casts += [e for e in evs if e["kind"] == "SPELL" and e["card"] in F]
        s_uses += [e for e in evs if e["kind"] == "ABIL" and e["card"] in S and e["sac"]]
        for deck, cards in g["draw"].items():
            for c in cards & F:
                f_drawn += 1
                f_drawn_cast += any(e["kind"] == "SPELL" and e["card"] == c and e["player"] == deck for e in evs)
            s_gih += len(cards & S)
        if not g["ended"] or g["winner"] is None:
            continue
        for deck, cards in g["draw"].items():
            if deck not in idx:
                continue
            won = int(g["winner"] == deck)
            for c in cards:
                if c in BASICS:
                    continue
                k = 0 if c in F else 2 if c in S else 4
                a[idx[deck], k] += won
                a[idx[deck], k + 1] += 1
                if k < 4:
                    per_card[c][0] += won
                    per_card[c][1] += 1
    agg[name] = a
    lines = [v for g in games for v in g["lines"].values()]
    unfinished = len(games) - sum(g["ended"] for g in games)
    fm = sum(map(f_meaningful, f_casts))
    sm = sum(map(s_meaningful, s_uses))
    res[name] = {
        "games": len(games), "timeouts": max(tt, unfinished), "mean_turns": float(np.mean(turns)) if turns else None,
        "draw_lines_per_player": float(np.mean(lines)) if lines else None,
        "F_casts": len(f_casts), "F_meaningful": fm, "F_pointless_rate": (len(f_casts) - fm) / len(f_casts) if f_casts else None,
        "F_cast_phase": dict(collections.Counter(("自" if e["own"] else "相") + ":" + e["phase"] + (" 対応" if e["opp"] else "") for e in f_casts).most_common()),
        "F_drawn": f_drawn, "F_drawn_never_cast_rate": 1 - f_drawn_cast / f_drawn if f_drawn else None,
        "S_uses": len(s_uses), "S_meaningful": sm, "S_meaningful_rate": sm / len(s_uses) if s_uses else None,
        "S_gih_games": s_gih, "S_uses_per_gih": len(s_uses) / s_gih if s_gih else None,
        "S_use_phase": dict(collections.Counter(e["card"] + " @" + ("自" if e["own"] else "相") + ":" + e["phase"] + (" 対応" if e["opp"] else "") for e in s_uses).most_common()),
        "per_card": {c: v for c, v in sorted(per_card.items())},
    }
    for key, k in (("F", 0), ("S", 2), ("N", 4)):
        n = a[:, k + 1].sum()
        res[name][key + "_gih_n"] = int(n)
        res[name][key + "_gih_wr"] = float(a[:, k].sum() / n) if n else None

rng = np.random.default_rng(20261019)
w = rng.multinomial(len(deck_names), [1 / len(deck_names)] * len(deck_names), size=10000)
for key, k in (("F", 0), ("S", 2), ("N", 4)):
    with np.errstate(invalid="ignore", divide="ignore"):
        d = (w @ agg["patch"][:, k]) / (w @ agg["patch"][:, k + 1]) - (w @ agg["base"][:, k]) / (w @ agg["base"][:, k + 1])
    d = d[np.isfinite(d)]
    res["diff_" + key] = {"point": res["patch"][key + "_gih_wr"] - res["base"][key + "_gih_wr"],
                          "ci95": [float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))], "valid_resamples": int(len(d))}

b_placebo = res["diff_N"]["ci95"][0] <= 0 <= res["diff_N"]["ci95"][1]
b_timeouts = res["patch"]["timeouts"] <= res["base"]["timeouts"] + 2
b_turns = abs(res["patch"]["mean_turns"] - res["base"]["mean_turns"]) <= 1.0
b_ok = b_placebo and b_timeouts and b_turns
aF = res["patch"]["F_pointless_rate"] is not None and res["patch"]["F_pointless_rate"] <= 0.25
dS = (res["patch"]["S_uses_per_gih"] or 0) - (res["base"]["S_uses_per_gih"] or 0)
aS = dS >= 0.05 and (res["patch"]["S_meaningful_rate"] or 0) >= 0.80
res["verdict"] = {"b_placebo_ci_contains_0": b_placebo, "b_timeouts": b_timeouts, "b_turns": b_turns,
                  "aF_pointless_le_25pct": aF, "aS_uses_per_gih_diff": dS, "aS_ok": aS,
                  "F_part": "採用候補" if (aF and b_ok) else "不採用", "S_part": "採用候補" if (aS and b_ok) else "不採用"}
print(json.dumps(res, ensure_ascii=False, indent=1))
if JSON_OUT:
    json.dump(res, open(JSON_OUT, "w"), ensure_ascii=False, indent=1)
