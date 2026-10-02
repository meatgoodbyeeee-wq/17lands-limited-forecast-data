# Improvement 1 results: Rule I not supported

Research only; Pages unchanged. The plan was committed before any model was fitted.
Reproduce: `python3 research/intrinsic_target/intrinsic.py` (about 10 minutes; outputs `result.json`, `oof.csv.gz`).
26 sets, leave one set out, production model with one seed (20260922), both arms on the same 25 training sets.

| | MAE vs actual GIH (pp) | mean within-set Spearman | sets with lower MAE than A |
|---|---|---|---|
| **A** actual-GIH target | **2.404** | **0.561** | – |
| B κ = 1 (deck strength removed) | 2.531 | 0.554 | 6 / 26 |
| B κ = 0.5 | 2.442 | 0.559 | 9 / 26 |

Rule I fails on all three criteria.

## Reading
- B is worse on actual GIH because it predicts only the card's own part. The deck-strength part, which is in the actual GIH, is missing (no deck information at test time).
- In the card-effect space (adjusted target) B has a lower MAE (2.343 vs 2.402) but the same Spearman (0.570 vs 0.571). Most of the change is the removed deck term itself, not a better order of cards.
- With the oracle deck term added back (ceiling): A 2.356 / 0.593, B κ = 0.5 2.349 / 0.596. The two arms end up the same.
- By rarity, B is worse in every rarity.

## Conclusion
The model already ranks cards as well when trained on actual GIH. Removing deck strength from the target does not teach it more about the cards, and the deck-strength part cannot be predicted before release. Not pursued further. Nothing is frozen for FRA.
