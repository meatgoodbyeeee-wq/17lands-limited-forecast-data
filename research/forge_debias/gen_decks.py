"""forge-debias のデッキ生成(K3 の gen_k3.py と同じ規則。カードの出どころだけ TRK に対応)。

usage (research/ から): python3 -I forge_debias/gen_decks.py <FORGE_DIR> <OUT_DIR> <SET> [njobs] [decks_per_job] [seed]
  過去セット: c9_power_questions/cards.csv.gz(K3 の gen.pool と同じ。基本土地・auto・'//'・土地を除く)
  TRK: forge_debias/trk_cards.csv(サキヨミ™ 公開データ data/trk/target.json.gz から作成。土地・'//' を除く)
  Forge のカードフォルダにある名前だけを使う。
  1 デッキ = 2 色の組(ランダム)、その色に収まる非土地 23 枚(重複なし、クリーチャー 11〜17 枚)+ 基本土地 8 + 9。
  njobs × decks_per_job デッキ。ジョブ内の総当たりで対戦する(各組 1 試合)。
  出力: OUT_DIR/job<j>/<名前>.dck、OUT_DIR/pool.csv(使ったカード一覧)。
"""
import itertools
import os
import random
import re
import sys
import unicodedata

import pandas as pd

BASIC = {"W": "Plains", "U": "Island", "B": "Swamp", "R": "Mountain", "G": "Forest"}


def norm(s):
    return re.sub(r"[^a-z0-9]", "", unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower())


def pool(code):
    if code == "TRK":
        t = pd.read_csv("forge_debias/trk_cards.csv")
        t["colors"] = t.colors.fillna("")
        t = t[~t.type_line.str.contains("Land") & ~t.name.str.contains("//")]
        return t[["name", "mv", "colors", "type_line"]].rename(columns={"type_line": "tl"}).drop_duplicates("name")
    c = pd.read_csv("c9_power_questions/cards.csv.gz")
    rows = []
    for _, r in c.iterrows():
        for k in str(r["keys"]).split(";"):
            if k.startswith(code + "|"):
                n = k.split("|", 1)[1]
                if n in BASIC.values() or r["auto"] == 1 or "//" in n or "Land" in str(r["type_line"]):
                    continue
                rows.append(dict(name=n, mv=r["mv"], colors=r["colors"] if isinstance(r["colors"], str) else "",
                                 tl=r["type_line"]))
    return pd.DataFrame(rows).drop_duplicates("name")


if __name__ == "__main__":
    FD, OUT, CODE = sys.argv[1], sys.argv[2], sys.argv[3]
    NJ = int(sys.argv[4]) if len(sys.argv) > 4 else 8
    ND = int(sys.argv[5]) if len(sys.argv) > 5 else 40
    SEED = int(sys.argv[6]) if len(sys.argv) > 6 else 20261019
    fn = set()
    for r, _, fs in os.walk(FD + "/forge-gui/res/cardsfolder"):
        fn |= {norm(f[:-4]) for f in fs if f.endswith(".txt")}
    p0 = pool(CODE)
    p = p0[[norm(n) in fn for n in p0.name]].copy()
    missing = sorted(set(p0.name) - set(p.name))
    os.makedirs(OUT, exist_ok=True)
    p.to_csv(f"{OUT}/pool.csv", index=False)
    PAIRS = ["".join(c) for c in itertools.combinations("WUBRG", 2)]
    rng = random.Random(SEED)
    ok = {pr: p[p.colors.map(lambda c, pr=pr: set(c) <= set(pr))] for pr in PAIRS}
    cnt = 0
    for j in range(NJ):
        d = f"{OUT}/job{j}"
        os.makedirs(d, exist_ok=True)
        for i in range(ND):
            pr = rng.choice(PAIRS)
            pl = ok[pr]
            while True:
                sp = rng.sample(list(pl.name), 23)
                ncr = sum("Creature" in pl.set_index("name").loc[n].tl for n in sp)
                if 11 <= ncr <= 17:
                    break
            name = f"{CODE.lower()}_j{j}_d{i}_{pr}"
            lines = ["[metadata]", f"Name={name}", "[Main]"] + [f"1 {n}|{CODE}" for n in sp] + \
                    [f"8 {BASIC[pr[0]]}", f"9 {BASIC[pr[1]]}"]
            open(f"{d}/{name}.dck", "w").write("\n".join(lines) + "\n")
            cnt += 1
    print(f"{CODE}: decks {cnt}, pool {len(p)} / {len(p0)} (Forge にない {len(missing)}: {missing[:20]})")
