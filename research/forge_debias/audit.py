"""監査の集計(PLAN.md §4)。usage (forge_debias/ から): python3 -I audit.py <SET> [games_dir]
カードごとに: 引いた回数(試合・デッキ単位)、終了時に手札にあった回数、手札に残る割合。
出力: audit/<SET>/retention.csv。引いた回数 10 回以上で 30% 超のカードを表示する。
"""
import glob
import json
import sys
from collections import Counter

import os

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from debias_lib import norm

SET = sys.argv[1]
GD = sys.argv[2] if len(sys.argv) > 2 else f"audit/{SET}/games"
drawn, kept, name_of = Counter(), Counter(), {}
games = 0
for f in sorted(glob.glob(GD + "/job*.json")):
    for g in json.load(open(f)):
        games += 1
        for deck, cards in g["draws"].items():
            hand = {norm(c) for c in g["hand_end"].get(deck, [])}
            for c in {norm(x): x for x in cards}.items():
                k, nm = c
                name_of.setdefault(k, nm)
                drawn[k] += 1
                kept[k] += k in hand
basics = {norm(b) for b in ("Plains", "Island", "Swamp", "Mountain", "Forest")}
rows = [dict(name=name_of[k], drawn=drawn[k], kept=kept[k], rate=kept[k] / drawn[k]) for k in drawn if k not in basics]
df = pd.DataFrame(rows).sort_values("rate", ascending=False)
df.to_csv(f"audit/{SET}/retention.csv", index=False)
big = df[df.drawn >= 10]
print(f"{SET}: games {games}, cards drawn {len(df)}, drawn>=10 {len(big)}, drawn<10 {len(df) - len(big)}, "
      f"median rate {big.rate.median():.2f}")
print(big[big.rate > 0.30].to_string(index=False))
