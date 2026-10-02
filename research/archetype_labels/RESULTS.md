# Improvement 4 (redo): official-archetype labels for pair strength — result (Rule A, pre-registered): not supported

All 6,425 non-basic cards of the 26 sets were labelled by 26 blind labelling agents (one per set) with the set's official draft archetypes (`defs/<SET>.md`, with sources; many from third-party guides, noted in each file) and a per-card primary / secondary archetype and role P/E/G (`raw/<SET>.csv`). Colour rule used by all agents: a card's colours must lie inside the archetype's colours. Share of cards with primary `none` per set: see `result.json` (about 14–48%).

26 sets × 10 pairs, leave one set out, ridge alpha 3:

| | mean within-set Spearman | MAE of centred pair WR (pp) |
|---|---|---|
| F0 current formula | 0.348 | 1.779 |
| D: F1–F6 | 0.418 | 1.788 |
| **A: F1–F6 + archetype features A1–A5** | **0.401** | **1.768** |
| A1–A5 only | 0.312 | 1.838 |

Rule A: Spearman ≥ F0 + 0.05 and ≥ D ❌ (0.401 < D 0.418); better than F0 in 11/26 sets ❌ (need 15); MAE lower ✔ (1.768 vs 1.779) → fails. Alpha 1/10: 0.401 / 0.400.

Single features (Spearman): A1 archetype density 0.12, A2 archetype quality 0.26, A3 balance 0.08, A5 payoff quality 0.23 (A4 undefined because the count is constant within some sets). A2 and A5 carry some signal, but only the part already contained in the card-quality features of D; adding all five does not improve on D.

Reading: even with real archetype labels, pair strength is not predicted better than from card quality. Weaknesses to keep in mind: one labelling pass per set, sources partly third-party guides, and a large share of cards labelled `none`. The labellers know these historical sets, so leakage would favour the test, and it still fails. Pages and production unchanged; nothing frozen for FRA.
