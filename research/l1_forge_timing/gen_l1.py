"""L1 deck generator: random two-colour MSH decks in Forge .dck format.

usage: python3 -I gen_l1.py <FORGE_REPO> <OUT_DIR> <SEED> <N_DECKS> [PREFIX]
Reads the MSH edition list and card scripts from the Forge repo. Pool = nonland MSH cards whose colours fit a pair.
Deck = 23 spells (11-17 creatures, >=5 cards of each colour) + 17 basics (8/9). Rarity weights approximate a draft deck.
"""
import itertools
import os
import random
import re
import sys

REPO, OUT, SEED, N = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
PREFIX = sys.argv[5] if len(sys.argv) > 5 else "l1"
BASIC = {"W": "Plains", "U": "Island", "B": "Swamp", "R": "Mountain", "G": "Forest"}
RARITY_W = {"C": 0.60, "U": 0.28, "R": 0.09, "M": 0.03}


def norm(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


scripts = {}
for root, _, files in os.walk(os.path.join(REPO, "forge-gui/res/cardsfolder")):
    for f in files:
        if f.endswith(".txt"):
            scripts[norm(f[:-4])] = os.path.join(root, f)


def parse_script(path):
    name = cost = types = None
    for line in open(path, encoding="utf-8"):
        line = line.rstrip("\n")
        if line.startswith("ALTERNATE"):
            break  # only the front face
        if line.startswith("Name:") and name is None:
            name = line[5:]
        elif line.startswith("ManaCost:") and cost is None:
            cost = line[9:]
        elif line.startswith("Types:") and types is None:
            types = line[6:]
    return name, cost, types


pool = {}
in_cards = False
for line in open(os.path.join(REPO, "forge-gui/res/editions/Marvel Super Heroes.txt"), encoding="utf-8"):
    line = line.strip()
    if line == "[cards]":
        in_cards = True
        continue
    if line.startswith("[") and in_cards:
        break
    m = re.match(r"^\d+\s+([CURMS])\s+(.+?)(\s+@.*)?$", line)
    if not (in_cards and m):
        continue
    rarity, cname = m.group(1), m.group(2).split(" // ")[0].strip()
    if cname in pool or norm(cname) not in scripts:
        continue
    name, cost, types = parse_script(scripts[norm(cname)])
    if not types or "Land" in types.split() or not cost or cost == "no cost":
        continue
    colors = set(re.findall(r"[WUBRG]", cost.replace("P", "")))
    pool[cname] = {"rarity": rarity if rarity in RARITY_W else "C", "colors": colors,
                   "creature": "Creature" in types.split()}

PAIRS = ["".join(c) for c in itertools.combinations("WUBRG", 2)]
rng = random.Random(SEED)
os.makedirs(OUT, exist_ok=True)
made = set()
i = 0
while i < N:
    pair = rng.choice(PAIRS)
    cands = {n: c for n, c in pool.items() if c["colors"] <= set(pair)}
    names = list(cands)
    weights = [RARITY_W[cands[n]["rarity"]] for n in names]
    deck = []
    while len(deck) < 23:
        pick = rng.choices(names, weights)[0]
        if pick not in deck:
            deck.append(pick)
    ncr = sum(cands[n]["creature"] for n in deck)
    c0 = sum(pair[0] in cands[n]["colors"] for n in deck)
    c1 = sum(pair[1] in cands[n]["colors"] for n in deck)
    if not (11 <= ncr <= 17 and c0 >= 5 and c1 >= 5):
        continue
    key = tuple(sorted(deck))
    if key in made:
        continue
    made.add(key)
    name = f"{PREFIX}_{i:03d}_{pair}"
    lines = ["[metadata]", f"Name={name}", "[Main]"] + [f"1 {n}|MSH" for n in deck]
    lines += [f"8 {BASIC[pair[0]]}", f"9 {BASIC[pair[1]]}"]
    open(os.path.join(OUT, name + ".dck"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
    i += 1
print("pool", len(pool), "decks", i)
