# forge-debias 再開メモ(2026-11-11 14:20 JST、11/14 に追記)

**11/14:本番・TRK の凍結(90e2937)・過去3セットの採点(1回)は済んだ。結果は RESULTS.md(合格、MAE 2.140 → 2.112)。残りは TRK の採点だけ(下の最後の行)。**


- 計画: PLAN.md(事前登録 519375c、対戦前)。手順1の再現は一致(repro.py、c3c968e)。
- 監査(§4)済み: 最初の監査で 30% 超は 197 枚。原因の切り分けは FORGE_DIAG=1 の診断(audit_diag.py、audit/*/diag0)。
  - 修正 1 つ: 出たときの効果を AI が断ると、効果が任意(対象 0 可)・相手だけが対象・選ぶだけ(名前・数・色・タイプ)・自分/つけた先だけの強化でも、カードごと唱えない。これを唱えるようにした(forge_debias_fixes.patch、AiController.etbEffectCannotHurtAi)。
  - 修正後の監査(audit/*/fix1)で 30% 以下になった 23 枚は修正済み(audit/fixed_cards.csv)。残り 174 枚は e = 0(audit_zero.csv、理由つき)。
  - 本番の jar: Card-Forge b1f615da + forge_debias_fixes.patch(sha256 07d07abc…)、jar sha256 c8d308b0…。FORGE_DIAG は本番では使わない。
- 本番: `bash run_all.sh <FORGE_REPO>`(research/forge_debias から)。ECL→TLA→EOE→TRK、2 ジョブずつ、60 分で一時停止、再実行で続きから。2 ジョブごとに commit・push。見込み約 9 時間(監査の速さから: 1 試合あたり ECL・EOE 約 2.0 秒、TLA 2.9 秒、TRK 3.2 秒、2 並行)。
  - Forge の作業ツリーはセッションの一時領域にある。新しい環境で再開するなら、b1f615da を clone して forge_debias_fixes.patch を当て、`mvn -q -B -pl forge-gui-desktop -am -DskipTests -Dcheckstyle.skip package` でビルドする。
- 本番の後: `python3 -I forge_debias/score.py freeze-trk`(research/ から)で TRK を凍結してコミット → `score.py past forge_debias/past_result.json` を 1 回だけ → RESULTS.md。
- TRK の採点は 17Lands の実測(GIH 500 試合以上)がそろってから `score.py score-trk <csv>` を 1 回だけ。
