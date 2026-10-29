# 再開手順 (Plan A: G3 を28セットに付与 → B10 の C9 を G3 に置換して再学習)
決定 (2026-10-28 ユーザー): TRK から G3 を採用 / 既試算の TRK 予測は C9→G3 に差し替え / MTGAZone の TRK レビューは TRK 予測に使わない (X1 は TRK に適用しない)。案A で進行 (案B は予備)。

## 状態確認
git checkout research/g3-expert-grade && cd research/g3_expert_grade && python3 status_all.py   # 不足セット一覧
## Step 1: 不足セットの判定 (1セット = Opus 1 エージェント、約0.2Mトークン)
Agent(model=opus) に prompt_judge_all.txt を読ませ {SET} を指定。出力 all/<SET>/pass1.json。
優先順: 検証に使う非教訓セット (AFR BRO DMU HOB KHM LTR MID MOM MSH NEO ONE SNC STX VOW WOE; ECL/TMT はパイロットから流用済み) → 教訓セット11 (BLB DFT DSK EOE FDN LCI MKM OTJ SOS TDM TLA)。
各セット完了ごとに git add/commit/push。答え (keys_all/) は判定フォルダに置かない・エージェントに読ませない。
## Step 2: 検証 (全セット完了後、または非教訓17セットが揃った時点)
G3特徴表 = all/<SET>/pass1.json × keys_all/<SET>.csv (key, g3)。c9_features.csv.gz の c9_m_GRADE を g3 に置換した B10 ("B11g") を、B10 と同じ28セット LOSO で学習 (research/c9_power_questions/c9.py を参照)。
比較は B10 と、教訓リストに使っていない17セットで判断 (MAE, within-set Spearman, 上位カードの過小予測)。採用基準は事前に PLAN に書いてから実行。
## Step 3: TRK（スクリプト準備済み 2026-10-29。実行開始はユーザーの指示を待つ）
決定 (2026-10-29 ユーザー)：B11g に広がり補正なし / FRA の詳細画面の数値内訳はそのまま（一文の予測理由は TRK のみ）。
全カード公開 (10/31、JSTで11/1にずれる可能性) 後。`P` = limited-forecast-pages のチェックアウト（`data/trk/target.json.gz` が全カード版になっていること）。
1. ラベル (C3〜C5 Sonnet。C9 は不要): `cd research/trk_preview && python3 trk_label.py queue --gallery $P/data/trk/target.json.gz` → 新しい分の c3/c4/c5 を Sonnet で判定 → `python3 trk_label.py check`
2. G3 (Opus・3パス): `cd research/g3_expert_grade && python3 build_trk.py --cards $P/data/trk/target.json.gz` → Opus エージェント3つ（`prompt_judge_trk.txt` の {DIR} と {K}=1,2,3 を置換、互いの出力は見せない）→ `TRK_full/pass{1,2,3}.json`（gitignore、公開リポジトリに push しない）
3. 書き出し: `cd research/trk_preview && python3 export_b11g.py --cards $P/data/trk/target.json.gz --out-dir $P/data/trk --explain export_tmp/trk_b11g_explain.json.gz --check`
   広がり補正: B11g では Rule F22 の S は不支持（`research/g3_retrain/spread_b11g.json`、改善 0.004pp < 0.01pp、b=1.074）。**ユーザー決定 (2026-10-29)：B11g には広がり補正をかけない**（`--spread` は付けない）。
4. 予測理由: `python3 reasons_b11g.py prepare --explain export_tmp/trk_b11g_explain.json.gz --cards $P/data/trk/target.json.gz` → バッチごとに Sonnet エージェント（`prompt_reasons.txt` の {DIR} と {BATCH}）→ `python3 reasons_b11g.py check` → `python3 reasons_b11g.py merge --out $P/data/trk/gih-reasons.json`
5. Pages: `BUILD_UNPUBLISHED=1 node scripts/build-set-forecast.mjs TRK` → 非公開アーティファクトでプレビュー確認 → freeze。公開 (`lib/set-config.mjs` の `available: true`, 11/3 頃) はユーザー確認後。
## 予備 (案B)
上限に当たった場合: B5 + G3 の一次式 (FRAでは B10 より MAE +0.03pp, 3セット平均 +0.05pp 悪い=改善なし) を暫定版として使用。
## 注意
並列の判定は各自の出力ファイルのみ書く (共有scratch禁止)。stop hook: git push + git update-ref refs/remotes/origin/<branch> $(git rev-parse HEAD)。
