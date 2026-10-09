# C9 results: power judged by seven questions × three passes (Rule F10) — supported

Research only; Pages and production unchanged. Pre-registered in PLAN.md before extraction. 28 sets, leave one set out, production model, 3 seeds.

## Rule F10 (B10 = B5 + 17 C9 columns vs B5)
| arm | pooled MAE pp | within-set Spearman | sets with lower MAE than B5 |
|---|---|---|---|
| A (production) | 2.3923 | 0.5624 | – |
| B5 (A + C4 + C5) | 2.2918 | 0.6061 | – |
| **B10 (B5 + C9)** | **2.2311** | **0.6248** | **26 / 28** (worse: MID, WOE) |

All four conditions hold (MAE lower, Spearman higher, ≥15 sets, gain 0.061 pp > 0.01) → **Rule F10 supported**.

Reported arms (1 seed): B5 + pass-1 answers only 2.2384 / 0.6242 (24/28); B5 + means only 2.2286 / 0.6277 (26/28); **A + C9 means only (no C4, no C5) 2.2510 / 0.6152 (22/28)**.
- Averaging three passes helps a little (pass 1 only: gain 0.053; means: 0.063). The spread features (sd across passes) add nothing (B10 with sd ≈ means only).
- Seven judged numbers alone beat the 14 C4 fields + 64 C5 columns together (2.251 vs 2.292): how strong the card is matters more than what it does, as far as these extractions go.

## Where it helps (MAE B5 → B10)
- Rarity: common 1.769→1.743, uncommon 2.282→2.242, rare 2.935→2.822, mythic 3.239→3.045 (largest gain where the error was largest).
- By number of C5 tags: 0–1 tags 1.794→1.743, 2–3 2.277→2.224, 4–5 2.423→2.356, 6+ 2.916→2.680 (n = 159).

## Inter-pass agreement (7,010 card texts, Spearman between passes; exact-match share)
IMP 0.84–0.88 (73%), UNA 0.75–0.79 (68%), VAL 0.69–0.80 (78%), FLOOR 0.66–0.77 (71%), FLEX 0.59–0.71 (68%), PLAY 0.77–0.84 (68%), GRADE 0.83–0.90 (55% exact; mean sd 0.35). Detail in `agreement.json`. The labelling is reasonably repeatable; FLEX and FLOOR are the noisiest.

## Caveats
- **Leakage**: the labellers may remember historical cards and how they performed (GRADE and PLAY most likely). The 28-set gain can therefore be inflated; names were hidden, but many cards are recognisable from text. FRA (released after the labellers' knowledge) is the clean test.
- Pass-1/2/3 labels come from different agents in different card orders; a systematic bias shared by all agents is not averaged out.
- Adoption into production is the user's decision.

## FRA freeze
`fra_frozen_predictions.csv` (columns pred_A, pred_B, pred_B5, pred_B10; sha256 in `fra_frozen_predictions.json`): B10 vs B5 mean absolute difference 0.61 pp, correlation 0.938. Added to PENDING_FRA as item 10 (B10 beats B5 and A on MAE and within-set Spearman, indicative, one set).
