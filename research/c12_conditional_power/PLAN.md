# C12: conditional power (strength online vs offline) × computed enabler probability — pre-registered (Rule F13)

Research only; Pages and production unchanged. Written before any C12 judgement was made. FIN, MH3 and FRA outcomes are not used. Inputs (set lists, 1,067 targets, mapping) are those of C11.

## Why
C11 added the AI's own PAY and enabler weights as extra columns: B12 2.2296 vs B10 2.2311 pp (gain 0.0015, Rule F12 not supported). Diagnostics (exploratory, on the finished C11 data, so only hypothesis-generating): the reader rated Avengers Assemble! (Hero anthem + draw, 91/278 Heroes in the set) PAY 9 — highest of all 1,018 targets — while the C9 single-card GRADE was 3; B10 predicted 52.7% (rank 260/278), actual 64.5% (rank 6). But PAY ≥ 7.5 also holds many misses (Rite of the Dragoncaller 8.5 → actual rank 227), and replacing C9 GRADE by PAY wholesale worsens MAE (2.231 → 2.255). The AI's PAY mixes two things: how strong the card is when it works, and how likely it is to work. C12 separates them: the AI judges strength when online (ON) and when offline (OFF), the threshold K and the enabler list E; the probability of being online is computed in code from E and rarity-weighted frequencies. The expected strength then replaces the single-card C9 GRADE for the targets, on the scale the model already learned.

## Judging
Same readers' setting as C11 (`RUBRIC.md`): one reader per set per pass sees the full set list (names hidden, random file code, rarity and freq per card), two independent passes s1/s2 (target order differs), output per target `<id> | K | ON | OFF | E: ...`. Caveat: readers may recognise historical sets; FRA is the clean test.

## Features (no tuning; targets only, others flag 0 / −1)
Per pass: E expanded (`T:` → all other cards of the set with that subtype; target excluded); castable = shares a colour with the target or is colourless (for a colourless target all); λ = 3 × Σ freq(castable E) (fixed constant: a deck draws on its own three packs plus roughly twice as many cards seen in passed packs); p_on = P(Poisson(λ) ≥ K), 1 if K = 0; ev = p_on·ON + (1 − p_on)·OFF. Features are the means over the two passes: c12_K, c12_on, c12_off, c12_lam, c12_pon, c12_ev, plus c12_flag. Calibration (no outcome used): c12_evc = c12_ev − mean(c12_ev over targets) + mean(c9_m_GRADE over targets), a single global shift.

## Arms (LOSO over 28 sets; production model via `e.parts`, ×1.25, seeds 20260922–24)
- **B13** (3 seeds) = B10 with the column c9_m_GRADE replaced by c12_evc for targets (others keep c9_m_GRADE) + c12_flag + c12_K, c12_on, c12_off, c12_lam, c12_pon.
- Reported only (1 seed): **shuffled control** (within each set permute the targets' c12 values, seed 20261014, then build the replacement as above); **add-only** (B10 + the six c12 columns + flag, GRADE untouched); **replace-only** (B10 with GRADE replaced, no added columns).
- Reported: MAE targets vs others and by rarity; pass agreement (Spearman of ev, ON, OFF, pon); for Avengers Assemble!, Chronicle of Victory, Necroduality the c12 values, B10/B13 predictions and within-set predicted rank; among targets the AUC of B10 vs B13 prediction for "actual top-15 of its set".

## Rule F13 (all must hold)
B13 pooled MAE < B10 (2.2311) · mean within-set Spearman > B10 (0.6248) · MAE lower than B10 in ≥ 15/28 sets · MAE gain > 0.01 pp · shuffled-control gain < half of B13's gain. If supported: freeze FRA B13 predictions next to A, B, B5, B10 and add to PENDING_FRA; if not, FRA readings stay descriptive.
