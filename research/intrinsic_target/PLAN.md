# Improvement 1: train on the card's own effect (deck strength removed) — pre-registered

Research only; Pages unchanged. FIN, MH3, FRA outcomes not used. Written before any model is fitted.

## Idea
Actual GIH WR = effect of the card + strength of the decks it was played in. Remove the second part from the training target so the model learns the card's own effect, then compare on actual GIH.

## Data
- Training pool and features: the production 28-set pool and feature columns (baseline + C3), unchanged.
- Deck strength from step 1 (`research/deck_pair`): pair WR (unsplashed two-colour decks) centred within set; per card, the shares of its GIH games by pair (from `*_cardpair.csv.gz`, 10 pairs only).
  b_A = Σ_pair share × (pair WR − set mean pair WR) / 100.
- 26 sets (KHM and STX have no deck-colour data). Both arms use the same 25 training sets in every fold.

## Arms (leave one set out; the production model: ExtraTrees 600, leaf 8, mf 0.6, 70% + TF-IDF Ridge 30%, ×1.25; one seed, 20260922)
- **A**: target = actual GIH.
- **B**: target = actual GIH − κ·b_A, **κ = 1**.
- Test: each arm's prediction for the held-out set is compared with the held-out set's **actual** GIH. B gets no deck information at test time.

## Rule I
B is supported if, over the 26 sets, it:
1. lowers pooled MAE versus A;
2. raises mean within-set Spearman versus A;
3. has lower MAE than A in at least 14 of 26 sets.

Reported, not used for the decision: κ = 0.5; each arm against the adjusted target (card-effect space); B + the oracle deck term (b from card colours and true pair WRs, as step 1 M3 B) as a ceiling; split by rarity.

## What follows
If supported: refit with 3 seeds on all training sets as a candidate, and freeze its FRA predictions next to production before FRA data is used. Adoption is the user's decision.
