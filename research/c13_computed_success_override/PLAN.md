# C13 — computed success probability + explicit override of B10 (pre-registered before any computation)

## Motivation
C11/C12: reading the set list identifies theme-dependent cards, but adding the readings as columns to the ET model changes nothing (columns ignored). C12's success probability (Poisson, λ = dwc + 0.5·iwc ≈ 4) was too conservative (Avengers Assemble!: 91/273 Hero cards in MSH, P(on)=0.21). C13 (a) computes P(on) from the set composition, and (b) applies a narrow explicit override to B10's prediction instead of feeding features to the model. No new AI judgement is used: K, ON, OFF from C12 (s1, s2), enabler lists from C11 (s1, s2, D ∪ I with `T:` expanded; target excluded). The 28 sets are a *selection ground* (nested LOSO); the clean test is FRA on 10/28.
Known weakness stated up front: ON was under-called for some top cards in C12 (ON < C11 PAY in 264/1,067). It is not changed here.

## P(on) (deterministic, no tuning)
- Deck colour options for a target card with colour set S: |S| ≥ 2 → exactly S; |S| = 1 → S plus each one of the other four colours (4 options); colourless → all 10 colour pairs. A card is castable in a deck if its colours ⊆ deck colours (colourless always castable). Only non-land cards count.
- share = Σ freq(enablers castable in the deck, excluding the target) / Σ freq(all non-land cards castable in the deck, excluding the target) (freq = rarity-aware expected copies, as in C11).
- X ~ Binomial(22, share) (22 other spells in a 23-spell build); P(on) = P(X ≥ K), 1 if K = 0; averaged over the deck options; computed per pass (C11 s_i lists with C12 s_i K) then averaged. ev = P(on)·ON + (1−P(on))·OFF per pass, averaged.

## Override of B10 (applied to B10's out-of-fold prediction; no retraining)
For target cards: d = ev − g, g = c9_m_GRADE (C9 mean GRADE); adj_pp = κ · slope · sign(d) · max(0, |d| − m); pred' = pred + adj_pp/100. slope = pp of B10 prediction per GRADE point, from least squares of (pred − mean by set×rarity) on (GRADE − mean by set×rarity) over the training sets (all cards). Grid: m ∈ {0,1,2,3} grade points × κ ∈ {0.25,0.5,1.0} (12 combos; no other values). Selection by **nested LOSO**: for each held-out set choose the (m, κ) with lowest pooled MAE of pred' on the other 27 sets (all cards, adjustments only on targets), apply to the held-out set. Non-targets unchanged.

## Reported
Pooled MAE, mean within-set Spearman, sets with lower MAE than B10, chosen (m,κ) per fold, MAE of targets vs others, AUC for set top-15 of pred' vs pred, predicted change for Avengers Assemble!, Chronicle of Victory, Necroduality, Rite of the Dragoncaller, Smile at Death, Oko, Lorwyn Liege; P(on) summary and its value for those cards; sensitivity: MAE gain with all-28-set best (m, κ) (optimistic, not used for the rule).
**Shuffled control**: within each set permute the targets' (ev) values (seed 20261017), same nested procedure.

## Rule F14 (versus B10 = 2.2311 pp / Spearman 0.6248)
Supported if nested pooled MAE lower, mean Spearman higher, ≥15/28 sets lower MAE, MAE gain > 0.01 pp, and the shuffled control's gain < half of the actual gain. If supported: freeze FRA override predictions (the (m, κ) selected on all 28 sets, applied to frozen pred_B10 with FRA C11/C12 readings) as `pred_B10ovr` in a new frozen file with sha256, add PENDING_FRA item 11, update the scheduled verification. If not: FRA stays on B10; readings descriptive. No production/Pages change either way.
