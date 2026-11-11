"""監査の原因の切り分け(PLAN.md §4)。research/forge_debias から実行する。

usage: python3 -I audit_diag.py <diag_dir> <label>
<diag_dir>/<SET>/job0.json(試合)と job0.out.gz の「Diag:」行(FORGE_DIAG=1 で回した監査)を読む。
  Diag 行: AI が手札の呪文を唱えるか判断したときの結果(AiPlayDecision)と、土地の数がマナ総量以上か(L / l)。
  1 試合の Diag 行は、その試合の「Timeouts:」行の直後に出る(試合番号の欄は総当たりでは常に 1 なので使わない)。
カードごと(引いた回数 10 以上)に:
  rate     手札に残る割合(このディレクトリの試合で計算)
  g_eval   土地が足りている状態で判断された試合の数
  g_will   唱える(WillPlay など)と判断した試合の数
  cls      no_eval(g_eval = 0)/ never(g_will / g_eval < 0.10)/ rare(< 0.40)/ often
  top      土地が足りているときの、唱えない理由の上位 3 つ(判断の回数)
出力: audit/<label>_cards.csv(全カード)。30% 超のカードの分類の表を表示する。
"""
import gzip
import json
import os
import sys
from collections import Counter, defaultdict

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from debias_lib import norm  # noqa: E402

D, LABEL = sys.argv[1], sys.argv[2]
PLAY = ("WillPlay", "MandatoryPlay", "PlayToEmptyHand")
BASICS = {norm(b) for b in ("Plains", "Island", "Swamp", "Mountain", "Forest")}
rows = []
for s in ("ECL", "TLA", "EOE", "TRK"):
    if not os.path.exists(f"{D}/{s}/job0.json"):
        continue
    drawn, kept, nm = Counter(), Counter(), {}
    for g in json.load(open(f"{D}/{s}/job0.json")):
        for deck, cards in g["draws"].items():
            hand = {norm(c) for c in g["hand_end"].get(deck, [])}
            for c in cards:
                k = norm(c)
                if k in BASICS or k in nm and nm[k] is None:
                    continue
                nm.setdefault(k, c)
            for k in {norm(c) for c in cards} - BASICS:
                drawn[k] += 1
                kept[k] += k in hand
    ge, gw, why = defaultdict(set), defaultdict(set), defaultdict(Counter)
    g = 0
    for line in gzip.open(f"{D}/{s}/job0.out.gz", "rt", errors="replace"):
        if line.startswith("Timeouts: "):
            g += 1
        elif line.startswith("Diag:\t"):
            _, _, name, dec, land, n = line.rstrip("\n").split("\t")
            k = norm(name)
            if land == "L":
                ge[k].add(g)
                if dec not in PLAY:
                    why[k][dec] += int(n)
            if dec in PLAY:
                gw[k].add(g)
    for k in drawn:
        if drawn[k] < 10:
            continue
        e, w = len(ge[k]), len(gw[k])
        cls = "no_eval" if e == 0 else ("never" if w / e < 0.10 else ("rare" if w / e < 0.40 else "often"))
        rows.append(dict(set=s, name=nm[k], drawn=drawn[k], kept=kept[k], rate=round(kept[k] / drawn[k], 3),
                         g_eval=e, g_will=w, cls=cls,
                         top=";".join(f"{d}:{n}" for d, n in why[k].most_common(3))))
df = pd.DataFrame(rows)
df.to_csv(f"audit/{LABEL}_cards.csv", index=False)
f = df[df.rate > 0.30]
print(f"30% 超: {len(f)} 枚")
print(f.groupby(["set", "cls"]).size().unstack(fill_value=0))
