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
## Step 3: TRK
全カード公開 (10/31) 後に TRK を G3 で判定 (3パス; build.py の FRA 同様に target を作る) → B11g を TRK に適用 (B10S 同様のスケーリング) → export (research/trk_preview/export_b10.py の VERSION 名変更) → forecast-trk.json → 非公開アーティファクト再構築 (JS を再生成) → freeze。公開 (available:true, 11/3 頃) はユーザー確認後。
## 予備 (案B)
上限に当たった場合: B5 + G3 の一次式 (FRAでは B10 より MAE +0.03pp, 3セット平均 +0.05pp 悪い=改善なし) を暫定版として使用。
## 注意
並列の判定は各自の出力ファイルのみ書く (共有scratch禁止)。stop hook: git push + git update-ref refs/remotes/origin/<branch> $(git rev-parse HEAD)。
