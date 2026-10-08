# C8: card × set environment — pre-registered (Rule F8)

Research only; Pages and production unchanged. Written before any C8 model was trained or scored (the step-1 profiles and the feature definitions below were built from card text only). FIN, MH3, FRA outcomes are not used.

## Why
Every earlier extraction judged each card alone ("compared with typical Limited rates"). GIH WR is strength inside one set's environment: the same 5-mana 5/5 flier is a bomb when the set has few answers and few blockers for it, and ordinary when common removal kills it. The full card list of a set is known before release, but no feature so far relates a card to it. B5's largest remaining errors are rares and mythics in both directions, which fits this. C8 computes, for each card, how it fares against the actual cards of its set.

## Step 1 (done, reviewed by the user)
Objective profiles from card text, no AI and no outcomes: `extract.py` (creature P/T/MV/combat keywords; removal effects with kind, amount, scope, speed, conditions) and `perf.py` (47 further performance fields: card flow, tokens, counters, pumps and tricks, protection, life, mana, graveyard, structure, drawbacks; reminder text read; wordings the rules cannot read are filled from the C5 tags, see `filled_from_c5`). Audit against C5 in `audit.py`.

## Step 2 features (`env.py`, 16 columns; NA = −1 where a feature does not apply)
Every other card of the same set is weighted by the expected number of copies a drafter sees per 3 packs (booster layout by rarity, as in C7c). The card itself is excluded from its own environment.
- Removal environment: ans_w (expected copies of set removal that answer this creature), ans_share (as a share of the set's removal), ans_cheap_share (share among removal with MV ≤ 3), reach_share (share of the set's creatures this removal answers), reach_threat_share (the same among threats: rare/mythic or power ≥ 4), set_removal_density.
- Combat environment: atk_survive (share of set creatures it can attack into and survive, including unblockable cases), blk_kill / blk_survive (as a blocker against set creatures), blockable_share (share of set creatures able to block it), stat_rank_mv (P+T percentile among set creatures of the same MV).
- Performance × environment: trick_flip (share of set creatures for which the trick turns a median-size combat: kills gained + blockers saved), protect_env (protection effects × single-target removal density), token_sweep_risk (tokens × sweeper density), lifegain_env (life gained × set aggression: mean power of cheap creatures + share of evasive creatures), aura_risk (creature auras × single-target removal density).

Answer rules (`kill`): damage/shrink kill if toughness ≤ amount; destroy fails on indestructible; hexproof stops single-target; ward ×0.7, protection ×0.5; symmetric sweepers ×0.6; tapped/combat-only ×0.6; setup ×0.8; edict 0.25, bounce 0.25, tap 0.15, pacify 0.7, bite 0.7 of a full answer. Combat: simultaneous damage with first strike, deathtouch, indestructible, flying/reach, unblockable, can't-block. Fixed here, not tuned.

## Arms (28 sets, leave one set out, production model ET 70% + TF-IDF/Ridge 30%, ×1.25; seeds 20260922–24)
- B5 (A + C4 + C5) 2.2918 pp, the current best.
- **B8 = B5 + the 16 columns** (3 seeds). Candidate for the decision is B8 vs B5.
- Reported only (1 seed): removal environment only; combat environment only; performance × environment only; **wrong-environment control** — the same 16 features computed against the card pool of a different set (fixed derangement of sets, seed 20261005). It keeps the card's own profile but destroys the link to its real environment. A real environment effect must beat it.
- Reported: MAE by rarity and for rares + mythics together.

## Rule F8 (B8 vs B5)
Supported if (1) pooled MAE lower, (2) mean within-set Spearman higher, (3) lower MAE in ≥ 15 of 28 sets, (4) MAE gain > 0.01 pp, and (5) the wrong-environment control's MAE gain over B5 is less than half of B8's. If supported: freeze FRA predictions of B8 next to A, B, B5 (FRA's environment = the 290 FRA cards). Adoption is the user's decision.
