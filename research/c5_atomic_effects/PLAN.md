# C5: atomic effect tags for GIH WR — pre-registered (Rule F5)

Research only; Pages and production unchanged. Written before any extraction. FIN, MH3, FRA outcomes are not used.

## Why
C4 (14 effect-detail fields) lowered pooled MAE 2.392 → 2.353 pp (25/28 sets); the gain came from its numeric fields (STACK, DEAD, SWG, TGT, DMG strongest). The next step is a finer decomposition: each card is broken into atomic effects from a controlled vocabulary of 58 tags (removal mechanisms, card flow, growth, combat abilities, opponent-facing effects, economy, trigger shapes, risks), each at level 1 (minor) or 2 (main), plus three scales (rate vs mana value, clock, defence). Hypothesis: the tree model learns better from which atomic effects a card combines than from a few summary scores.

## Extraction
Same blinded queue as C4 (identical ids, 7,010 unique card texts of the 28 production sets + 290 FRA cards), blind labelling agents following `RUBRIC.md`, sparse line format; `check_raw.py` validates format, tag names, ranges, coverage. Cards with no text are zeros. Caveat as before: the extractor knows historical cards; FRA is the clean test.

## Features
Per card: 58 tag columns (0/1/2), RATE, CLK, BLK (3), and 3 fixed counts: number of tags, number of level-2 tags, number of distinct groups hit (removal, flow, growth, combat, opponent, economy, trigger, risk). 64 columns total, no tuning.

## Arms (28 sets, leave one set out, production model ET 70% + TF-IDF/Ridge 30%, ×1.25, seeds 20260922–24)
- A: production. B: A + C4 (the current best, Rule F passed). **B5: A + C4 + C5.** Candidate for the decision is B5 vs B; B5 vs A is also reported.
- Reported only: A + C5 without C4; tags only (no scales/counts); level-binarised tags.

## Rule F5 (B5 vs B)
Supported if (1) pooled MAE lower, (2) mean within-set Spearman higher, (3) lower MAE in ≥ 15 of 28 sets, (4) MAE gain > 0.01 pp.
If supported: freeze FRA predictions of B5 next to A and B (3 seeds). Adoption is the user's decision.
