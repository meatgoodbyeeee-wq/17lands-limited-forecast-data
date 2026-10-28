# Plan A: resume guide (user decision 2026-10-28: adopt G3 for TRK, replace C9 with G3; do NOT use MTGAZone TRK reviews for TRK)
Worktree /home/claude/wt-g3, branch research/g3-expert-grade (if missing: clone data repo, checkout the branch; pageswt only needed for FRA text).

## Step 1 — G3 on the 28 training sets (1 pass each)
1. `cd research/g3_expert_grade && python3 status_all.py` → list of missing sets (inputs all/<SET>/, keys keys_all/<SET>.csv; ECL/TMT copied from pilot).
2. For each missing set launch one Opus subagent: prompt =
   "Read /home/claude/wt-g3/research/g3_expert_grade/prompt_judge_all.txt and follow it exactly with {SET}=<SET>. Only touch all/<SET>/pass1.json. Do not read any other file under research/ (especially keys_all/). Use no shared scratch files."
   Run ≤6 in parallel. Priority: non-lesson sets first (AFR BRO DMU HOB KHM LTR MID MOM MSH NEO ONE SNC STX VOW WOE), then lesson sets (BLB DFT DSK EOE FDN LCI MKM OTJ SOS TDM TLA).
3. After each batch run `./commit_progress.sh` (commits + pushes). A pass.json is valid only if it parses and has one key per target (status_all checks).
## Step 2 — retrain ("B11g")
Replace C9 features with G3 (z-score within set, 1 column) in the B10 feature table (research/c9_power_questions/c9.py builds B10 = B5 + C9 columns; B5 = research/c5_atomic_effects). LOSO 28 sets, ExtraTrees+Ridge 70:30, same as B10. Compare MAE/Spearman vs B10 (oof_B10.csv.gz: MAE 2.231, Spearman 0.6248) pooled and on the 17 non-lesson sets (lesson sets leak: BLB DFT DSK EOE FDN LCI MKM OTJ SOS TDM TLA). Also a TMT/ECL/FRA check (FRA: B10 2.316, B5 2.415). Rule: adopt B11g for TRK if non-lesson-17 MAE <= B10 and Spearman >= B10; else report to user (user already decided to adopt G3 → still use it, but tell the user the numbers).
## Step 3 — TRK (after all cards are revealed 10/31)
G3 on TRK cards: 3 passes, whole set in context, examples from all 13 graded past sets (no outcomes), lessons.md. Recompute TRK forecast with B11g + B10S-style scaling; no X1/MTGAZone. Rebuild export (research/trk_preview/export_b10.py), forecast-trk.json, private preview artifact (rebuild JS bundle). User confirms before publishing (`available: true`, ~11/3).
## Step 4 — docs
Update Projects doc claude/sakiyomi-g3-expert-grade-2026-10-27.md and claude/trk-plan-2026-10-21.md with results/decision.
