#!/bin/bash
# K3 chunk: run two jobs of one set (unpatched Forge) in parallel, then commit and push what finished.
# usage: bash k3_chunk.sh <SET> <job_a> <job_b>
set -u
SET="$1"; JA="$2"; JB="$3"
REPO=/tmp/claude-0/-home-claude/2513f87c-6a9f-5def-ac70-473a552d5b71/scratchpad/forge_src/repo
DECKS=/tmp/claude-0/-home-claude/2513f87c-6a9f-5def-ac70-473a552d5b71/scratchpad/k3_decks/$SET
DATA=/home/claude/17lands-limited-forecast-data
HERE=$DATA/research/k3_engine_gih_sets
OUT=$HERE/games_$SET
python3 -I "$HERE/run_k2.py" "$REPO" "$DECKS" "$OUT" 2 "base:$JA" "base:$JB" 2>&1 | sed "s/^/$SET /" | tee -a "$HERE/progress.log"
cd "$DATA" || exit 1
git add research/k3_engine_gih_sets 2>/dev/null
if ! git diff --cached --quiet; then
  git commit -q -m "K3: $SET jobs $JA,$JB game logs

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_013SwJrW4aSxn41re38A9W4f"
  for i in 1 2 3; do git push -q origin research/l1-forge-timing && break; sleep 20; done
fi
echo "$(date +%H:%M:%S) $SET chunk jobs $JA,$JB finished" | tee -a "$HERE/progress.log"
