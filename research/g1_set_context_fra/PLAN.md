# G1: セット構成(機械的に数えた密度)を使った改善を FRA で先に試す — 事前登録

研究のみ。本番モデル `gih-c3-28set-20260929`・Pages・main は変更しない。PR は作らない。FRA の発売後実測(17Lands の FRA データ)は **この計画書の作成・準備では一切読んでいない**。TRK のデータ・予測は使わない。人間の発売前評価・セットレビューは使わない。

## 1. 目的と比べる案

B10(本番 + C4 + C5 + C9、LOSO 28セット: pooled MAE 2.2311 pp / Spearman 0.6248)の誤りの大半は C9 の GRADE のずれで、D1 が示した代表例は Avengers Assemble!(MSH、実測6位、B10 255位)と Chronicle of Victory(ECL、実測8位、B10 215位)。どちらも GRADE 3 で、「特定のクリーチャー・タイプ(ヒーロー/選んだタイプ)を強化しドローする」カード。判定役はそのタイプがセットに何体いるか知らず「狭いカード」と判定した(PLAY 1、FLEX 0)。

C11〜C14 は、判定役にセット一覧を読ませて自由に読解させた。この計画は、**カード一覧から機械的に数えた数字だけ**を渡す点が違う(判定役は一覧を読まない)。FRA で先に試し、効果が確かめられたら TRK に使うかをユーザーが決める。

| 案 | 内容 | AI | モデルの学習 |
|---|---|---|---|
| 案0(基準) | B10 の凍結済み FRA 予測 `research/c9_power_questions/fra_frozen_predictions.csv` の `pred_B10`(sha256 `b53b2149…58f041dc`、2026-10-09 にコミット済み、本計画で再確認済み) | – | 変更なし |
| **案1(主案)** | 参照ありカードだけ、セット構成の数字を付けて C9 の7問+GRADE を Opus で3回判定し直し、その平均で B10 の C9 17列を置き換える。B10 の学習済みモデルにそのまま入れて FRA を予測 | Opus ×3パス | 変更なし(過去28セットは今の C9 のまま) |
| **案2** | 同じ抽出規則の密度を特徴量として B10 に追加し、28セット LOSO で再学習・評価。FRA を予測して凍結 | 使わない | 13列を追加して再学習 |
| 副案(案1+2、事前登録) | 案1の判定を、案2のモデル(密度13列つき)に入れる。多くしない: これ1つだけ | 案1と共通 | 案2と同じ |

## 2. 抽出規則(スクリプト `sc_extract.py` で生成。判定結果を見る前に固定、コミット 4d11a49)

入力: 29セット(過去28セット + FRA)のカード一覧 `research/c11_set_reading_synergy/set_cards.csv.gz`(カード文、タイプ行、色、レアリティ、freq = 3パックで見る期待枚数。基本土地を除く。過去セットは17Landsにデータのあるカードのみ、FRAは公式一覧の全カード)。実測値は一切含まない。

### 2.1 前処理
- 注釈文(括弧内、入れ子対応)を除く。カード名は「~」。
- 「トークンを生成する」節(`create … token(s)` と、それに続く `with/that has …`)は参照とみなさない。`this <型>`(自己参照)、`as a sorcery`、`instant speed` などの語、`becomes a … creature` も除く。

### 2.2 何を参照とみなすか(5種類)
1. **クリーチャー・タイプ**(`ctype`): 29セットのクリーチャーのタイプ行から作った語彙(約240語、単数・複数・不規則複数)が、大文字始まりでカード文にある。
2. **タイプを選ぶ**(`chosen_type`): 「choose a creature type」「chosen type」。
3. **キーワード能力**(`keyword`): 固定18語(flying, first strike, double strike, deathtouch, defender, flash, haste, hexproof, indestructible, lifelink, menace, reach, trample, vigilance, ward, prowess, changeling, convoke)が `with <kw>` / `that has <kw>` / `<kw> creatures|spells…` / `non<kw>` の形で現れ、かつ「依存の語」(下記)を含む節にある。付与(`gains flying`)は参照ではない。
4. **カードタイプ**(`cardtype`): instant, sorcery, artifact, enchantment, planeswalker, legendary, noncreature spell。依存の語を含む節にある。
5. **非クリーチャーのサブタイプ**(`nc_sub`): Equipment, Aura, Vehicle, Saga, Lesson, Room, Class, Case, Spacecraft, Food, Clue, Treasure, Desert, Cave。依存の語を含む節にある。
- **依存の語**(3〜5に必要): whenever / each time / for each / number of / equal to the number / gets +N / as long as / spells you cast / costs {N} less / you control have|gain|get / if you control|cast / first spell… など。「Sacrifice an artifact or creature」のようなコストとしての言及は含めない。
- **役割**: 節に `target` / `opponent` があり `you control` / `you cast` / `chosen` が無ければ「対象(target)」、そうでなければ「支援(support)」。**案1・案2の主特徴・判定入力に使うのは support のみ**(target のみの参照はモデルの別列に入れるだけで判定には出さない)。

### 2.3 密度の数え方(カードごとに、そのカードのセットで)
- 分母/分子はそのカード自身を除く。土地を除く。
- `n_match / n_den`: セット全体の枚数(クリーチャー参照は「クリーチャー」を分母、それ以外は「土地以外」を分母)。`n_match_cu / n_den_cu`: コモン・アンコモンだけ。Changeling は全タイプに数える。
- **デッキでの期待枚数 `exp_in_deck`**(判定役が使う数字): そのカードが入りうる2色デッキ(単色なら +他の4色の4通り、2色以上ならその色、無色なら全10組)ごとに、「そのデッキで唱えられるカード」の freq 重み付き割合を出し、平均。クリーチャー参照は ×15、それ以外は ×23(40枚デッキ: 土地17、呪文23のうちクリーチャー約15)。
- `chosen_type` はタイプとデッキ2色の組み合わせのうち割合が最大のもの(最良の場合 = best case)。
- `n_mk`: 参照先のトークンを作る他のカード数(クリーチャー・タイプ、artifact、enchantment、planeswalker。注釈文も含めて検出)。判定入力では 3 枚以上のときだけ「他に n 枚が作る」と書く。

### 2.4 判定入力に載せる情報(案1)
support の参照ごとに 1 行 `SET INFO: …`(1カード最大3行、文面は `g1_inputs.py` の `render`)。例(実際の生成物):

```
#3454 | MV 5 W | Enchantment
Flash
Heroes you control get +2/+2.
At the beginning of each end step, if you attacked with a Hero this turn or a Hero entered the battlefield under your control this turn, draw a card.
SET INFO: "Hero" creatures: 91 of 170 creature cards in the set (54%), 62 of 119 at common/uncommon. A typical deck that can play this card has about 7.7 of its 15 creatures of this type.

#1531 | MV 6 C | Legendary Artifact
As ~ enters, choose a creature type.
Creatures you control of the chosen type get +2/+2 and have first strike and trample.
Whenever you cast a spell of the chosen type, draw a card.
SET INFO: the creature type is chosen when the card is played: the best type for this card's colours has 45 of 168 creature cards in the set (27%), 33 of 113 at common/uncommon; in its best two-colour pair a deck built around that type has about 7.6 of its 15 creatures of one type (best case; an ordinary deck has fewer).
```
(この2枚は過去セットの例。判定には FRA のカードだけを使う。)
- 渡さないもの: カード名、セット名、レアリティ、17Landsの数字、他カードの文。

### 2.5 抽出結果の集計(実測は見ていない)
- 過去28セット: 土地以外 6,537 枚のうち support 参照あり 1,171 枚(17.9%)、ユニークなカード文 1,164。内訳(カード数): cardtype 450、ctype 610、nc_sub 125、chosen_type 30、keyword 30。うちタイプ参照(ctype + chosen_type)は 637 枚(ユニークな文 633)。target のみの参照は 51 枚(判定に出さない)。
- FRA: 土地以外 269 枚のうち support 参照あり **44 枚**(16.4%)。内訳: cardtype 36(うち planeswalker 22)、ctype 7、chosen_type 1、nc_sub 1。target のみ 2 枚。
- **注意**: FRA はクリーチャー・タイプを強化するカードがほとんど無い(8枚)。Avengers Assemble! や Chronicle of Victory のようなカードの検証としては弱い。FRA は「害が出ないか」「カードタイプ・キーワード参照に効くか」の確認が中心になる。

## 3. 参照がないカードの扱い(決定: 今の C9 判定のまま、再判定しない)
理由:
1. C14(セットを見せて全7,210枚を判定し直し)は、外れの大きいカードは改善したが、残りの大多数で悪化し、MAE が +0.03 pp。判定指示を変えると全カードの GRADE が動く。
2. 参照のないカードに足せる情報がない(渡す数字がない)。
3. モデルは過去28セットの「今の C9」で学習している。非参照カード(FRA の 85%)は学習時と同じ判定のままの方が分布が合う。
4. 案0との比較が対応のある比較になる(変わるのは参照あり 44 枚だけ)。AI の量も約1/100。

代償: 参照ありカードの新判定と、非参照カードの旧判定で尺度がずれる可能性。そこで **アンカー**として非参照の FRA カード 30 枚(乱数 seed 20261023)を、SET INFO なしで同じバッチに混ぜて新ルーブリックで判定する。アンカーの新旧差(平均 ΔGRADE、Spearman)で「新ルーブリックの文面だけによるずれ」を測り、報告する。アンカーの判定は予測には使わない。

## 4. 判定の手順(案1)
- 判定対象: FRA の support 参照ありカード 44 枚 + アンカー 30 枚 = 74 枚。入力 `input/p1.txt, p2.txt, p3.txt`(`g1_inputs.py inputs` で生成。カードごとの SET INFO 行つき)。
- **Opus 3パス**、独立(各パスは別のエージェント、他のパスを見ない)。カードの順序はパスごとに変える: p1 = id 昇順、p2 = 逆順、p3 = 乱数順(seed 20261026)。
- カード名は「~」、セット名・レアリティ・17Landsの数字は渡さない(`g1_inputs.py leakcheck` が入力に FRA のカード名・「FRA」・レアリティ語・17Lands語が無いことを確認、現状 0 件)。「過去の知識を使わない」条件(RUBRIC.md の「Do not use what you may remember…」)は維持。
- 出力形式は C9 と同じ(1行 `<id> <IMP> <UNA> <VAL> <FLOOR> <FLEX> <PLAY> <GRADE>`、`raw/p1.txt` など)。検証 `g1_inputs.py check` は C9 の `check_raw.py` と同じ検査(形式、範囲、全カードの回答があること、重複・余分がないこと)。
- 特徴量: 3パスの平均・母標準偏差・3つの和(IMP+UNA、VAL+FLOOR、GRADE−1.25·PLAY)を C9 と同じ式で作り、参照ありカードの C9 17列(MEAN, SD, SUM)を置き換える。
- **判定役への指示(新ルーブリック)**: 全文は下記。既存 `c9_power_questions/RUBRIC.md` との差分は ①冒頭の「Use only …」に「and the SET INFO lines if the card has them」を追加 ②「SET INFO」節の新設(7問の質問・出力形式・規則は変更なし)。

```
# Rubric (C9: how strong is the card — power broken into questions)

You judge Magic: The Gathering cards for two-player Limited (draft, 40-card decks, 17 lands, opponents with typical draft decks). For each card answer seven questions about HOW STRONG it is, not what it does. Use only the shown text, mana value, colours, type and P/T, and the SET INFO lines if the card has them. "~" is the card itself. Do not use what you may remember about the card or its set; judge the text as if you saw it for the first time.

Think like a strong drafter evaluating a card for the main deck of a deck in its colours.

## SET INFO (new in this rubric)
Some cards are followed by lines that start with `SET INFO`. A script counted them from the complete card list of the set the card comes from (the set is not named, and you do not know it). They say how common the things are that the card's text refers to (a creature type, a keyword, a card type such as instant or artifact). You cannot know this otherwise. The counts are facts about the set, not an opinion about the card. Cards without SET INFO lines are judged exactly as before.
How to use them:
- Use SET INFO only to decide how often the card's condition is met in a deck that plays the card. The number to reason about is "about E of the 15 creatures" or "of the 23 spells" of an ordinary two-colour deck that can play the card. The "typical deck" numbers are weighted by how often each card is seen in packs (rares and mythics count less than commons and uncommons), which is why they can differ from the plain card counts; use the typical-deck number. A line marked "best case" describes a deck built around the theme; an ordinary deck has fewer.
- As a guide: if a typical deck has about 5 or more of 15 creatures (or 7 or more of 23 spells) that the card refers to, the condition is usually met and you should judge the card as the text reads when it works. About 2 to 4 creatures (3 to 6 spells): it works part of the time, so judge it between its working and not-working strength. Under 2 creatures (under 3 spells): it is mostly inactive and its value comes from the rest of its text. Count the card's other uses too: a card that is fine without the condition stays fine.
- SET INFO can lower a grade as well as raise it. Do not raise a grade because SET INFO exists. Raise it only if the information shows that the condition the text depends on is common, and lower it (or keep it low) if the condition is rare.
- Sequencing still counts (for example a permanent that must be on the battlefield before you cast the spells it rewards), and so does the cost of building around the card. When the information does not change what you think of the card, keep your usual answer.
- "also make such tokens" (printed only when at least 3 other cards do) counts other cards that create a token of the same kind. They help only if the card in front of you can use those tokens.

Output exactly one line per card, in input order:
`<id> <IMP> <UNA> <VAL> <FLOOR> <FLEX> <PLAY> <GRADE>`
Example: `417 3 2 2 2 1 3 6`
Ids are the numbers after `#`. Every card must get a line. No other text in the file.

## The questions
- IMP (0–4) Immediate impact: cast on curve (on the turn its mana value allows), how much does it change the board or the game right away? 0 nothing · 1 small · 2 a fair play for its cost · 3 strong swing · 4 dominates the board on arrival.
- UNA (0–4) Unanswered: if the opponent cannot deal with it (or, for an instant/sorcery, after it resolves), how much has it changed the game two turns later? 0 nothing more · 1 small extra · 2 steady advantage · 3 large advantage · 4 usually wins the game by itself.
- VAL (0–4) Card value: how many cards' worth does it give on average? 0 less than one card (weak or situational) · 1 about one card · 2 about one and a half · 3 about two cards · 4 three or more.
- FLOOR (0–4) Worst realistic case: how useful is it when the situation is bad for it (behind on board, wrong timing, opponent's best answer)? 0 dead card · 1 rarely useful · 2 usually something · 3 almost always useful · 4 always good.
- FLEX (0–3) Flexibility: does it work early and late, on offence and defence, in many board states? 0 narrow · 1 some · 2 broad · 3 very broad (modal, scalable, or good in any position).
- PLAY (0–4) Playability: how often would a good drafter in its colours put it in the main deck? 0 never · 1 only in special decks · 2 filler · 3 usually · 4 always, first picks.
- GRADE (0–10) Overall Limited grade: 0 unplayable · 2 sideboard · 4 filler · 5 average playable · 6 good playable · 7 strong · 8 very strong · 9 bomb · 10 game-winning bomb.

Rules: answer every question for every card (lands and odd cards included: judge what they contribute to a Limited deck). Use the whole scale; most commons are 3–6 in GRADE. When unsure, take the middle value. Do not add explanations.
```

## 5. 案2: 密度の特徴量と LOSO 評価(AI トークンなし)
- 特徴量(カードごと、support 参照のみ。参照が無ければ 0): `sc_n_sup`(参照の数)、`sc_sup_share_max` / `sc_sup_share_min`(デッキ内の割合の最大・最小)、`sc_sup_E_max` / `sc_sup_E_min`(期待枚数)、種類別の割合 `sc_tribe_share` `sc_chosen_share` `sc_kw_share` `sc_ctyp_share` `sc_ncsub_share`、`sc_sup_mk_n`(トークンを作る他カード数)、target 参照用に `sc_n_tgt` `sc_tgt_share_max`。計13列。探索・選別はしない(上の13列を固定)。
- 学習・評価: B10 の列(B5 + C9 の MEAN, SD, SUM)に13列を追加(`B10SC`)。本番と同じ評価: 28セット leave-one-set-out、本番モデル(ExtraTrees 70% + TF-IDF/Ridge 30%、×1.25)、seed 20260922–24 の3本平均。基準は B10 の既存 OOF(`c9_power_questions/oof_B10.csv.gz`)。環境差の確認のため B10 の再実行(`B10re`)も同じ環境で行い、既存 OOF との差を報告する。
- **シャッフル対照**(1 seed、seed 20261023): 各セット内で13列をカード間で入れ替える。
- **採用条件(Rule G1-LOSO)** — 全部満たしたら「支持」:
  1. pooled MAE が B10 より 0.01 pp 以上改善
  2. セット内 Spearman の平均が B10 以上(悪化なし)
  3. MAE が B10 より低いセットが 15/28 以上(過半数)
  4. E1(Rule F18)の上位カード指標が悪化しない: 各セット実測上位10枚の T_mae が B10 以下、Hit@20(予測上位20位以内に入る上位10枚の割合)が B10 以上、|T_bias| が B10 以下、F_bias(予測上位10枚の過大評価)の悪化が 0.5 pp 以内
  5. シャッフル対照の MAE 改善が実際の改善の半分未満(C11・C12・C13 と同じ形)
- 結果は `LOSO_RESULTS.md` と `result.json`。支持でも不支持でも、案2の FRA 予測は凍結する(FRA は別の独立した1セット評価)。

## 6. FRA の採点(1回だけ。10/28 の確定データ)
- 実測: FRA 28日 Public Game Data(Premier Draft、game_time 2026-09-29 〜 2026-10-26)、GIH 500試合以上のカード。`g1_score.py --actual …` を**一度だけ**実行(これまで実測は読んでいない。スクリプトは合成データで動作確認だけする)。再学習・調整はしない。
- 比較: 案1・案2・副案を、案0(凍結済み B10)と**同じカード集合**で対応比較する。
- **合否基準**(案ごと、全部満たしたら FRA で「効果あり」):
  1. FRA 全体 MAE が案0より悪化しない(Δ ≤ 0)
  2. 実測上位20枚の過小予測 mean(実測 − 予測) が案0より縮む、かつ上位10枚の過小予測が拡大しない
  3. FRA 内 Spearman が案0より悪化しない(Δ ≥ 0)
- 参照ありカード(案1: 44枚)だけの MAE の差、各指標の差の 95% ブートストラップ区間(カード単位の復元抽出、10,000回、seed 20261028)を必ず併記する(290枚なので区間は広い。合否は点推定で決め、区間は「偶然かもしれない」程度の判断材料として示す)。
- **案1の追加報告**: 再判定で GRADE が動いたカード一覧(旧3パス平均 → 新3パス平均、7問すべて、`grade_moves.csv`)、予測の変化、動いたカードのうち実測に近づいた枚数(符号検定)。動きと密度(期待枚数)の Spearman: 密度が高いカードほど上がり、低いカードは下がるか(一律に上がるなら C14 と同じ偏りの兆候)。アンカー30枚の新旧差(ルーブリック文面だけによるずれ)。
- 案2の追加報告: LOSO で効いた列の傾向、FRA で特徴量が非ゼロの枚数。

## 7. 予測の凍結
- 案2: LOSO 後、PLAN.md 等と一緒に `fra_frozen_arm2.csv`(`pred_arm2`、基準の `pred_B10_frozen` と B10 の再計算 `pred_B10_rerun` を並記)と `fra_frozen_arm2.json`(sha256)をコミット。
- 案1・副案: Opus 判定(`raw/p1..p3.txt`、検証済み)をコミットしたうえで `python3 g1.py freeze arm1 …` / `freeze arm12 …` で `fra_frozen_arm1.csv` / `fra_frozen_arm12.csv` とハッシュを作り、**採点前に**コミット・push。`g1_score.py` はハッシュが一致しないと動かない。
- 凍結コミットより後に、モデル・規則・ルーブリック・判定を変更しない。

## 8. 日程
- 10/23〜25 準備: 抽出規則、判定入力、新ルーブリック、案2の LOSO(完了予定)、案2の FRA 凍結、採点スクリプト
- 10/25〜27 案1: Opus 3パスの判定(ユーザー承認後)、検証、凍結、コミット
- 10/28 FRA の確定データで採点(1回)、結果をユーザーに報告
- 10/28〜30 ユーザーが TRK への採用を判断
- 11/1(TRK の全カード公開後) 採用なら TRK の全カードに適用。**TRK は全カードがそろわないとセット構成(密度)を数えられない**ので、全カード公開前は適用できない。11/1 に抽出規則を TRK の全カードに実行 → 参照ありカード(FRA 並みなら約15%、約45枚)を Opus 3パスで判定 → 予測を更新(プレリリース 11/6 の前)。

## 9. Opus の判定量(案1)
- 判定カード: 参照あり 44 + アンカー 30 = 74 枚 × 3パス = 222 カード判定。入力は1パス約 30 KB(約 9,000 トークン)+ルーブリック約 1,500 トークン、出力 74 行。3パス合計は C9(7,300枚 × 3 = 約 21,900 カード判定)の約 1%。
- 参考(要承認、計画外): 過去28セットの参照ありカード(1,164 枚、うちタイプ参照 633 枚)も同様に再判定すれば案1を LOSO でも評価できる(633 枚 × 3 = 1,899 カード判定、C9 の約 9%)。FRA はタイプ参照が8枚しかなく、AA・Chronicle 型の検証が弱いため。

## 10. C11〜C14 の問題と、この計画への反映
| 過去の案 | 結果 | 問題 | この計画での対応 |
|---|---|---|---|
| C11(セット一覧を読ませ PAY・enabler を8列追加) | 改善 0.0015 pp、不支持 | 約4%のカードにだけ入る列は ET に無視される。AA の誤差は 11.8→11.5 pp | 追加列だけに頼らず、モデルが実際に使う C9 17列(GRADE 等)自体を参照ありカードで置き換える(案1) |
| C12(K/ON/OFF + 成立確率 = 期待値) | 不支持。AA の λ が保守的(P=0.21) | 成立確率の定義 | 確率の仮定をやめ、期待枚数(デッキに何枚入るか)をそのまま渡す |
| C13(B10 を明示的に上書き) | 不支持。シャッフル対照と区別できず | AA の P=0.78 に直しても予測 52.7→53.5%。Rite・Smile も同方向に動く | 判定役が1枚ずつ数字を見て判断する。動きと密度の相関で一律の底上げを検出する |
| C14(セットを見せ全カードを判定し直し) | MAE +0.03 pp 悪化、AA は 260→42位だが Rite・Smile も上がる | テーマ依存カードを一律に高く見積もる。全カードの判定が動く | 全カードを再判定しない(3章)。数字は参照のあるカードだけ、判定役はセット一覧を読まない。ルーブリックで「上げるための情報ではない、下げる場合もある」と明記し、期待枚数の目安を数値で示す |
| 共通 | E1: 上位10枚は全案で約 −4.6 pp 過小予測のまま | 全体 MAE では効果が見えない | 参照ありカードの MAE と E1 指標を評価に入れる |

## 11. 限界(事前に明記)
- FRA の参照ありカードは 44 枚、タイプ参照は 8 枚。1セットの点推定で、ブートストラップ区間は広い。「効果あり」は TRK への採用の根拠としては弱く、「悪化しない」ことの確認が主になる。
- 判定役(Opus)が過去のカードを知っている可能性(C9 と同じ注意)。FRA は判定役の知識より後のセットなので、FRA は汚染のない検証。
- 抽出規則は機械的で、誤検出がある(例: 注釈外の言及、`creature or planeswalker` の planeswalker など)。誤検出も事前に固定した規則どおりに扱う。
- 過去セットの一覧は17Landsにデータのあるカードのみ(MOM・VOW・MID・WOE・HOB・TMT は 180〜215 枚と少ない)。FRA は全カード。割合の推定に小さな系統差がありうる。
- 採用はユーザーの判断。
