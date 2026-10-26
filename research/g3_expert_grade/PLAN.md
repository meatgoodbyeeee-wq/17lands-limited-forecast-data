# G3: AI GRADE that imitates expert pre-release judgement (pilot, pre-registered 2026-10-26)

Goal: make the AI's card grade as good as a human expert's, using past experts' grades as the
teacher, so that it works for a new set (TRK) WITHOUT that set's expert reviews.

Facts motivating it (13 past sets, 3,251 cards): within-set Spearman with actual GIH is 0.41 for
the AI GRADE (C9) and 0.62 for MTGAZone grades; AI–expert agreement is only 0.46; where they
disagree, the expert tends to be right (Spearman(disagreement, B10 residual) = +0.32).

Inputs per target set T (build.py, deterministic):
- lessons.md: general lessons on where the AI GRADE goes wrong, written once by Opus from
  lesson_material.txt = the 400 largest AI-vs-expert disagreements in 11 sets that are NEVER
  targets (BLB DFT DSK EOE FDN LCI MKM OTJ SOS TDM TLA), with outcomes shown.
- T/examples.txt: ~800 past cards (name hidden) with the EXPERT grade as label (no outcomes),
  66 per past set excluding T.
- T/targets.txt: all scored cards of T (doubles as the whole-set context).
- The target set's expert grades and outcomes are never shown.
Judging: 3 independent Opus passes per set (prompt_judge.txt), output 0–5 grades → T/passK.json.
G3 = mean of passes.

Targets: FRA, TMT, ECL. Metrics per set: Spearman(G3, actual), vs Spearman(C9 GRADE, actual) and
Spearman(expert, actual); Spearman(G3, B10 residual); Spearman(G3, expert).
Pilot pass (needs ≥ 2 of 3 sets): Spearman(G3, actual) > Spearman(C9 GRADE, actual) AND
Spearman(G3, B10 residual) > 0.15.
Reported: B10 + G3 combination with coefficients fitted on the other two pilot sets (MAE, Spearman).
If the pilot passes: full validation (more sets, G3 as a B10 feature replacing/adding to C9).

Resume: see README_RESUME.md; `python3 status.py` lists missing outputs.
