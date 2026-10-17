# A3 — simulated P(on) with A2 OFF/ON (pre-registered, Rule F17)

Committed before any simulation or scoring. Production gih-c3-28set-20260929 and Pages are untouched.

## Why
In A2 the judge estimated P by feel (e.g. Rite of the Dragoncaller 60–75 %, close to Avengers Assemble!).
A3 keeps A2's per-deck OFF and ON unchanged and replaces only P with a value computed from the deck list,
the Sonnet enabler list (MV, BEFORE/AFTER/EITHER) and draw order. No new AI calls.

## Simulation (per A2 deck, 20,000 games, seed 20261018)
- Deck = A2 decks/<name>.txt: MAIN ids (with copies) + basics. Lands = basics + MAIN cards whose type contains "Land".
- Play/draw 50/50; 7-card opening hand, no mulligan; draw each turn (not turn 1 on the play); horizon turn 10.
- One land played per turn when a land is in hand; available mana on turn n = lands played so far.
- Target is cast on the first turn where it is in hand and mana >= its MV. Games where it is never cast by turn 10 are excluded (P is conditional on the target being played).
- Enablers: each copy of a listed id in MAIN. An enabler is "castable" on a turn when it is in hand and its MV <= mana that turn.
  - BEFORE/EITHER enabler counts for "before" if castable on some turn strictly before the target turn, or on the target turn with MV + target MV <= mana.
  - AFTER/EITHER enabler counts for "after" if in hand (drawn) and castable on a turn from target turn+1 to min(target turn+3, 10), or on the target turn with leftover mana.
- Condition met: if the list has any BEFORE entry -> need >= 1 "before" enabler; else if it has AFTER entries -> need >= 1 "after" enabler; EITHER-only -> either count. No enablers -> P = 1.
- Removal / combat losses are NOT modelled (limitation, stated in advance).
- EV_sim = P_sim * ON + (1 - P_sim) * OFF per deck; card value = mean over its 3 decks.
- Descriptive only: P with threshold >= 2 enablers.

## Arms (same machinery as A2, B10 baseline)
- B16r: replace c9_m_GRADE with EV_sim for the 290 selected cards.
- B16a: add a3_flag, a3_off, a3_on, a3_psim, a3_evsim (-1 for non-selected).
- shuf_B16r / shuf_B16a: within-set permutation of A3 columns among selected cards, seed 20261018, 1 seed.

## Rule F17 (per arm, vs B10 pooled MAE 2.2311 / Spearman 0.6248)
Pass iff MAE lower AND Spearman higher AND >= 15/28 sets lower MAE AND gain > 0.01 pp AND shuffled gain < half of the arm's gain.
If either arm passes: freeze FRA predictions (file + sha256), add PENDING_FRA item 12, update the 10/28 scheduled task. Otherwise FRA stays descriptive.
Also reported (descriptive): P_sim vs A2 judge P, named cards (Avengers Assemble!, Rite of the Dragoncaller, Smile at Death, ...), and comparison with A2 (Rule F16).
A1 pilot cards shaped the method and are flagged.
