"""forge-debias の共通部品(再現 repro.py と本番の集計 score.py で同じものを使う)。"""
import json
import re
import unicodedata
from collections import defaultdict

import numpy as np
import pandas as pd

COLOR_GROUPS = ["W", "U", "B", "R", "G", "multi", "colorless"]
TYPE_GROUPS = ["creature", "instant_sorcery", "other"]


def norm(s):
    return re.sub(r"[^a-z0-9]", "", unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower())


def color_group(colors):
    c = "".join(ch for ch in str(colors or "") if ch in "WUBRG")
    if len(c) == 0:
        return "colorless"
    if len(c) > 1:
        return "multi"
    return c


def type_group(type_line):
    if not isinstance(type_line, str):
        return None
    if "Creature" in type_line:
        return "creature"
    if "Instant" in type_line or "Sorcery" in type_line:
        return "instant_sorcery"
    return "other"


def load_games(files):
    G = []
    for f in files:
        G += json.load(open(f))
    return G


def engine_gih(files):
    """引いたときの勝率。K1〜K4 と同じ: 1 試合・1 デッキで同じカードは 1 回だけ数える。勝者なしの試合は除く。"""
    w = defaultdict(int)
    n = defaultdict(int)
    for g in load_games(files):
        if g["winner"] is None:
            continue
        for dk, cards in g["draws"].items():
            win = int(g["winner"] == dk)
            for c in {norm(x) for x in cards}:
                n[c] += 1
                w[c] += win
    df = pd.DataFrame({"n": pd.Series(n), "w": pd.Series(w)})
    df["gih"] = df.w / df.n
    return df[["n", "gih"]]


def debias(d, mode="sequential"):
    """1 セット分。e_c = 色グループの平均を引いた e、e_t = タイプの平均を引いた e、
    e_ct = 色の平均を引き、次にタイプの平均を引いた e(sequential)。two_way は色とタイプのダミーへの回帰の残差。"""
    d = d.copy()
    d["e_c"] = d.e - d.groupby("cg").e.transform("mean")
    d["e_t"] = d.e - d.groupby("tg").e.transform("mean")
    if mode == "sequential":
        d["e_ct"] = d.e_c - d.groupby("tg").e_c.transform("mean")
    else:
        X = pd.get_dummies(d[["cg", "tg"]], drop_first=True).astype(float)
        X.insert(0, "const", 1.0)
        b = np.linalg.lstsq(X.values, d.e.values, rcond=None)[0]
        d["e_ct"] = d.e.values - X.values @ b
    return d
