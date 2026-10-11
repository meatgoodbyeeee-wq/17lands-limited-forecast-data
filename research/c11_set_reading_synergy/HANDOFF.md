# C11 引き継ぎメモ (2026-10-11 JST 停止時点)

## 状態
- 判定 s1, s2 とも完了 (1,067/1,067、check_raw OK。s2 は S06 の空 `I:` を `I: -` に修正、NORMALISED.md 記載)。
- c11.py (features/arm/evaluate)、c11_features.csv、agreement.json はコミット済み。スコア計算前にコミット済みなので事前登録 (PLAN.md の Rule F12) は有効。
- アーム計算 (B12 3シード / shuffled / payonly 各1シード) は未完了。一度バックグラウンドが消え、再起動後に手動停止した。oof_*.csv.gz は未生成。

## 再開手順
cd research/c11_set_reading_synergy
setsid nohup python3 c11.py arm B12 > b12.log 2>&1 < /dev/null &
setsid nohup sh -c 'python3 c11.py arm shuffled; python3 c11.py arm payonly' > ctl.log 2>&1 < /dev/null &
(各 約1〜1.5時間、2CPU。前景は sleep ≤119 秒でポーリング。*.log は未追跡のままなので .git/info/exclude に追加するか gitignore する)

完了後: python3 c11.py evaluate → RESULTS.md (Rule F12 判定、対象/レアリティ/dwc四分位/名指しカード/パス一致) → PR・squash merge。
支持された場合のみ: FRA B12 予測を凍結 (fra_frozen_predictions.csv に pred_B12 追加 + sha)、PENDING_FRA に項目11追加、定期タスク trig_013Wr6YZfz4UvLaimtJeb7de のプロンプト更新。不支持なら FRA 読みは記述のみ。
本番・Pages は変更しない。報告は日本語。
