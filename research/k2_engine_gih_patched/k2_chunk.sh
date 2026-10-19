#!/bin/bash
# K2 chunk: run base and patch for one job in parallel, then commit and push whatever finished.
# usage: bash k2_chunk.sh <job>
set -u
J="$1"
REPO=/tmp/claude-0/-home-claude/2513f87c-6a9f-5def-ac70-473a552d5b71/scratchpad/forge_src/repo
DECKS=/tmp/claude-0/-home-claude/2513f87c-6a9f-5def-ac70-473a552d5b71/scratchpad/k2_decks
DATA=/home/claude/17lands-limited-forecast-data
HERE=$DATA/research/k2_engine_gih_patched
OUT=$HERE/games
python3 -I "$HERE/run_k2.py" "$REPO" "$DECKS" "$OUT" 2 "base:$J" "patch:$J" 2>&1 | tee -a "$HERE/progress.log"
cd "$DATA" || exit 1
git add research/k2_engine_gih_patched/games research/k2_engine_gih_patched/progress.log 2>/dev/null
if ! git diff --cached --quiet; then
  git commit -q -m "K2: job $J game logs (base and patch)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_013SwJrW4aSxn41re38A9W4f"
  for i in 1 2 3; do git push -q origin research/l1-forge-timing && break; sleep 20; done
fi
echo "$(date +%H:%M:%S) chunk job$J finished" | tee -a "$HERE/progress.log"
