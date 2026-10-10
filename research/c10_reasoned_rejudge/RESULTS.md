# C10 results: reasoned re-judgement of hard cards against a FIN reference ladder (Rule F11) — not supported

Research only; Pages and production unchanged. Pre-registered in PLAN.md before any judging. 2,461 targeted card texts (2,105 rare/mythic, 356 common/uncommon with C9 disagreement), two independent passes with a written reason, ladder of 7 FIN cards per class. 28 sets, leave one set out, production model.

## Rule F11 (B11 = B10 + 5 C10 columns vs B10)
| arm | pooled MAE pp | within-set Spearman | sets lower MAE than B10 |
|---|---|---|---|
| B5 | 2.2918 | 0.6061 | – |
| B10 (C9, current best) | 2.2311 | 0.6248 | – |
| **B11 (B10 + C10)** | 2.2332 | 0.6234 | 11 / 28 |
| shuffled control (1 seed) | 2.2350 | 0.6228 | 12 / 28 |
| pct only (1 seed) | 2.2304 | 0.6245 | 14 / 28 |

MAE not lower, Spearman not higher, 11 < 15 sets, gain −0.002 pp → **Rule F11 not supported** (the control condition is met only because B11 itself gains nothing).

## Where it should have helped, and did not (MAE B10 → B11)
- Targeted cards (n = 2,372 rows): 2.780 → 2.788; non-targeted 1.954 → 1.953.
- Rarity: common 1.743→1.745, uncommon 2.242→2.251, rare 2.822→2.812, mythic 3.045→3.053.
- By C9 disagreement quartile (low → high): 1.986→1.986, 2.108→2.103, 2.323→2.319, 2.506→2.525 (the quartile C10 targeted most).

## Why: C10 repeats C9
- Within the targeted cards, C10 percentile and the C9 mean grade are correlated 0.88 (Spearman). Their within-set rank correlation with actual GIH WR is the same: C10 PCT 0.58, C10 GRADE 0.58, C9 GRADE 0.60 (rares/mythics 0.59 vs 0.61; commons/uncommons 0.26 vs 0.30).
- Correlation with B10's residual is small for both (C10 PCT 0.10, C9 GRADE 0.08) and the tree model gained nothing from it.
- Two C10 passes agree well (Spearman PCT 0.92, GRADE 0.90, SPEC 0.83), so the lack of gain is not labelling noise: the judges consistently misjudge the same cards. A written reason and a calibrated ladder change the scale, not which cards the AI misreads.
- SPEC (build-around dependence) correlates −0.38 with actual rank, but that is mostly the same card-weakness information, and it added nothing beyond B10.

## Conclusion
More careful judgement of the same cards by the same kind of judge is exhausted: C9's three fast passes already carry what a reasoned, ladder-anchored AI judgement can say about card text. The remaining error on hard cards is information the text-only judgement does not contain (how the card is actually drafted and played, deck context, set environment). No FRA freeze for C10 (rule not supported). Adoption of C9/B10 remains the user's decision after the 10/28 FRA check.
