# C12 — conditional value of theme-dependent cards (pre-registered, written before any judgement)

## Motivation
C11 showed that a set-list reading identifies cards like Avengers Assemble! (PAY 9, top of 1,018 targets; actual 6th of 278, B10 rank 260) but that adding the readings as extra columns changes almost nothing (B12 gain 0.0015 pp), and that using PAY in place of the single-card GRADE hurts overall (many high-PAY cards, e.g. Rite of the Dragoncaller, Smile at Death, are not good). The missing piece is *whether the condition is met* and the value in each case. C12 separates the two: the reader gives K (enablers needed), ON and OFF grades (same 0–10 scale as C9 GRADE); the probability that a deck meets the condition is computed in code from the set list and the C11 enabler lists. Exploratory diagnostics behind this proposal were run on the C11 output and are not part of the test.

## Judgements
Same 1,067 target cards (unique texts with C10 mean SPEC ≥ 1.5, 29 sets incl. FRA), same input files as C11 (`input/s1`, `input/s2`, names hidden, target order differs), two independent passes by different agents, RUBRIC.md (K, ON, OFF). Caveat as before: readers may recognise historical sets; FRA is the clean test.

## Features (no tuning; non-targets −1, flag 0); each averaged over the two passes
- c12_k (mean K), c12_on, c12_off, c12_dgap = |ON−OFF| mean.
- λ = dwc + 0.5·iwc from the C11 features (castable-in-the-card's-colours, freq-weighted enabler weights, mean of C11 passes); factor fixed a priori.
- c12_pon = P(Poisson(λ) ≥ K) computed per pass then averaged (K = 0 → 1).
- c12_ev = pon·ON + (1−pon)·OFF (per pass, averaged).
- c12_flag.
- Reported-only variant: pon using λ = C11 EXP instead (c12_ev_exp), not used in arms.

## Arms (LOSO over 28 sets, production model e.parts, ×1.25 formula, seeds 20260922–24)
- B10 reference (2.2311 pp / Spearman 0.6248).
- **B13** = B10 + [c12_flag, c12_k, c12_on, c12_off, c12_pon, c12_ev] (3 seeds).
- **B13r** = B10 with `c9_m_GRADE` replaced for target cards by c12_ev (non-targets unchanged), no extra columns (3 seeds).
- Controls (1 seed each): **shuffled B13** and **shuffled B13r**: within each set, permute the targets' (k,on,off,pon,ev) tuples among that set's targets (seed 20261016).
- Reported only: PAY-free ablation `ON only` (c12_on + flag) (1 seed); MAE targets vs others, by rarity, by pon quartile; AUC (set top-15 by actual) of ev vs GRADE vs B10 prediction; predicted GIH WR for Avengers Assemble!, Chronicle of Victory, Necroduality, Rite of the Dragoncaller, Smile at Death, Oko, Lorwyn Liege; pass agreement.

## Rule F13
An arm (B13 or B13r) is supported if all hold versus B10: pooled MAE lower; mean within-set Spearman higher; ≥15/28 sets lower MAE; MAE gain > 0.01 pp; and its shuffled control's gain < half of the arm's gain. The overall rule is supported if at least one of the two arms is supported (two arms tested; no further arm is added after seeing results). If supported: freeze FRA predictions for that arm next to A,B,B5,B10 and add to PENDING_FRA; if not, FRA readings stay descriptive. No production/Pages change either way.
