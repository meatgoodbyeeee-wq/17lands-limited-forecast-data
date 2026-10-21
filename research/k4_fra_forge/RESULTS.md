# K4 結果(実行のみ。採点は 2026-10-28 以降)

Forge の実行は完了。FRA の実測(17Lands)は未参照。
- 6,240 試合を完走(勝者なし 0)。8 ジョブ × 780 試合を 4 回の小分けで、2026-10-22 01:05〜03:56 に実行。
- 最初の起動は、止めたはずの古いプロセスが残って記録が混ざったため破棄し、最初からやり直した(コミット履歴に記録)。
- e を出せるカード(n ≥ 150): 230 枚(Forge に出たカード 248 枚のうち)。
- エンジン GIH の信頼性(半分に分けた相関): 0.86(K3 の 0.84〜0.86 と同程度)。

## 採点の手順(10/28、FRA 28日データが揃ってから)
`python3 -I k4.py games_FRA/base ../c9_power_questions/fra_frozen_predictions.csv <FRA実測csv: name,actual_gih,gih_games> result.json`
判定は PLAN.md の Rule K4(MAE と Spearman の両方で p + 0.1e が p より良ければ支持)。
