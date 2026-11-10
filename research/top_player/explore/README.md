# top player の GIH WR:過去セットの読み込み(2026-11-11、探索的)

事前登録なしの探索的な集計。採否には使わない。FRA と TRK の top 指標は集計していない(検証用に残すため)。

## データ
- `research/case6/data/<SET>_case6_28d.csv`(17Lands 公開データ Premier Draft、発売後28日。Case 6 で集計済み)。
- top player = プレイヤーの勝率帯(`user_game_win_rate_bucket`)が 0.60 以上、かつ試合数帯(`user_n_games_bucket`)が 50 以上。符号は `top60n50`。
- 対象カードは top の試合が 500 以上のもの。23セット 5,780枚。KHM・STX・AFR・MID・VOW は勝率帯の列が無い。
- 予測は `research/g3_retrain/oof_B11g.csv.gz` と `research/c9_power_questions/oof_B10.csv.gz`(research/q-small-gains ブランチ)。

## 主な結果(23セット平均。pp)
| 項目 | 値 |
|---|---|
| top の試合の割合 | 20.4% |
| top の GIH − 全体の GIH(水準の差) | +8.40(セット別 7.37〜8.94) |
| カード間の SD:top / 全体 | 2.95 / 3.40 |
| セット内の順位相関(top と全体) | 0.927(最低は HOB の 0.873) |
| 折半信頼性:top / 全体 | 0.883 / 0.983 |
| top = b × 全体(セット内で中心化)の傾き b | 0.817 |
| 上の式の残差の SD | 0.995 |
| 残差の折半信頼性(top と top 以外を別の半分で測る) | 0.14(top 2,000試合以上のカードでは 0.24) |
| 全体の GIH を完全に当てたときに残る top の MAE | 0.737 |
| B11g × k の top に対する MAE(k は LOSO、約 0.81) | 1.732(k = 1 では 1.756) |
| B11g の順位相関:top に対して / 全体に対して | 0.584 / 0.610 |

16セット(Case 6 の `top_oof.csv.gz` がある範囲、3,849枚)での比較:
| 予測 | top に対する MAE | 順位相関 |
|---|---|---|
| B11g × k | 1.694 | 0.619 |
| T1+C3(本番特徴量+C3 を top で直接学習) | 1.768 | 0.569 |
| B11g と T1+C3 のブレンド(重みは LOSO) | 1.662 | – |
| B11g と T0+C3(全体で学習)のブレンド(対照) | 1.690 | – |

## ファイル
- `analyze.py`:セット別の表、差の信頼性、レアリティ別、現行予測との比較、定義の感度(Sonnet 5.5 のサブエージェントが作成。入出力のパスは作業環境のもの)。
- `verify_descriptive.py`:主な数値の別実装での検算。
- `compare_existing_oof.py`:既存の OOF どうしの比較とブレンド。
- `A_by_set_with_mean.csv`、`B_summary.json`、`B_rarity.csv`、`C_summary.csv`、`D_summary.csv`:集計結果。
