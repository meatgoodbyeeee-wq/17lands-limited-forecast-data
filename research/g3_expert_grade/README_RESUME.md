# Resuming G3 (if a session stops part-way)
Branch: research/g3-expert-grade. All inputs are committed; each finished output is committed as it lands.
1. `git checkout research/g3-expert-grade && cd research/g3_expert_grade && python3 status.py`
   (inputs are deterministic: `python3 build.py` regenerates them if needed; it reads
   /home/claude/pageswt/data/target.json.gz for FRA card text — pages repo, branch with FRA target.)
2. For each missing item launch one Opus subagent:
   - lessons: prompt = prompt_lessons.txt (must exist before any judge pass).
   - "<SET> passK": prompt = prompt_judge.txt with {SET} and {K} replaced.
   Paths in the prompts assume the worktree at /home/claude/wt-g3; adjust if different.
3. Commit each new output; when status.py shows none missing: `python3 score.py` → score.json, RESULTS.md.
