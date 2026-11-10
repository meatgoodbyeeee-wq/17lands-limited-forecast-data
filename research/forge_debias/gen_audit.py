"""監査用デッキ(PLAN.md §4)。すべてのカードが少なくとも 1 デッキに入るように 21 デッキを作る。

usage (research/ から): python3 -I forge_debias/gen_audit.py <FORGE_DIR> <OUT_DIR> <SET> [ndecks] [seed]
カードの規則は gen_decks.py と同じ(2 色、非土地 23 枚、重複なし、クリーチャー 11〜17、基本土地 8 + 9)。
2 色の組は 10 組を順に回す。各デッキは、まだ使われた回数の少ないカードを優先して選ぶ(同数の中はランダム)。
出力: OUT_DIR/job0/<名前>.dck、OUT_DIR/coverage.csv(カードごとの採用デッキ数)。
"""
import itertools
import os
import random
import sys
from collections import Counter

sys.path.insert(0, "forge_debias")
from gen_decks import BASIC, norm, pool  # noqa: E402

FD, OUT, CODE = sys.argv[1], sys.argv[2], sys.argv[3]
ND = int(sys.argv[4]) if len(sys.argv) > 4 else 21
SEED = int(sys.argv[5]) if len(sys.argv) > 5 else 20261110
fn = set()
for r, _, fs in os.walk(FD + "/forge-gui/res/cardsfolder"):
    fn |= {norm(f[:-4]) for f in fs if f.endswith(".txt")}
p0 = pool(CODE)
p = p0[[norm(n) in fn for n in p0.name]].copy()
cre = dict(zip(p.name, p.tl.map(lambda t: "Creature" in str(t))))
PAIRS = ["".join(c) for c in itertools.combinations("WUBRG", 2)]
rng = random.Random(SEED)
order = PAIRS[:]
rng.shuffle(order)
use = Counter()
d = f"{OUT}/job0"
os.makedirs(d, exist_ok=True)
for i in range(ND):
    pr = order[i % len(order)]
    ok = [n for n, c in zip(p.name, p.colors) if set(c) <= set(pr)]
    for _ in range(2000):
        cand = sorted(ok, key=lambda n: (use[n], rng.random()))
        sp = cand[:23]
        ncr = sum(cre[n] for n in sp)
        if 11 <= ncr <= 17:
            break
        # クリーチャーの数を合わせる: 多すぎ・少なすぎの側を 1 枚入れ替える
        want_cre = ncr < 11
        rest = [n for n in cand[23:] if cre[n] == want_cre]
        drop = [n for n in sp if cre[n] != want_cre]
        while not (11 <= ncr <= 17) and rest and drop:
            out, inn = drop.pop(), rest.pop(0)
            sp[sp.index(out)] = inn
            ncr += 1 if want_cre else -1
        if 11 <= ncr <= 17:
            break
    for n in sp:
        use[n] += 1
    name = f"{CODE.lower()}_audit_d{i}_{pr}"
    lines = ["[metadata]", f"Name={name}", "[Main]"] + [f"1 {n}|{CODE}" for n in sp] + \
            [f"8 {BASIC[pr[0]]}", f"9 {BASIC[pr[1]]}"]
    open(f"{d}/{name}.dck", "w").write("\n".join(lines) + "\n")
with open(f"{OUT}/coverage.csv", "w") as f:
    f.write("name,decks\n")
    for n in p.name:
        f.write(f"\"{n}\",{use[n]}\n")
print(f"{CODE}: audit decks {ND}, cards {len(p)}, not covered {sum(use[n] == 0 for n in p.name)}, "
      f"max decks per card {max(use.values())}")
