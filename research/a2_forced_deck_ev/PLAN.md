# A2 — conditional expected value judged inside forced-inclusion decks (pre-registered; written before any A2 judgement)

## Background
Pilot A1 (MSH, FDN; 6 hand-picked cards × 3 decks): with the card forced into a sealed deck built by Opus, Sonnet listing the deck's enablers with the order they must be played in, and Opus judging OFF / ON / P (P = share of games the condition is met, accounting for order and timing), the expected value EV = P·ON + (1−P)·OFF ranked the six cards exactly in their actual GIH WR order (Avengers Assemble! 7.1 > Agent Phil Coulson 6.3 ≈ Arahbo 6.3 > Rite of the Dragoncaller 5.5 > Thunderbolts Conspiracy 5.3 > Doubling Season 3.6). The six cards were chosen knowing their outcomes, so the pilot is not evidence; A2 is the test.

## Cards
Per set (29 sets incl. FRA), the 10 rare/mythic theme-dependent cards (C11 targets, SPEC ≥ 1.5) with the highest C11 PAY (ties: higher rarity, then lower id). Selection uses no outcome data. 290 cards; 280 in the 28 scoring sets.

## Pipeline (per card, 3 decks)
1. Pools (code): sealed-style pools of 6 packs (10 C, 3 U, 1 R/M per pack, mythic 1/8), seeds `A2-<set>-<id>-<k>`, k = 0..2, card added if absent; names hidden.
2. Deck building (**Opus**): FORCE.md from A1 unchanged (card must be in the deck; build the best 40-card deck around it).
3. Enablers and order (**Sonnet**): ENABLERS.md from A1 unchanged (each enabler with BEFORE / AFTER / EITHER).
4. Judgement (**Opus**): EVJUDGE.md from A1 unchanged (OFF, ON, P with order and timing).
5. Aggregation (code): per card mean over its 3 decks of OFF, ON, P, EV.
All prompts tell the agents to judge from text only. Checks: forced card present in the deck; formats parsed; any repair documented in NORMALISED.md.

## Arms (LOSO over 28 sets, production model e.parts and ×1.25 formula, seeds 20260922–24)
- B10 reference (2.2311 pp / 0.6248).
- **B15r**: B10 with `c9_m_GRADE` replaced by EV for the 280 cards (other columns unchanged).
- **B15a**: B10 + [a2_flag, a2_off, a2_on, a2_p, a2_ev] (non-selected cards −1, flag 0).
- Control (1 seed each): shuffled B15r / shuffled B15a — within each set, EV tuples permuted among that set's selected cards (seed 20261016).

## Rule F16 (each arm vs B10)
Supported if pooled MAE lower, mean within-set Spearman higher, ≥ 15/28 sets lower MAE, MAE gain > 0.01 pp, and the shuffled control's gain < half of the arm's gain. Overall supported if at least one arm is supported (no further arms after seeing results).
Reported only: MAE and within-set Spearman on the 280 selected cards; Spearman of EV alone vs actual within each set's selected cards; predictions for Avengers Assemble!, Rite of the Dragoncaller and the other A1 cards (flagged: they shaped the method).
If supported: freeze FRA predictions of the supported arm (new frozen file + sha256), add PENDING_FRA item 11, update the 10/28 scheduled verification. If not: FRA readings descriptive. No production/Pages change either way.

## Cost
870 decks: ~870 Opus deck builds, ~870 Sonnet enabler lists, ~870 Opus judgements (batched several per agent call). Run in waves with checkpoints; partial waves are committed as they finish.
