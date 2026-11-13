"""Markdown tables (Japanese labels) for the write-up. Usage: python3 make_tables.py <results dir>"""
import sys
import numpy as np, pandas as pd
R = pd.read_csv(sys.argv[1] + "/effects_all.csv"); A = pd.read_csv(sys.argv[1] + "/effects_iwd_gns.csv")[["feature", "iwd_q", "gns_q"]]
R = R.merge(A, on="feature", how="left").set_index("feature")
JA = {"KD": "確定除去(破壊・追放)", "KX": "条件つきの除去", "DM": "クリーチャーへのダメージ", "DA": "任意の対象・本体へのダメージ", "MS": "−X/−X の修整", "BN": "バウンス", "TP": "タップ・麻痺", "FT": "格闘・噛みつき",
      "ED": "布告(相手が生け贄を選ぶ)", "CS": "打ち消し", "PA": "攻撃・ブロックを封じるオーラ", "SW": "全体除去", "DR": "ドロー", "SC": "占術・諜報・ルーターなどの選別", "RC": "墓地からの回収", "TU": "ライブラリーのサーチ",
      "IM": "衝動的ドロー(追放して唱える)", "TK": "クリーチャー・トークンの生成", "CL": "手がかり・宝物・食物などのトークン", "PC": "+1/+1 カウンター", "PT": "一時的な強化", "PP": "恒久的な強化", "AN": "全体強化・ロード",
      "CP": "コピー", "EQ": "装備品・オーラ・機体による修整", "FL": "飛行", "MN": "威迫・トランプルなどの弱い回避能力", "FS": "先制攻撃・二段攻撃", "DT": "接死", "LL": "絆魂", "HS": "速攻", "VG": "警戒", "RH": "到達",
      "IN": "破壊不能・呪禁・護法・プロテクション", "FH": "瞬速", "DS": "手札破壊", "ST": "コントロール奪取", "MI": "切削", "DL": "ドレイン・ライフを失わせる", "TX": "相手への課税・制限",
      "RM": "繰り返し使えるマナ加速(マナ能力)", "FX": "色マナの補助・土地サーチ", "CR": "コスト軽減", "SK": "終盤のマナの使い道(X、起動型能力)", "CY": "サイクリング・魂力", "ET": "戦場に出たときの効果", "AT": "攻撃時の誘発",
      "DY": "死亡時・離れたときの誘発", "UP": "毎ターンの誘発", "SP": "呪文を唱えるたびの誘発", "LD": "上陸", "SA": "生け贄(手段・見返り)", "CH": "モード選択・分割・出来事", "KC": "キッカーなどの追加コスト",
      "RE": "フラッシュバック・脱出など墓地からの再利用", "SE": "相手にも働く対称な効果", "DW": "欠点(タップイン、生け贄など)", "CD": "条件・準備が必要", "RN": "ランダム", "SD": "ライフを払う・自分にダメージ"}
def f2(x): return "–" if pd.isna(x) else f"{x:+.2f}".replace("-", "−")
def q(x): return "–" if pd.isna(x) else ("<0.001" if x < .001 else f"{x:.3f}")
def row(lab, r, lvl2=None):
    s = f"| {lab} | {int(r.n)} | {f2(r.raw)} | {f2(r.ctrl)} ± {r.ctrl_se:.2f} | {q(r.q)} | " + ("–" if pd.isna(r.sets) else f"{int(r.sets_same_sign)}/{int(r.sets)}") + f" | {f2(r.iwd)} | {f2(r.gns)} | {f2(r.vsN)} |"
    if lvl2 is not None: s += " " + lvl2 + " |"
    return s
HEAD = "| 効果・能力 | 枚数 | そろえる前 | そろえた後 ± 標準誤差 | q | 同じ向きのセット | 引いたとき(IWD) | デッキ単位(GNS) | 対 普通の人 |"
def table(title, items, lvl=False):
    print(f"\n#### {title}\n"); print(HEAD + (" 主な効果のとき(枚数) |" if lvl else "")); print("|" + "---|" * (9 + (1 if lvl else 0)))
    rows = []
    for lab, key in items:
        if key not in R.index: continue
        l2 = None
        if lvl:
            k2 = key + "=2 (main)"; l2 = f"{f2(R.loc[k2].ctrl)}({int(R.loc[k2].n)})" if k2 in R.index else "–"
        rows.append((R.loc[key].ctrl, row(lab, R.loc[key], l2)))
    for _, s in sorted(rows, key=lambda t: -t[0]): print(s)
G = {"除去と干渉": ["KD", "KX", "DM", "DA", "MS", "BN", "TP", "FT", "ED", "CS", "PA", "SW"], "カードの流れ": ["DR", "SC", "RC", "TU", "IM", "TK", "CL"], "強化": ["PC", "PT", "PP", "AN", "CP", "EQ"],
     "戦闘のキーワード能力": ["FL", "MN", "FS", "DT", "LL", "HS", "VG", "RH", "IN", "FH"], "相手への効果": ["DS", "ST", "MI", "DL", "TX"], "マナ": ["RM", "FX", "CR", "SK", "CY"],
     "誘発と形": ["ET", "AT", "DY", "UP", "SP", "LD", "SA", "CH", "KC", "RE"], "リスクと条件": ["SE", "DW", "CD", "RN", "SD"]}
for t, tags in G.items(): table(t + "(C5 タグ)", [(f"{JA[k]}({k})", "c5_" + k) for k in tags], lvl=True)
table("カードの役割(C4)", [("マナ加速・色補助・土地(N)", "c4_role_N"), ("継続的に得をするカード(V)", "c4_role_V"), ("守り・ブロッカー(D)", "c4_role_D"), ("フィニッシャー(F)", "c4_role_F"), ("除去・干渉(R)", "c4_role_R"),
       ("シナジーの部品(S)", "c4_role_S"), ("攻める体(A)", "c4_role_A"), ("コンバット・トリック・保護(T)", "c4_role_T"), ("その他(O)", "c4_role_O")])
table("色・タイプ・レアリティ", [("青", "col_U"), ("白", "col_W"), ("黒", "col_B"), ("赤", "col_R"), ("緑", "col_G"), ("多色", "col_multi"), ("無色", "col_none"), ("クリーチャー", "is_creature"), ("インスタント", "is_instant"),
       ("ソーサリー", "is_sorcery"), ("アーティファクト(クリーチャー以外)", "is_artifact"), ("エンチャント(クリーチャー以外)", "is_enchantment"), ("オーラ", "is_aura"), ("装備品", "is_equipment"), ("機体", "is_vehicle"),
       ("英雄譚", "is_saga"), ("伝説", "is_legendary"), ("コモン", "rarity_common"), ("アンコモン", "rarity_uncommon"), ("レア", "rarity_rare"), ("神話レア", "rarity_mythic")])
table("クリーチャーのサイズとコスト", [("クリーチャー、マナ総量 2 以下", "creature mv<=2"), ("クリーチャー、マナ総量 3〜4", "creature mv 3-4"), ("クリーチャー、マナ総量 5 以上", "creature mv>=5"), ("クリーチャー、パワー 4 以上", "creature power>=4"),
       ("クリーチャー、タフネス 4 以上でパワー 2 以下", "creature tough>=4 & power<=2"), ("クリーチャー、パワーがタフネスより大きい", "creature power>tough"), ("クリーチャー以外、マナ総量 2 以下", "noncreature mv<=2"), ("クリーチャー以外、マナ総量 5 以上", "noncreature mv>=5")])
table("本文の文字列一致(主なもの)", [("マナ能力({T}: マナを加える)", "x_mana_ability"), ("ルーター(引いて捨てる)", "x_loot"), ("自分の手札を捨てる", "x_discard_self"), ("土地サーチ・好きな色のマナ・土地サイクリング", "x_landcycle_fix"),
       ("宝物", "x_treasure"), ("サイクリング", "x_cycling"), ("絆魂", "x_lifelink"), ("タップ能力({T}:)", "x_tap_ability"), ("起動型能力", "x_activated"), ("「してもよい」(任意の効果)", "x_you_may"), ("カードを引く", "x_draw"), ("2枚以上引く", "x_draw2"),
       ("墓地に触れる", "x_graveyard"), ("インスタント・ソーサリーを参照", "x_instant_sorcery_matters"), ("瞬速", "x_flash"), ("飛行", "x_flying"), ("威迫", "x_menace"), ("トランプル", "x_trample"), ("速攻", "x_haste"), ("護法", "x_ward"),
       ("呪禁・破壊不能・プロテクション", "x_hexproof_ind"), ("打ち消し", "x_counter_spell"), ("対象を取る", "x_target"), ("トークン生成", "x_token"), ("+1/+1 カウンター", "x_counters_p1"), ("一時的な +X/+X", "x_pump_until_eot"),
       ("手がかり・調査(3セットだけ)", "x_clue")])
print("\n#### 段階のある項目(1 標準偏差あたり)\n"); print(HEAD); print("|" + "---|" * 9)
for lab, key in (("マナの補助(C4 MANA)", "c4_MANA"), ("タグの数(C5)", "c5_ntags"), ("本文の語数", "x_words"), ("独立した効果の数(C4 STACK)", "c4_STACK"), ("守りの価値(C5 BLK)", "c5_BLK"), ("何もしない頻度(C4 DEAD)", "c4_DEAD"),
                 ("除去の速度(C4 SPD)", "c4_SPD"), ("除去の大きさ(C4 DMG)", "c4_DMG"), ("除去の対象の広さ(C4 TGT)", "c4_TGT"), ("ライフの増減(C4 DRAIN)", "c4_DRAIN"), ("他のカードを助ける度合い(C4 SYNO)", "c4_SYNO"),
                 ("マナ総量に対する効率(C5 RATE)", "c5_RATE"), ("対象の数", "x_ntarget"), ("試合が長いほど伸びる(C4 SCALE)", "c4_SCALE"), ("テンポ(C4 TEMPO)", "c4_TEMPO"), ("効き始めの遅さ(C4 TURN)", "c4_TURN"),
                 ("回避能力(C4 EVA)", "c4_EVA"), ("対処されたときの損(C4 VULN)", "c4_VULN"), ("出たときの戦力(C4 SWG)", "c4_SWG"), ("ライフへの圧力(C5 CLK)", "c5_CLK")):
    print(row(lab, R.loc[key + " (per SD)"]))
