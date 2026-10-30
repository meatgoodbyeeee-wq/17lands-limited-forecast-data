#!/bin/bash
# usage: bash k4_chunk.sh <job_a> <job_b>
set -u
JA="$1"; JB="$2"
S=/tmp/claude-0/-home-claude/2513f87c-6a9f-5def-ac70-473a552d5b71/scratchpad
DATA=/home/claude/17lands-limited-forecast-data; HERE=$DATA/research/k4_fra_forge
python3 -I "$HERE/run_k2.py" $S/forge_src/repo $S/k4_decks "$HERE/games_FRA" 2 "base:$JA" "base:$JB" 2>&1 | tee -a "$HERE/progress.log"
cd "$DATA" || exit 1
git add research/k4_fra_forge 2>/dev/null
if ! git diff --cached --quiet; then
  git commit -q -m "K4: FRA jobs $JA,$JB game logs

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_013SwJrW4aSxn41re38A9W4f"
  for i in 1 2 3; do git push -q origin research/l1-forge-timing && break; sleep 20; done
fi
echo "$(date +%H:%M:%S) FRA chunk jobs $JA,$JB finished" | tee -a "$HERE/progress.log"
