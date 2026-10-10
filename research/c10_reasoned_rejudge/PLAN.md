# C10: reasoned re-judgement of hard cards against a reference ladder — pre-registered (Rule F11)

Research only; Pages and production unchanged. Written before any C10 judgement was made. FIN is used only as the source of reference cards (see below); MH3 and FRA outcomes are not used.

## Why
B10 (B5 + C9) lowered MAE 2.292 → 2.231 pp. Its remaining large errors (26% of cards off by > 3 pp) are concentrated in rares and mythics (3.0 pp, mythic 3.05) and in cards the three C9 passes disagreed on (MAE 2.51 vs 1.99 pp for cards they agreed on); the worst misses are build-around or odd cards judged too low or too high. C9 asked fast numeric questions without any anchor and without reasoning. C10 re-judges exactly the hard cards: with a written reason first, and against a ladder of reference cards of known strength, so the scale is calibrated rather than the judge's own.

## Targets (fixed in `build.py`, `targets.csv`)
Unique card texts (the C9 queue, 7,010 texts incl. 290 FRA) that are rare or mythic in at least one set (FRA by its Pages rarity), OR whose three C9 GRADE answers have standard deviation ≥ 0.6. Cards with no rules text are excluded (neutral). 2,461 cards: 2,105 class R (rare/mythic), 356 class C (common/uncommon with disagreement).

## Reference ladder (`ladder.json`, in `RUBRIC.md`)
From FIN (not among the 28 research sets, not FRA; its outcome was already spent as the final holdout in `fin_final`): per class (C = common/uncommon, R = rare/mythic) seven cards at the 5/20/35/50/65/80/95th percentile of FIN GIH WR within the class (cards with ≥ 1,500 GIH games, rules text ≤ 300 characters, no basic lands; nearest card to each percentile). Judges see the card texts (names hidden) labelled level 1–7, not their win rates. Because FIN is outside all 28 evaluation sets and FRA, the ladder cannot leak any evaluation outcome.

## Extraction
Blind labelling agents, 65 cards per batch (batches within class), two independent passes r1, r2 (different shuffles, different agents, no agent labels a batch twice, no agent sees another pass). Per card one line: reason (≤ 25 words, written first) then PCT (0–100, step 5, position among cards of the class by win rate, anchored on the ladder), GRADE (0–10), SPEC (0–3 build-around dependence). `check_raw.py` validates. Caveat as before: judges may remember historical cards; FRA is the clean test.

## Features (5 columns, no tuning)
For targeted cards: c10_pct = mean PCT of the two passes, c10_grade = mean GRADE, c10_spec = mean SPEC, c10_dpct = |PCT r1 − PCT r2|. c10_flag = 1 for targeted cards. Non-targeted cards: the four values = −1, flag 0 (the tree model separates them).

## Arms (28 sets, leave one set out, production model, ×1.25, seeds 20260922–24)
- B10 (2.2311 pp, Spearman 0.6248), the current best.
- **B11 = B10 + the 5 C10 columns** (3 seeds). Candidate for the decision is B11 vs B10.
- Reported only (1 seed): **shuffled control** — within each set, the targeted cards' four C10 values are permuted among the targeted cards of the same class (seed 20261009), which keeps the distribution and destroys the card link; **pct only** (c10_pct + flag); and MAE of B10 vs B11 for targeted vs non-targeted cards, rarity, and by C9 disagreement.

## Rule F11 (B11 vs B10)
Supported if (1) pooled MAE lower, (2) mean within-set Spearman higher, (3) lower MAE in ≥ 15 of 28 sets, (4) MAE gain > 0.01 pp, and (5) the shuffled control's MAE gain over B10 is less than half of B11's. If supported: freeze FRA predictions of B11 next to A, B, B5, B10 and add to PENDING_FRA. Adoption is the user's decision.
