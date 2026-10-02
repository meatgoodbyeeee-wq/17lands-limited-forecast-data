# Card GIH: official-archetype features and C3 ablations — result (Rule G, pre-registered): not supported

28 production sets, leave one set out, production model. Labels: all 28 sets + FRA (`research/archetype_labels`). Fold check: re-running arm A on AFR reproduced the production OOF exactly (max diff 2e-16).

## Rule G (3 seeds)
| | pooled MAE (pp) | mean within-set Spearman | sets with lower MAE than A |
|---|---|---|---|
| A production (baseline + C3) | 2.392 | 0.562 | – |
| **B: A + 9 archetype features** | 2.396 | 0.560 | 14 / 28 |

All four conditions fail (MAE, Spearman, sets ≥ 15, gain > 0.01 pp). By rarity (A → B, pp): common 1.812 → 1.814, uncommon 2.368 → 2.372, rare 3.137 → 3.135, mythic 3.407 → 3.435.
Not frozen for FRA (the plan only freezes a supported candidate).

## Reported only (seed 20260922; compared with A at the same seed: 2.392 / 0.562)
| arm | pooled MAE | Spearman | sets lower MAE |
|---|---|---|---|
| B without set-context features (support/payoff counts) | 2.396 | 0.561 | 11 |
| A without C3 raw 10 fields | 2.424 | 0.548 | 4 |
| A without C3 12 dependency one-hots | 2.393 | 0.563 | 12 |
| A without C3 4 composites | 2.399 | 0.559 | 12 |

## Reading
- Archetype membership and role add nothing to the card model; the context version (how many enablers support a payoff) does not help either. The trees already see the card's effects (C3) and colours; which named archetype a card belongs to is redundant with them, and archetype labels carry no information about how strong that archetype turned out to be.
- C3's gain comes almost entirely from the 10 raw fields (removing them costs 0.032 pp and 0.014 Spearman). The 4 composites help a little (0.007 pp). The 12 dependency one-hots are neutral (removing them changes MAE by +0.001 pp, within noise), so there is nothing meaningful to prune.
- Feature optimisation of the current C3 set therefore has little headroom; the next gains would need new information in the raw-field style (better-extracted card effects), not regrouping.

Pages and production unchanged.
