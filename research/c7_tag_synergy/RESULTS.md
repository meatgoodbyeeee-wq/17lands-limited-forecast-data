# C7: tag synergy — result (Rule F7, pre-registered): not supported

A table of 108 tag pairs (+2 strong, +1 good, −1 poor; written from Magic knowledge before scoring, `SYNERGY` in `c7.py`) was turned into 8 features per card: synergy inside the card (W, Wpos, Wneg, level-weighted) and support/friction from other cards of the same set (set-wide and same-colour). 28 sets, leave one set out, production model, B7 with seeds 20260922–24.

| arm | pooled MAE (pp) | mean within-set Spearman | sets lower MAE vs B5 |
|---|---|---|---|
| B5 (A + C4 + C5) | 2.2918 | 0.6061 | – |
| **B7 = B5 + 8 synergy columns** | **2.2914** | **0.6067** | **14 / 28** |
| within-card only (4), reported | 2.2906 | 0.6066 | 18 |
| set-context only (4), reported | 2.2924 | 0.6061 | 13 |
| shuffled-label control (8), reported | 2.2922 | 0.6055 | 14 |

Rule F7: MAE lower ✔ (−0.0004 pp), Spearman higher ✔ (+0.0006), ≥ 15 sets ❌ (14), gain > 0.01 pp ❌ → not supported. The shuffled control gains nothing either (−0.0004 pp), so there is also no sign that the table carries meaning the model could use.

Descriptive check (not used by any model): for the 213 tag pairs with ≥ 30 cards, the mean B5 residual of cards carrying both tags. Pairs the table rates positive (37 pairs) average +0.124 pp, pairs the table does not list (176 pairs) +0.126 pp: no difference. No pair rated negative has ≥ 30 cards (such combinations are rare: 0.4% of cards have any within-card negative pair). Named examples (mean residual pp, n): flying + lifelink +0.88 (57), equipment + flying +0.57 (50), tokens + anthem +0.95 (29), ramp + mana sink +0.85 (29), menace/trample + lifelink +0.39 (21), recursion + sacrifice −0.43 (20); deathtouch with first strike (6 cards) or with menace/trample (6) are too few to say anything.

Reading
- Direction of the examples is mostly right (positive residuals for flying + lifelink etc.), but B5 already captures most of it, and the leftover is small and of the same size for pairs the table does not list.
- Good-combination cards are few: only about half of the cards carry any listed pair and most carry one; the model has little data on specific combinations, so a hand-written table cannot add much beyond the tags themselves.
- Not tested: pair effects learned from data (1,653 possible pairs on ~7,000 cards would need strong shrinkage), and synergy at the deck level (colour-pair strength), where card tags have not helped either.
- Pages and production unchanged; B5 stays the best card model; nothing new frozen for FRA.
