#!/bin/bash
# forge-debias 本番(PLAN.md §8)。2 ジョブずつ回し、終わるたびに commit・push する。止まっても再実行で続きから。
# usage: bash run_all.sh <FORGE_REPO>   (research/forge_debias から)
# MAX_MIN 分(既定 60)を過ぎたら次の組を始めずに「PAUSED」で終わる。もう一度実行すると続きから。
set -u
FORGE=$1
cd "$(dirname "$0")"
unset FORGE_DIAG
export JOB_LIMIT_S=${JOB_LIMIT_S:-3300}
MAX_MIN=${MAX_MIN:-60}
START=$(date +%s)
for SET in ECL TLA EOE TRK; do
  for PAIR in "0 1" "2 3" "4 5" "6 7"; do
    a=${PAIR% *}; b=${PAIR#* }
    if [ -f "games/$SET/job$a.json" ] && [ -f "games/$SET/job$b.json" ]; then continue; fi
    if [ $(( $(date +%s) - START )) -gt $(( MAX_MIN * 60 )) ]; then echo "$(date +%H:%M:%S) PAUSED before $SET $PAIR" | tee -a progress.log; exit 0; fi
    for TRY in 1 2; do
      python3 -I run_debias.py "$FORGE" "decks/$SET" "games/$SET" 2 $PAIR 2>&1 | sed "s/^/$SET try$TRY /" | tee -a progress.log
      if [ -f "games/$SET/job$a.json" ] && [ -f "games/$SET/job$b.json" ]; then break; fi
    done
    git add "games/$SET" progress.log
    git commit -q -m "forge-debias: $SET jobs $PAIR

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_015Njcn5X2QakPJUCz9p6Ew3" || true
    for i in 1 2 3; do git push -q origin research/forge-debias 2>/dev/null && break; sleep 30; done
    echo "$(date +%H:%M:%S) $SET $PAIR committed" | tee -a progress.log
  done
done
echo "ALL DONE" | tee -a progress.log
