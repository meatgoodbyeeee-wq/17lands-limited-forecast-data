# D1: C9 GRADE の系統的な誤りの診断 — 事前登録 (集計前に確定)

診断のみ。モデルの変更・採用判定ではない。本番 gih-c3-28set-20260929・Pages・main は不変。TRK のデータ・予測は使わない。人間の発売前評価・セットレビューは使わない。AI に新しい判定をさせない(既存の C5/C9/B10 の集計のみ)。

## 使うデータ(すべて main 上の既存ファイル)
- `research/c9_power_questions/oof_B10.csv.gz`: B10(本番+C4+C5+C9、3 seed、LOSO)の OOF 予測。28 セット 7,075 枚。列 set, name, rarity_ord(0=C,1=U,2=R,3=M), actual_gih, pred。
- `research/c9_power_questions/c9_features.csv.gz`: `c9_m_GRADE`(GRADE 平均)、`c9_s_GRADE`(パス間 SD)。GRADE は Limited 総合評価の整数 0–10。独立した 3 パス(別々の判定エージェント、カード名・セット・レアリティ・17Lands 数値は伏せ、順序も別)の平均。SD は 3 パスの母標準差。テキスト無し(auto=1、基本土地等)はニュートラル値 5.0 なので**除外**する(`cards.csv.gz` の auto)。
- `research/c5_atomic_effects/c5_features.csv.gz`: C5 タグ(>0 を「あり」)。AN=アンセム/ロード、DR=ドロー、FH=瞬速、CD=条件/準備が必要、TK=クリーチャートークン生成、FL=飛行 など。
- `research/c9_power_questions/cards.csv.gz`: type_line, btext(名前を `~` に置換した本文), mv, colors。
- キーは `set|name`。

## 定義
1. 単位 = 1 枚。実測・予測ともにセット内相対: `act_rel = actual_gih − そのセットの actual_gih 平均`、`pred_rel = pred − そのセットの pred 平均`(平均は auto を除く全レアリティ)。単位 pp。
2. **B10 残差** = `act_rel − pred_rel`(正 = B10 の過小予測)。
3. **GRADE のずれ**: `act_rel ~ a + b·c9_m_GRADE` の単回帰を、**評価セットを除く 27 セット**で当てはめ(LOSO)、評価セットのカードの `ずれ = act_rel − (a + b·GRADE)`(正 = GRADE が実力より低く見ている)。当てはめは**層ごと**(R/M 層は R/M のみ、C/U 層は C/U のみ)。したがって層全体のずれ平均はほぼ 0。GRADE は 3 パス平均を使い、パス間 SD(`c9_s_GRADE`)を各群のばらつきとして併記する(平均 SD)。線形のみ(非線形・レアリティ補正は事前に採らない)。
4. 層: **主表 = R/M**(rarity_ord 2,3)、**補足 = C/U**(0,1)。同じ表を両層で出す。
5. 上位カード = 各セットの actual_gih 上位 10 枚(E1 と同じ定義、レアリティ問わず 28×10=280 枚)。ずれは各カードの層の当てはめを使う。

## 群(各層で作る。非排他。層内件数 n)
- C5 タグ単独(全 62 タグ、層内 n≥10 のもの)
- C5 タグの 2 つ組: 層内で共起数が多い上位 30 組(「>0」かつ「>0」)
- 仮説群(事前に名指し): AN&FH、AN&DR、AN&FH&DR、AN&CD、TK&FL(飛行トークン生成)、大型トークン(本文の create…`N/M`…token で power≥4)
- カードタイプ(type_line から、非排他): Creature, Instant, Sorcery, Enchantment, Artifact, Planeswalker, Land。トークン生成あり(本文に create…token)
- レアリティ: R/M 層は R と M、C/U 層は C と U
- マナ総量帯(土地を除く): 0–1, 2, 3, 4, 5, 6+
- 色数(colors の文字数): 0, 1, 2, 3+
- キーワード(btext を大文字小文字無視の語境界一致で機械判定。リマインダー文・付与文も拾う): flying, flash, haste, trample, deathtouch, lifelink, vigilance, first strike(double strike含む), menace, reach, ward, hexproof, indestructible, defender
- CD あり / なし

## 各群の出力
n、ずれ平均(95%CI)、B10 残差平均(95%CI)、実測 act_rel 平均、ずれの向きが群平均と同じセットの割合(群が 2 枚以上いるセットのみ、そのセット数 n_sets も)、GRADE 平均と平均パス間 SD。
- CI: **セット単位のブロック・ブートストラップ**(28 セットを復元抽出、2000 回、プール平均、percentile、seed 20261023)。ずれは LOSO 当てはめ後の値を固定したまま再抽出(当てはめの再推定はしない)。p 値 = 2·min(P(boot≤0), P(boot≥0))(+1 補正)。
- 多重比較: 層×指標(ずれ/B10 残差)ごとに、n≥30 の全群で Benjamini–Hochberg q=0.1。n<30 の群は表示するが「参考」扱いで BH の対象外。
- 縮小推定: n≥30 の群について、各群の平均 m_g とブートストラップ SE_g から DerSimonian–Laird で τ²、精度重み付き全体平均 μ を求め、`μ + τ²/(τ²+SE_g²)·(m_g − μ)`。ずれ・B10 残差それぞれ。
- 上位 10 枚の分析: 同じ群・同じ関数だが、検定の基準は「上位 10 枚全体の平均」(選択による回帰効果で全体が正になるため、群の平均 − 全体平均)。群の n 下限は 10、BH は n≥10 の群。件数が小さいので全体として参考。

## 分類(R/M 層、n≥30 の群)
- **A. B10 でも残差が残る**: B10 残差が BH 有意(q≤0.1)。そのうち、ずれが同じ向きで BH 有意なら「GRADE 起因の残り」、そうでなければ「GRADE 以外の残り」。
- **B. GRADE は外れるが B10 が補正済み**: ずれが BH 有意で、B10 残差が BH 有意でない。(補足として |B10 残差| < 0.5·|ずれ| も併記。)
- 今後の改善対象は A、とくに「GRADE 起因の残り」。
- 注意: 群は重なり合う。因果ではなく関連。ずれの当てはめは 1 本の線形でありレアリティ内の非線形は拾わない。GRADE の判定者は歴史的カードを記憶している可能性がある(C9 の既知の注意点)。

## 個別カード
Avengers Assemble!(MSH)と Chronicle of Victory(ECL): GRADE(平均/SD)、ずれ、B10 残差、act_rel、セット内実測順位と B10 順位、所属する群(層内 n≥10 の全群)と各群のずれ・B10 残差。カード名は結果の説明にのみ使う。

## 成果物
`d1.py`(リポジトリ内相対パスで動作)、`RESULTS.md`、小さな集計 CSV(`groups_RM.csv`, `groups_CU.csv`, `groups_top10.csv`, `cards_named.csv`, `fit_summary.csv`)。
