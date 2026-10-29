# Resuming G3.1
Branch research/g3-expert-grade, folder research/g31_expert_grade. `python3 status.py` lists missing outputs.
- lessons_cu: Opus subagent with prompt_lessons_cu.txt (needed before judging).
- "<SET> passK": Opus subagent with prompt_judge.txt, {SET}/{K} replaced. Paths assume /home/claude/wt-g3.
Commit each output as it lands; when nothing is missing: `python3 score.py`.
