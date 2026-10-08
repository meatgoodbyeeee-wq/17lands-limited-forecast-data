# C8: card × set environment — result (Rule F8, pre-registered): not supported

16 features relating each card to the actual cards of its set (removal that answers it, what its removal answers, combat against the set's creatures, tricks/protection/tokens/lifegain/auras against the set's removal, sweepers, sizes and speed), each other card weighted by how often a drafter sees it. Built from the step-1 objective profiles (no AI beyond the C5 fallback, no outcomes). 28 sets, leave one set out, production model, B8 with seeds 20260922–24.

| arm | pooled MAE (pp) | mean within-set Spearman | sets lower MAE vs B5 |
|---|---|---|---|
| B5 (A + C4 + C5) | 2.2918 | 0.6061 | – |
| **B8 = B5 + 16 environment columns** | **2.2914** | **0.6051** | **15 / 28** |
| removal environment only (6), reported | 2.2899 | 0.6061 | 15 |
| combat environment only (5), reported | 2.2931 | 0.6050 | 9 |
| performance × environment only (5), reported | 2.2930 | 0.6051 | 11 |
| wrong-environment control (16), reported | 2.2932 | 0.6051 | 15 |

Rule F8: MAE lower ✔ (−0.0004 pp), Spearman higher ❌ (0.6061 → 0.6051), ≥ 15 sets ✔ (15), gain > 0.01 pp ❌, control below half ✔ → not supported.

By rarity (MAE pp, B5 → B8): common 1.769 → 1.767, uncommon 2.282 → 2.279, rare 2.935 → 2.937, mythic 3.239 → 3.247; rares + mythics 3.009 → 3.012. The rare/mythic errors that motivated C8 do not shrink.

Descriptive check (not used by any model): rank correlation of each environment feature with the B5 residual (actual − predicted). All are small (|ρ| ≤ 0.07 over all cards; for rares and mythics ≤ 0.06, e.g. removal answering the creature 0.002, attacking survival 0.03). Values computed against the real set and against a wrong set correlate 0.84–0.99 across cards, so set environments differ much less than cards do.

Reading
- The environment of a set, as far as it can be computed from the card list, explains almost nothing of what B5 gets wrong. How many of a set's answers kill a creature, or how it fights the set's creatures, is mostly determined by the card's own size and keywords, which B5 already has.
- Removal environment alone is the best subset (−0.002 pp), still noise-level.
- The remaining rare/mythic error is therefore not about the set environment in this sense. Candidates left: how strong a card's effect is when it resolves (not captured by structure), how the actual metagame plays out (speed, popular archetypes), and labelling noise in the outcome itself for rarely drafted cards (mythics have the fewest GIH games).
- Pages and production unchanged; B5 stays the best card model; nothing frozen for FRA. The step-1 profiles (`profiles.csv.gz`, `review_profiles.csv`) remain available for later work.
