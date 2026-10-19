"""L1 analysis per PLAN.md (and its amendment 1).

usage: python3 -I analyze_l1.py <OUT_DIR> [JSON_OUT]
Reads <OUT_DIR>/g*.log lines:
 card|chain|phase|turn|ownTurn|inCombat|stackBelow|ownCreatures|oppCreatures|isAI|isInstant|isFlash|player
Class = root API of the spell (first element of the chain).
Only casts with a combat opportunity (any creature on either side) are counted.
"out of combat" = cast in a non-combat phase with an empty stack (stackBelow == 0).
"""
import collections
import glob
import json
import math
import os
import sys

OUT = sys.argv[1]
JSON_OUT = sys.argv[2] if len(sys.argv) > 2 else None
NONCOMBAT = {"UPKEEP", "DRAW", "MAIN1", "MAIN2", "END_OF_TURN", "CLEANUP"}
MIN_N = 30


def wilson(k, n, z=1.96):
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (c - h, c + h)


rows = []
for path in sorted(glob.glob(os.path.join(OUT, "g*.log"))):
    for line in open(path, encoding="utf-8"):
        f = line.rstrip("\n").split("|")
        if len(f) != 13:
            continue
        rows.append({"card": f[0], "chain": f[1], "cls": f[1].split(">")[0], "phase": f[2], "turn": int(f[3]),
                     "own": f[4] == "true", "combat": f[5] == "true", "below": int(f[6]),
                     "nown": int(f[7]), "nopp": int(f[8]), "inst": f[10] == "true", "flash": f[11] == "true"})

opp = [r for r in rows if r["nown"] + r["nopp"] >= 1]
print(f"casts logged {len(rows)}, with combat opportunity {len(opp)}")

by = collections.defaultdict(list)
for r in opp:
    by[r["cls"]].append(r)

summary = {}
print(f"\n{'class':22s} {'n':>5s} {'out-of-combat':>14s} {'95% CI':>16s} {'own upk+draw':>13s} {'own combat':>11s}")
for cls, rs in sorted(by.items(), key=lambda kv: -len(kv[1])):
    n = len(rs)
    out = sum(1 for r in rs if r["phase"] in NONCOMBAT and r["below"] == 0)
    ud = sum(1 for r in rs if r["own"] and r["phase"] in ("UPKEEP", "DRAW"))
    cb = sum(1 for r in rs if r["own"] and r["phase"].startswith("COMBAT_"))
    lo, hi = wilson(out, n)
    summary[cls] = {"n": n, "out": out, "out_rate": out / n, "ci": [lo, hi], "own_upkeep_draw": ud / n, "own_combat": cb / n}
    flag = "" if n >= MIN_N else "  (n<30: 判定不能)"
    print(f"{cls:22s} {n:5d} {out / n:14.1%} [{lo:5.1%},{hi:5.1%}] {ud / n:13.1%} {cb / n:11.1%}{flag}")


def rate(cls):
    s = summary.get(cls)
    return s if s and s["n"] >= MIN_N else None


print("\n--- 事前仮説の判定 (集合のデータのみ。n<30 は判定不能) ---")
verdict = {}
p, pa = rate("Pump"), rate("PumpAll")
verdict["H1"] = None if not p else p["out_rate"] <= 0.20
verdict["H2"] = None if not (p and pa) else (pa["out_rate"] - p["out_rate"]) >= 0.20
pn = rate("PermanentNoncreature")
verdict["H3"] = None if not pn else pn["own_upkeep_draw"] >= 0.20
verdict["H4"] = None if not pn else pn["own_combat"] < 0.20
names = {"H1": "Pump の戦闘外使用率 <= 20%", "H2": "PumpAll - Pump の戦闘外使用率差 >= 20pt",
         "H3": "PermanentNoncreature の自分のアップキープ+ドロー使用率 >= 20%",
         "H4": "PermanentNoncreature の自分の戦闘中使用率 < 20%"}
for h in ("H1", "H2", "H3", "H4"):
    v = verdict[h]
    print(f"{h}: {names[h]} -> {'判定不能' if v is None else ('成立' if v else '不成立')}")

print("\n--- フェイズ分布 (上位クラス、戦闘機会ありの使用) ---")
for cls, rs in sorted(by.items(), key=lambda kv: -len(kv[1]))[:8]:
    c = collections.Counter(("自" if r["own"] else "相") + ":" + r["phase"] for r in rs)
    print(cls, dict(c.most_common(8)))

print("\n--- Avengers Assemble! (クラスの内訳として) ---")
aa = [r for r in opp if r["card"] == "Avengers Assemble!"]
print(len(aa), "casts;", dict(collections.Counter(("自" if r["own"] else "相") + ":" + r["phase"] for r in aa)))

if JSON_OUT:
    json.dump({"casts": len(rows), "casts_with_opportunity": len(opp), "classes": summary, "verdict": verdict},
              open(JSON_OUT, "w"), ensure_ascii=False, indent=1, default=lambda x: None)
