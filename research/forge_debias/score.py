"""forge-debias の集計と採点(PLAN.md §5〜§7)。research/ から実行する。

usage:
  python3 -I forge_debias/score.py past [JSON_OUT]        # 過去 3 セット(ECL・TLA・EOE)の採点。事前登録の採点は 1 回だけ
  python3 -I forge_debias/score.py freeze-trk              # TRK の値を凍結(trk_frozen_e.csv)。実測は使わない
  python3 -I forge_debias/score.py score-trk <actual_csv> [JSON_OUT]   # TRK の採点(列: name, actual_gih(小数), gih_games)
  python3 -I forge_debias/score.py dry-run                 # 合成の実測で動作確認(結果は使わない)
"""
import glob
import json
import os
import random
import sys
from collections import defaultdict

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, "forge_debias")
from debias_lib import color_group, type_group, norm, load_games  # noqa: E402

PAST = ["ECL", "TLA", "EOE"]
K = 0.10
GDIR = "forge_debias/games/{}"
DECKS = "forge_debias/decks/{}"
VALS = ["e", "e_c", "e_t", "e_ct"]
BASICS = {norm(b) for b in ("Plains", "Island", "Swamp", "Mountain", "Forest")}


def games(code):
    return load_games(sorted(glob.glob(GDIR.format(code) + "/job?.json")))


def deck_contents(code):
    out = {}
    for f in glob.glob(DECKS.format(code) + "/job*/*.dck"):
        name, cards = None, set()
        for line in open(f):
            line = line.strip()
            if line.startswith("Name="):
                name = line[5:]
            elif line[:1].isdigit():
                nm = line.split(" ", 1)[1].split("|")[0]
                if norm(nm) not in BASICS:
                    cards.add(norm(nm))
        out[name] = cards
    return out


def card_stats(code):
    """引いたときの勝率(e_raw の元)、デッキ内の差(IWD)、手札に残る割合。勝者なしの試合は除く。"""
    G = games(code)
    dk = deck_contents(code)
    n, w = defaultdict(int), defaultdict(int)          # 引いた試合
    nn, wn = defaultdict(int), defaultdict(int)        # デッキにあるが引かなかった試合
    kept = defaultdict(int)
    nowin, touts = 0, 0
    half = []                                          # 信頼性用: (card, win, game index)
    for gi, g in enumerate(G):
        touts += g.get("timeouts", 0)
        if g["winner"] is None:
            nowin += 1
            continue
        for deck, cards in g["draws"].items():
            win = int(g["winner"] == deck)
            drawn = {norm(c) for c in cards} - BASICS
            hand = {norm(c) for c in g.get("hand_end", {}).get(deck, [])}
            for c in drawn:
                n[c] += 1
                w[c] += win
                kept[c] += c in hand
                half.append((c, win, gi))
            for c in dk.get(deck, set()) - drawn:
                nn[c] += 1
                wn[c] += win
    df = pd.DataFrame({"n": pd.Series(n, dtype=float), "w": pd.Series(w, dtype=float),
                       "nn": pd.Series(nn, dtype=float), "wn": pd.Series(wn, dtype=float),
                       "kept": pd.Series(kept, dtype=float)}).fillna(0)
    df["gih"] = df.w / df.n
    df["iwd"] = df.gih - df.wn / df.nn.replace(0, np.nan)
    df["keep_rate"] = df.kept / df.n
    meta = {"games": len(G), "no_winner": nowin, "ai_timeouts": touts}
    return df, meta, pd.DataFrame(half, columns=["k", "w", "gi"])


def reliability(half, keys):
    rng = random.Random(1)
    gis = sorted(half.gi.unique())
    rs = []
    for _ in range(20):
        h = set(rng.sample(gis, len(gis) // 2))
        A = half[half.gi.isin(h)].groupby("k").w.mean()
        B = half[~half.gi.isin(h)].groupby("k").w.mean()
        j = A.index.intersection(B.index).intersection(keys)
        r = stats.spearmanr(A[j], B[j])[0]
        rs.append(2 * r / (1 + r))
    return float(np.mean(rs))


def zero_set(code):
    f = "forge_debias/audit_zero.csv"
    if not os.path.exists(f):
        return set()
    z = pd.read_csv(f)
    return set(z[z.set == code].name.map(norm))


def debias_col(d, src, X):
    """§5 の 4〜5: X を除いて中心化し、色の平均、次にタイプの平均を引く。X は 0。"""
    m = ~d.k.isin(X)
    v = pd.Series(0.0, index=d.index)
    v[m] = d.loc[m, src] - d.loc[m, src].mean()
    sub = d.loc[m].assign(v=v[m])
    c = sub.v - sub.groupby("cg").v.transform("mean")
    t = sub.v - sub.groupby("tg").v.transform("mean")
    ct = c - sub.assign(c=c).groupby("tg").c.transform("mean")
    out = {}
    for name, s in (("", v[m]), ("_c", c), ("_t", t), ("_ct", ct)):
        col = pd.Series(0.0, index=d.index)
        col[m] = s
        out[name] = col
    return out


def build(code, actual=None):
    """採点対象の表。actual: 列 name, actual_gih(小数)。過去セットは oof_B10 から。"""
    cs, meta, half = card_stats(code)
    if code == "TRK":
        t = pd.read_csv("forge_debias/trk_cards.csv")
        t["colors"] = t.colors.fillna("")
        P = json.load(__import__("gzip").open("forge_debias/trk_adopted_gih.json.gz"))["cards"]
        P = pd.DataFrame(P)[["name", "gih"]].rename(columns={"gih": "pred_pp"})
        o = t.merge(P, on="name")
        o["pred"] = o.pred_pp / 100
        o = o.rename(columns={"type_line": "type"})
        if actual is not None:
            o = o.merge(actual[["name", "actual_gih"]], on="name")
        else:
            o["actual_gih"] = np.nan
    else:
        O = pd.read_csv("c9_power_questions/oof_B10.csv.gz")
        o = O[O.set == code].copy()
        SC = pd.read_csv("c14_context_power/set_cards.csv.gz")
        SC["colors"] = SC.colors.fillna("")
        o["key"] = code + "|" + o.name
        o = o.merge(SC[["key", "type", "colors"]], on="key", how="left")
    o["k"] = o.name.map(norm)
    o = o[o.type.notna() & ~o.type.astype(str).str.contains("Land")]
    d = o.merge(cs[cs.n >= 150], left_on="k", right_index=True).reset_index(drop=True)
    d["a"] = (d.actual_gih - d.actual_gih.mean()) * 100
    d["p"] = (d.pred - d.pred.mean()) * 100
    d["res"] = d.a - d.p
    d["e_raw"] = d.gih * 100
    d["iwd_raw"] = d.iwd * 100
    d["cg"] = d.colors.map(color_group)
    d["tg"] = d.type.map(type_group)
    d["set"] = code
    X = zero_set(code)
    d["zeroed"] = d.k.isin(X)
    for src, pre in (("e_raw", "e"), ("iwd_raw", "iwd")):
        for suf, col in debias_col(d, src, X).items():
            d[pre + suf] = col
    meta.update({"scored_cards": int(len(d)), "zeroed_cards": int(d.zeroed.sum()),
                 "reliability": reliability(half, set(d.k)), "cards_with_n150": int((cs.n >= 150).sum())})
    return d, meta, cs


def one_sided(r, p2):
    return p2 / 2 if r > 0 else 1 - p2 / 2


def evaluate(d):
    out = {"cards": int(len(d)), "mae_p": float(np.mean(np.abs(d.res)))}
    for pre in ("e", "iwd"):
        for suf in ("", "_c", "_t", "_ct"):
            v = pre + suf
            r, p2 = stats.spearmanr(d[v], d.res)
            out[v] = {"spearman_vs_miss": float(r), "p_one_sided": float(one_sided(r, p2)),
                      "mae_p_plus_0.10": float(np.mean(np.abs(d.res - K * d[v]))),
                      "coef_fit": float((d[v] * d.res).sum() / (d[v] ** 2).sum())}
    cr, sp = d.tg == "creature", d.tg == "instant_sorcery"
    out["creature_minus_spell"] = {"e_raw": float(d[cr].e_raw.mean() - d[sp].e_raw.mean()),
                                   "a": float(d[cr].a.mean() - d[sp].a.mean()),
                                   "n_creature": int(cr.sum()), "n_spell": int(sp.sum())}
    out["keep_rate_by_type"] = {t: float(d[d.tg == t].keep_rate.mean()) for t in ("creature", "instant_sorcery", "other")}
    return out


def verdict(ev):
    a_ok = ev["e_ct"]["spearman_vs_miss"] > 0 and ev["e_ct"]["p_one_sided"] < 0.05
    b_ok = ev["e_ct"]["mae_p_plus_0.10"] < ev["mae_p"]
    return {"a_spearman_pos_and_p_lt_0.05": bool(a_ok), "b_mae_improves": bool(b_ok), "pass": bool(a_ok and b_ok)}


def past(json_out=None):
    frames, res = [], {"per_set": {}, "meta": {}}
    for code in PAST:
        d, meta, _ = build(code)
        frames.append(d)
        res["meta"][code] = meta
        res["per_set"][code] = evaluate(d)
    D = pd.concat(frames, ignore_index=True)
    res["pooled"] = evaluate(D)
    res["verdict"] = verdict(res["pooled"])
    cols = ["set", "name", "type", "colors", "cg", "tg", "n", "a", "p", "res", "zeroed", "keep_rate",
            "e_raw", "e", "e_c", "e_t", "e_ct", "iwd_raw", "iwd", "iwd_ct"]
    D[cols].to_csv("forge_debias/past_cards.csv", index=False)
    res["reference_8sets"] = reference_8sets(D)
    print(json.dumps(res, ensure_ascii=False, indent=1))
    if json_out:
        json.dump(res, open(json_out, "w"), ensure_ascii=False, indent=1)


def reference_8sets(D3):
    """報告のみ: 既存 5 セット(repro.py のデータ、中心化だけ §5 に統一)+ 過去 3 セットでの係数。"""
    try:
        import repro
        rows = []
        for code in repro.SETS:
            o = repro.load(code)
            o["a"] -= o.a.mean()
            o["p"] -= o.p.mean()
            o["res"] = o.a - o.p
            o["e"] -= o.e.mean()
            o = repro.debias(o, "sequential")
            rows.append(o[["set", "res", "e_ct"]])
        A = pd.concat(rows + [D3[["set", "res", "e_ct"]]], ignore_index=True)
        return {"cards": int(len(A)), "coef_e_ct": float((A.e_ct * A.res).sum() / (A.e_ct ** 2).sum()),
                "per_set_coef": {s: float((g.e_ct * g.res).sum() / (g.e_ct ** 2).sum()) for s, g in A.groupby("set")}}
    except Exception as ex:  # noqa: BLE001
        return {"error": str(ex)}


def freeze_trk():
    d, meta, cs = build("TRK")
    cols = ["name", "type", "colors", "n", "zeroed", "keep_rate", "e_raw", "e", "e_c", "e_t", "e_ct",
            "iwd_raw", "iwd", "iwd_ct"]
    d[cols].to_csv("forge_debias/trk_frozen_e.csv", index=False, float_format="%.6f")
    json.dump(meta, open("forge_debias/trk_frozen_meta.json", "w"), indent=1)
    print(json.dumps(meta, indent=1))


def score_trk(actual_csv, json_out=None):
    A = pd.read_csv(actual_csv)
    A = A[A.gih_games >= 500]
    if len(A) < 100:
        sys.exit(f"対象 {len(A)} 枚 < 100: 採点を延期する(PLAN §7)")
    F = pd.read_csv("forge_debias/trk_frozen_e.csv")
    d, meta, _ = build("TRK", actual=A)
    # 凍結した値を使う(build の再計算と一致するかも確かめる)
    m = d.merge(F[["name", "e_ct", "e"]], on="name", suffixes=("", "_frozen"))
    meta["frozen_max_abs_diff"] = float((m.e_ct - m.e_ct_frozen).abs().max())
    ev = evaluate(d)
    res = {"meta": meta, "eval": ev, "verdict": verdict(ev)}
    print(json.dumps(res, ensure_ascii=False, indent=1))
    if json_out:
        json.dump(res, open(json_out, "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "past":
        past(sys.argv[2] if len(sys.argv) > 2 else None)
    elif mode == "freeze-trk":
        freeze_trk()
    elif mode == "score-trk":
        score_trk(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
    elif mode == "dry-run":
        # 監査の試合を本番の場所に見立て、実測を合成して式が動くかだけ確かめる
        GDIR = "forge_debias/audit/{}/games"
        DECKS = "forge_debias/audit/{}"
        d, meta, cs = build("TRK")
        rng = np.random.default_rng(0)
        print(meta, "rows", len(d), "(n>=150 は監査の 210 試合ではほぼ 0 になる)")
