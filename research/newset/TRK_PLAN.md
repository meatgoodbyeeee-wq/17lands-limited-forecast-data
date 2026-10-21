# TRK（スター・トレック）の予測計画（2026-10-21 事前登録）

目的：プレリリース（2026-11-06）までに、サキヨミ™の発売前予測（GIH WR・予測の幅・ALSA・デッキカラー）をTRKで公開する。
日程の根拠：全カードプレビュー完了 10/31、プレリリース 11/6（11/6〜12）、発売 11/13（[WPN公式](https://wpn.wizards.com/ja/news/star-trek-dates-and-details)。アリーナ提供日は未記載）。

## 方針（既定。変える場合はユーザーの明示的な決定）
- **モデルは本番のまま**：`gih-c3-28set-20260929`（28セット、ET 70% + TF-IDF/Ridge 30%、×1.25、シード20260922–24の平均）。FIN・MH3・FRAの実測は学習に使わない。
- **人間の事前評価（プロ・コミュニティの採点）は入力に使わない**。予測値の手動修正もしない。
- 新機構・新キーワードの扱い：学習済みの特徴量とC3ルーブリックだけで読む。ルーブリックの変更・追加はしない（TRK固有の記述は気づいた点をメモに残すだけ）。
- ALSA・デッキカラー・類似カードは現行のまま（`limited-forecast-pages` のFRAと同じ処理）。
- 公開済みカードの先行抽出はしない。全カードが揃った時点で一括で行う。

## 判断待ち（10/28の FRA 確認後、既定は「本番のまま」）
- `PENDING_FRA.md` の項目6・7・10（C4／C5／C9×3）がFRAで本番を上回った場合のみ、TRKに使うか提案する。使う場合は抽出がC4・C5・C9×3回ぶん増える（トークンは約5倍）。採用は別途ユーザーが決める。
- FRAを29番目の学習セットに加えるかどうか：FRAの28日間データ（10/27確定予定）とFIN方式の確認が要るため、既定は加えない。

## 手順（TRKのカード一覧は Actions の Collect set cards が `limited-forecast-pages` の `data/trk/target.json.gz` に作る）
1. `python research/newset/newset.py queue --set TRK --cards <target.json.gz>`：名前・セット・レアリティ・数値を伏せた抽出キュー（約290枚、シード20260929でシャッフル、150枚ずつのバッチ）
2. `newset.py show --set TRK <n>` を読み、`research/newset/TRK/raw/b<nn>.txt` に `RUBRIC.md` どおりの行を書く（C3ルーブリックは `research/gih_llm_extract/RUBRIC.md` のまま）
3. `newset.py check --set TRK`（形式・範囲・全件カバー）→ `newset.py features --set TRK`
4. `export_gih_c3_28set.py adopted --set TRK --fra <target.json.gz> --c3 research/newset/TRK/c3_features.csv.gz --version gih-c3-28set-20260929-trk --out <pages>/data/trk/adopted-gih.json.gz`、続けて `range`（同じ引数に `--adopted` と `--out <pages>/data/trk/gih-range.json`）
5. **予測の凍結**：出力のsha256を `research/newset/TRK/frozen.json` に記録し、プレリリース前にコミット（後日、TRKの28日間データで採点する）
6. Pagesで `node scripts/build-set-forecast.mjs TRK`、画面で確認 → PR → ユーザーの確認 → `lib/set-config.mjs` の `available: true` で公開

## 事前に決めた確認項目（満たさない場合は公開せず、ユーザーに報告）
- 抽出：全件が形式・範囲を通り、欠けがない。
- カード一覧：公開カードの枚数が公式の発表と一致する。同名カードの重複がない。基本土地・トークンが入っていない。
- 予測：全カードが有限値。分布はFRAの発売前予測と同程度（FRA：中央値55.6、SD 2.22、範囲47.6〜62.6）で、SDが1.5〜3.0ppを外れたら原因を調べる。
- 幅：`q` は本番と同じ（1.5905）。全カードに幅がある。
- 本番との整合：同じコードでFRAを再生成し、現行のFRA予測・幅と完全一致する（2026-10-21確認済み：最大差 0.0）。

## 日程
| 日付 | 作業 |
|---|---|
| 10/21〜10/26 | 基盤：セット指定のスクリプト、カード収集、Pagesの複数セット対応（FRAの出力が不変であることを確認）、この計画 |
| 10/27〜10/28 | FRA 28日間データの確定を待ち、`PENDING_FRA.md` を採点（モデル判断） |
| 10/29〜10/30 | 予備。収集の動作確認（カード一覧が取れているか） |
| 全カード公開（10/31 米国時間＝JSTでは11/1にずれる可能性） | カード一覧 → 抽出 → 予測 → 凍結 |
| 11/2 | 確認項目・画面の確認、PR |
| 11/3 | ユーザーの確認後に公開 |
| 11/4〜11/5 | 予備（日本語テキスト・画像の追加はここで間に合えば） |

## 既知の制限
- 日本語のカード名・テキスト・画像はFRAのみ。TRKは英語表示（画像は準備中）。
- 発売後の実測（17Lands）の取り込みはFRA専用で、TRKは発売後に別途対応が必要。
