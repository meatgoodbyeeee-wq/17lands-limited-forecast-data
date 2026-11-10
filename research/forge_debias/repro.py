"""手順1: 診断メモ(claude/sakiyomi-forge-diagnosis-2026-11-10.md)「分かったこと 5」の再現。対戦なし。

usage (research/ から): python3 -I forge_debias/repro.py
データ:
  MSH  k2_engine_gih_patched/games/base/job?.json(K2 の修正なし)
  HOB・SOS・TMT  k3_engine_gih_sets/games_<SET>/base/job?.json
  FRA  k4_fra_forge/games_FRA/base/job?.json + fra_actual_public_20261017.csv(500試合以上)+ 凍結 B10
  p・a(過去セット)  c9_power_questions/oof_B10.csv.gz
  タイプ・色  c14_context_power/set_cards.csv.gz(タイプが引けない 20 枚 = 各セットの基本土地 5 枚を除く)
定義: e = 引いたときの勝率(n ≥ 150)をセット内で中心化して ×100。外れ = a − p。
  e_c = e − 色グループの平均、e_t = e − タイプの平均、e_ct = e_c − タイプごとの e_c の平均(順に引く)。
MAE: 予測 = p + k × 値。k は対象セット以外の 4 セットで、外れを値に回帰した係数(切片なし)。

中心化の基準(メモの数値に一致した組み合わせ。メモはセットごとに既存の集計を流用していた):
  HOB・SOS・TMT  a・p は oof_B10 のセット全カードの平均で中心化(K3 の k3.py / cards_e.csv と同じ)
  MSH           a・p は n ≥ 150 のカードの平均で中心化
  FRA           a・p は採点対象(500試合以上 かつ n ≥ 150)の平均で中心化(K4 の k4.py と同じ)
  e はどのセットも n ≥ 150 かつ実測のあるカードで中心化。基本土地の除外は中心化の後。
本番(PLAN.md)ではこの混在をやめ、全セットで採点対象のカードの平均で中心化する。
"""
import glob
import json
import sys

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, "forge_debias")
from debias_lib import color_group, type_group, debias, norm, engine_gih  # noqa: E402

SETS = ["MSH", "HOB", "SOS", "TMT", "FRA"]
GDIR = {"MSH": "k2_engine_gih_patched/games/base", "HOB": "k3_engine_gih_sets/games_HOB/base",
        "SOS": "k3_engine_gih_sets/games_SOS/base", "TMT": "k3_engine_gih_sets/games_TMT/base",
        "FRA": "k4_fra_forge/games_FRA/base"}
VALS = ["e", "e_c", "e_t", "e_ct"]
MEMO_MAE = {"MSH": [2.291, 2.232, 2.318, 2.189, 2.318], "HOB": [2.491, 2.416, 2.437, 2.400, 2.401],
            "SOS": [2.454, 2.486, 2.448, 2.470, 2.425], "TMT": [2.612, 2.588, 2.608, 2.577, 2.602],
            "FRA": [2.380, 2.419, 2.359, 2.414, 2.342]}
MEMO_RHO = {"MSH": [0.34, -0.01, 0.39, 0.04], "HOB": [0.27, 0.41, 0.30, 0.41], "SOS": [0.03, 0.09, 0.07, 0.15],
            "TMT": [0.11, 0.06, 0.14, 0.08], "FRA": [-0.02, 0.10, 0.04, 0.17]}

O = pd.read_csv("c9_power_questions/oof_B10.csv.gz")
SC = pd.read_csv("c14_context_power/set_cards.csv.gz")
SC["colors"] = SC.colors.fillna("")
FZ = pd.read_csv("c9_power_questions/fra_frozen_predictions.csv")


def load(code):
    if code == "FRA":
        A = pd.read_csv("k4_fra_forge/fra_actual_public_20261017.csv")
        A = A[A.gih_games >= 500]
        o = A.merge(FZ[["id", "name", "pred_B10"]], on="name").rename(columns={"pred_B10": "pred"})
        o["key"] = "FRA|" + o.id
    else:
        o = O[O.set == code].copy()
        o["key"] = code + "|" + o.name
    o["k"] = o.name.map(norm)
    cnt = engine_gih(sorted(glob.glob(GDIR[code] + "/job?.json")))
    o = o.merge(cnt[cnt.n >= 150], left_on="k", right_index=True)
    o = o.merge(SC[["key", "type", "colors"]], on="key", how="left")
    if code in ("HOB", "SOS", "TMT"):
        full = O[O.set == code]
        am, pm = full.actual_gih.mean(), full.pred.mean()
    else:
        am, pm = o.actual_gih.mean(), o.pred.mean()
    o["a"] = (o.actual_gih - am) * 100
    o["p"] = (o.pred - pm) * 100
    o["e"] = (o.gih - o.gih.mean()) * 100
    o = o[o.type.notna()].copy()
    o["res"] = o.a - o.p
    o["cg"] = o.colors.map(color_group)
    o["tg"] = o.type.map(type_group)
    o["set"] = code
    return debias(o, "sequential")


def loso_k(D, v, code):
    tr = D[D.set != code]
    return float((tr[v] * tr.res).sum() / (tr[v] ** 2).sum())


if __name__ == "__main__":
    D = pd.concat([load(c) for c in SETS], ignore_index=True)
    rho = {c: {v: float(stats.spearmanr(D[D.set == c][v], D[D.set == c].res)[0]) for v in VALS} for c in SETS}
    mae = {}
    for c in SETS:
        te = D[D.set == c]
        mae[c] = {"p": float(np.mean(np.abs(te.res)))}
        for v in VALS:
            mae[c][v] = float(np.mean(np.abs(te.res - loso_k(D, v, c) * te[v])))
    cols = ["p"] + VALS
    mean = {v: float(np.mean([mae[c][v] for c in SETS])) for v in cols}
    kall = {v: float((D[v] * D.res).sum() / (D[v] ** 2).sum()) for v in VALS}
    print(f"カード {len(D)} 枚(各セット: {D.groupby('set').size().to_dict()})")
    print("Spearman(値, 外れ): そのまま / 色の中 / タイプの中 / 色とタイプの中   [メモ]")
    for c in SETS:
        print(f"  {c} " + " ".join(f"{rho[c][v]:+.2f}" for v in VALS) + "   [" + " ".join(f"{x:+.2f}" for x in MEMO_RHO[c]) + "]")
    print("MAE(pp): B10のみ / +e / +色の中 / +タイプの中 / +色とタイプの中   [メモ]")
    for c in SETS:
        print(f"  {c} " + " ".join(f"{mae[c][v]:.3f}" for v in cols) + "   [" + " ".join(f"{x:.3f}" for x in MEMO_MAE[c]) + "]")
    print("  平均 " + " ".join(f"{mean[v]:.3f}" for v in cols) + "   [2.446 2.428 2.434 2.410 2.417]")
    print("5セット全体の係数", {k: round(v, 3) for k, v in kall.items()}, "[色とタイプの中 0.096]")
    max_mae = max(abs(round(mae[c][v], 3) - MEMO_MAE[c][i]) for c in SETS for i, v in enumerate(cols))
    max_rho = max(abs(round(rho[c][v], 2) - MEMO_RHO[c][i]) for c in SETS for i, v in enumerate(VALS))
    ok = round(mean["p"], 3) == 2.446 and round(mean["e_ct"], 3) == 2.417
    print(f"セルごとの最大差: MAE {max_mae:.3f}、Spearman {max_rho:.2f}")
    print("平均 2.446 → 2.417(色とタイプの中)と一致:", ok)
    json.dump({"cards": int(len(D)), "spearman_value_vs_miss": rho, "mae": mae, "mae_mean": mean, "coef_all5": kall,
               "max_cell_diff_mae": max_mae, "max_cell_diff_spearman": max_rho, "mean_matches_2446_2417": ok},
              open("forge_debias/repro_result.json", "w"), ensure_ascii=False, indent=1)
    sys.exit(0 if ok else 1)
