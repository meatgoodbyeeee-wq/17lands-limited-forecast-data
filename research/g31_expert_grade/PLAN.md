# G3.1: colour-by-colour grading with retrieved expert-graded neighbours (pilot, pre-registered 2026-10-27)

Why: in the G3 pilot the remaining gap to the expert is mostly at common/uncommon (within-rarity
Spearman with actual: C 0.21 vs expert 0.52, U 0.23 vs 0.49; R 0.56 vs 0.61). The expert reviews
colour by colour and compares cards within a colour in the context of the set.

Changes vs G3 (everything else the same):
1. Targets are presented in colour sections (W, U, B, R, G, multicolour, colourless/land), and the
   grader grades each section comparing cards within it, after reading the whole set.
2. For every target card, the 5 most similar past cards (TF-IDF cosine on type + rules text) with
   their expert grades are shown (pool: expert-graded cards of the 13 past sets + FRA, excluding
   the target set). A smaller random calibration set (300 cards) replaces the 800 random examples.
3. lessons_cu.md (new): lessons on ranking commons/uncommons within a colour, written by Opus from
   the 11 lesson sets only (expert grade vs actual by colour and rarity). Used with lessons.md.
Targets: FRA, TMT, ECL; 2 passes each (G3 had 3; compared on the mean of passes).

Primary comparison G3.1 vs G3 (and C9), per set:
 a. Spearman with the B5 residual (B10 without C9) — the fair measure for a C9 replacement.
 b. Mean within-rarity Spearman with actual for commons and uncommons.
Pass: (a) G3.1 > G3 on ≥ 2 of 3 sets AND (b) the 3-set mean of (b) improves by ≥ 0.05.
Reported: overall Spearman with actual, by rarity, agreement with the expert.
Note: these 3 sets were already used for the G3 pilot and the C/U gap analysis that motivated this.
Resume: README_RESUME.md / status.py.

## Note (2026-10-28, during judging)
The answer keys (targets_key.csv, with actual GIH and expert grades) were stored in the same folders as
the judge inputs. Transcript check: only TMT pass 2 opened one (it read 3 rows: T1, T2, T187 — grades
unchanged per its report); all other passes only listed file names. Keys moved to keys/<SET>.csv.
G3 (research/g3_expert_grade) had the same layout; its transcripts show no reads of key contents.
