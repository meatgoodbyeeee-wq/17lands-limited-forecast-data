# C7: tag synergy (good / bad combinations) — pre-registered (Rule F7)

Research only; Pages and production unchanged. Written before any C7 feature was computed or scored. FIN, MH3, FRA outcomes are not used. The synergy table was written from Magic knowledge only (not from outcomes) and is frozen in `c7.py` (`SYNERGY`) with this plan.

## Question
Can the card model use how effect tags combine? Examples: deathtouch is strong with first strike and trample (MN here also covers menace/skulk-type evasion); lifelink wins damage races with flying or hard-to-block bodies; tokens with anthems; recursion with sacrifice; ramp with mana sinks; a mass-removal spell is awkward with your own tokens or counters.

## Table
A symmetric table over the 58 C5 tags, weights +2 (strong), +1 (good), −1 (poor), −2 (conflicting); everything else 0. 108 pairs (`SYNERGY`). Tag names as in `RUBRIC.md` (LL lifelink, DT deathtouch, FS first/double strike, MN menace/trample/skulk-type, FL flying, …). The user's examples are in it.

## Features (8 columns, no tuning)
Per card, tags counted as present (level ≥ 1):
- Within the card: W = sum of weights over tag pairs on the card; Wpos (positive part), Wneg (absolute negative part), Wlvl (W with each pair weighted by the lower of the two tag levels).
- Support from the set: for each tag a on the card, the weighted share of other cards of the same set (excluding the card) that carry a partner tag b: sup_set = Σ_a Σ_b max(S_ab,0) · d_b, fric_set the same with the negative part. Computed over all cards of the set (the full card list is known before release); sup_col / fric_col the same restricted to other cards of the set sharing at least one colour with the card (colourless cards: all cards). Basic lands are excluded.

## Arms (28 sets, leave one set out, production model, seeds 20260922–24)
- A production 2.392 pp, B 2.353, B5 = A + C4 + C5 2.292.
- **B7 = B5 + the 8 synergy columns.** Candidate for the decision is B7 vs B5.
- Reported only: within-card 4 columns alone; set-context 4 columns alone; **shuffled control** — the same 8 features computed with the tag labels of the table randomly permuted (seed 20261004), which keeps the number and weights of pairs but destroys the Magic meaning. A real effect should beat the control.
- Also reported (descriptive, not used by any model): for each tag pair with ≥ 30 cards, the mean B5 out-of-fold residual (actual − predicted GIH WR) of cards carrying both tags, summarised by table sign, and for the user's named examples. Multiple comparisons; direction only.

## Rule F7 (B7 vs B5)
Supported if (1) pooled MAE lower, (2) mean within-set Spearman higher, (3) lower MAE in ≥ 15 of 28 sets, (4) MAE gain > 0.01 pp. Additionally the shuffled control must not match B7 (its MAE gain over B5 must be less than half of B7's); otherwise a gain is reported as "not specific to the table".
If supported: freeze FRA predictions of B7 next to A, B, B5. Adoption is the user's decision.
