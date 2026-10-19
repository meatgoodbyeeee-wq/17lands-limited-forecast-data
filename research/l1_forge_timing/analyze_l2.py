"""L2' analysis per PLAN_L2prime.md.

usage: python3 -I analyze_l2.py <FORGE_REPO> <DECK_DIR_B> <OUT_BASE> <OUT_PATCH> [JSON_OUT]
Log lines (per group file g*.log, games run sequentially in one JVM):
  START | DRAW|card|player | END|winner | cast lines (13 fields, see analyze_l1.py)
Player names in DRAW/END are plain deck names; cast lines use "Ai(n)-<deck>" (prefix stripped here).
Target class T: cards whose script has K:Flash and whose Types contain none of
Creature/Instant/Sorcery/Land/Aura. N: every other non-basic-land card seen in the decks.
GIH = the card entered the hand from the library at least once in that game.
Primary metric: GIH WR(T, patched) - GIH WR(T, base), 95% CI by cluster bootstrap over decks (10000, seed 20261019).
"""
import collections
import glob
import json
import os
import re
import sys

import numpy as np

REPO, DECKS, OUT_BASE, OUT_PATCH = sys.argv[1:5]
JSON_OUT = sys.argv[5] if len(sys.argv) > 5 else None
BASICS = {"Plains", "Island", "Swamp", "Mountain", "Forest"}
NONCOMBAT_OWN = ("UPKEEP", "DRAW")


def norm(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


# ---- card classes from scripts (independent of results)
scripts = {}
for root, _, files in os.walk(os.path.join(REPO, "forge-gui/res/cardsfolder")):
    for f in files:
        if f.endswith(".txt"):
            scripts[norm(f[:-4])] = os.path.join(root, f)

deck_cards = set()
deck_names = []
for p in sorted(glob.glob(os.path.join(DECKS, "*.dck"))):
    deck_names.append(os.path.basename(p)[:-4])
    for line in open(p, encoding="utf-8"):
        m = re.match(r"^\d+ (.+?)\|", line)
        if m and m.group(1) not in BASICS:
            deck_cards.add(m.group(1))


def front_face(path):
    flash, types = False, ""
    for line in open(path, encoding="utf-8"):
        if line.startswith("ALTERNATE"):
            break
        if line.startswith("K:Flash"):
            flash = True
        elif line.startswith("Types:") and not types:
            types = line[6:].strip()
    return flash, types.split()


T, N = set(), set()
for c in sorted(deck_cards):
    path = scripts.get(norm(c.split(" // ")[0]))
    if not path:
        continue
    flash, types = front_face(path)
    if flash and not set(types) & {"Creature", "Instant", "Sorcery", "Land", "Aura"}:
        T.add(c)
    else:
        N.add(c)
print("target class T (%d):" % len(T), sorted(T))


def strip_ai(n):
    return re.sub(r"^Ai\(\d+\)-", "", n)


def load(out):
    games, casts = [], []
    for path in sorted(glob.glob(os.path.join(out, "g*.log"))):
        cur = None
        for line in open(path, encoding="utf-8"):
            line = line.rstrip("\n")
            if line == "START":
                cur = {"group": os.path.basename(path), "draw": collections.defaultdict(set), "winner": None, "ended": False}
                games.append(cur)
            elif line.startswith("DRAW|") and cur is not None:
                _, c, o = line.split("|")
                cur["draw"][strip_ai(o)].add(c)
            elif line.startswith("END|") and cur is not None:
                w = line.split("|", 1)[1]
                cur["winner"] = None if w in ("null", "None") else strip_ai(w)
                cur["ended"] = True
            else:
                f = line.split("|")
                if len(f) == 13:
                    casts.append({"card": f[0], "cls": f[1].split(">")[0], "phase": f[2], "own": f[4] == "true",
                                  "opp": int(f[7]) + int(f[8]) >= 1})
    turns = []
    for path in sorted(glob.glob(os.path.join(out, "g*.out"))):
        for line in open(path, encoding="utf-8", errors="replace"):
            m = re.match(r"Game Outcome: Turn (\d+)", line)
            if m:
                turns.append(int(m.group(1)))
    timeouts = sum(open(p, encoding="utf-8", errors="replace").read().count("Stopping slow match")
                   for p in glob.glob(os.path.join(out, "g*.out")))
    return games, casts, turns, timeouts


def per_deck(games):
    """deck -> {'T': [wins, n], 'N': [wins, n]} and per-card stats."""
    agg = {d: {"T": [0, 0], "N": [0, 0]} for d in deck_names}
    card = collections.defaultdict(lambda: [0, 0])
    for g in games:
        if not g["ended"] or g["winner"] is None:
            continue
        for deck, cards in g["draw"].items():
            if deck not in agg:
                continue
            won = int(g["winner"] == deck)
            for c in cards:
                if c in BASICS:
                    continue
                k = "T" if c in T else "N"
                agg[deck][k][0] += won
                agg[deck][k][1] += 1
                if k == "T":
                    card[c][0] += won
                    card[c][1] += 1
    return agg, card


def draws_per_player(games):
    v = [len(cs) for g in games for cs in g["draw"].values()]
    return float(np.mean(v)) if v else float("nan")


res = {}
data = {}
for name, out in (("base", OUT_BASE), ("patch", OUT_PATCH)):
    games, casts, turns, timeouts = load(out)
    agg, card = per_deck(games)
    pn = [c for c in casts if c["cls"] == "PermanentNoncreature" and c["opp"]]
    upk = sum(1 for c in pn if c["own"] and c["phase"] in NONCOMBAT_OWN)
    dist = collections.Counter(("自" if c["own"] else "相") + ":" + c["phase"] for c in pn)
    data[name] = {"agg": agg, "card": card}
    # a timeout draw = a game that started but has no END line (or is reported by the sim output); take the larger count
    unfinished = len(games) - sum(g["ended"] for g in games)
    res[name] = {"games": len(games), "ended": sum(g["ended"] for g in games), "timeouts": max(timeouts, unfinished),
                 "mean_turns": float(np.mean(turns)) if turns else None, "draws_per_player": draws_per_player(games),
                 "pn_casts": len(pn), "pn_upkeep_draw": upk, "pn_upkeep_draw_rate": upk / len(pn) if pn else None,
                 "pn_phase_dist": dict(dist.most_common()),
                 "aa_casts": [(("自" if c["own"] else "相") + ":" + c["phase"]) for c in casts if c["card"] == "Avengers Assemble!"]}
    for k in ("T", "N"):
        w = sum(a[k][0] for a in agg.values())
        n = sum(a[k][1] for a in agg.values())
        res[name][k + "_wr"] = w / n if n else None
        res[name][k + "_n"] = n

# ---- paired cluster bootstrap over decks
rng = np.random.default_rng(20261019)
idx = {d: i for i, d in enumerate(deck_names)}


def arr(name, k):
    a = np.zeros((len(deck_names), 2))
    for d, v in data[name]["agg"].items():
        a[idx[d]] = v[k]
    return a


A = {(nm, k): arr(nm, k) for nm in ("base", "patch") for k in ("T", "N")}
B = 10000
w = rng.multinomial(len(deck_names), [1 / len(deck_names)] * len(deck_names), size=B)  # B x D deck weights
boot = {}
for k in ("T", "N"):
    rates = {}
    for nm in ("base", "patch"):
        wins = w @ A[(nm, k)][:, 0]
        n = w @ A[(nm, k)][:, 1]
        with np.errstate(invalid="ignore", divide="ignore"):
            rates[nm] = wins / n
    d = rates["patch"] - rates["base"]
    d = d[np.isfinite(d)]
    boot[k] = d
    res["diff_" + k] = {"point": (res["patch"][k + "_wr"] or float("nan")) - (res["base"][k + "_wr"] or float("nan")),
                        "ci95": [float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))], "valid_resamples": int(len(d))}

# ---- verdict (PLAN_L2prime.md)
a_ok = res["patch"]["pn_upkeep_draw_rate"] is not None and res["patch"]["pn_upkeep_draw_rate"] <= 0.05
b_lo, b_hi = res["diff_T"]["ci95"]
c_placebo = res["diff_N"]["ci95"][0] <= 0 <= res["diff_N"]["ci95"][1]
c_timeout = res["patch"]["timeouts"] <= res["base"]["timeouts"] + 2
c_turns = (res["base"]["mean_turns"] is not None and res["patch"]["mean_turns"] is not None
           and abs(res["patch"]["mean_turns"] - res["base"]["mean_turns"]) <= 1.0)
c_ok = c_placebo and c_timeout and c_turns
if a_ok and c_ok and b_lo > 0:
    verdict = "効果あり"
elif b_hi < 0:
    verdict = "悪化"
else:
    verdict = "効果は検出できず"
res["verdict"] = {"a_patch_works": a_ok, "c_placebo_ci_contains_0": c_placebo, "c_timeouts": c_timeout, "c_turns": c_turns,
                  "b_ci95": [b_lo, b_hi], "result": verdict}

# ---- per-card detail (report only)
detail = {}
for c in sorted(T):
    b, p = data["base"]["card"].get(c, [0, 0]), data["patch"]["card"].get(c, [0, 0])
    detail[c] = {"base": b, "patch": p,
                 "base_wr": b[0] / b[1] if b[1] else None, "patch_wr": p[0] / p[1] if p[1] else None}
res["per_card_T"] = detail

print(json.dumps(res, ensure_ascii=False, indent=1))
if JSON_OUT:
    json.dump(res, open(JSON_OUT, "w"), ensure_ascii=False, indent=1)
