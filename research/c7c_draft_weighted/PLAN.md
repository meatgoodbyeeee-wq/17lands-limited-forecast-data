# C7c: rarity-weighted set support for strong synergy pairs — pre-registered (Rule F7c)

Research only; Pages and production unchanged. Written before any C7c feature was computed or scored. FIN, MH3, FRA outcomes are not used.

## Why
In C7/C7b the "support from the set" counted every other card of the set equally (a share of cards carrying a partner tag). The user pointed out that how many good partners a drafter actually meets depends on the set and on rarity: a commons-heavy partner is met often, a mythic partner almost never. C7c replaces the equal count with the expected number of copies of partner cards that a drafter sees, and also reports the plain number of partner cards.

## Table
The 18 strong pairs (weight +2) of the C7 table, unchanged (`SYNERGY` in `../c7_tag_synergy/c7.py`; the weaker pairs and the negative pairs stay out, as in C7b).

## Features (6 columns, no tuning)
Tags counted as present (level ≥ 1), basic lands excluded, the card itself excluded from its own support.
- W, Wlvl: within-card, as in C7b.
- sup_cnt_set, sup_cnt_col: Σ_a∈tags(card) Σ_b S_ab · N_b, where N_b is the NUMBER of other cards of the set (set-wide / sharing a colour; colourless cards: all) carrying tag b. Same as C7b but a count instead of a share.
- sup_w_set, sup_w_col: the same with N_b replaced by the expected number of copies a drafter sees: each card j counts w_j = 3 · slots(r_j) / n_r(set), where n_r(set) is the number of cards of rarity r in the set and slots are per-pack expectations of the booster layout: draft boosters 10 common, 3 uncommon, 0.875 rare, 0.125 mythic; play boosters 7 common, 3.5 uncommon, 1.3 rare, 0.2 mythic. Play layout is used when the set has at least 95 uncommons, else the draft layout (the sets with ~100 uncommons are the play-booster sets; HOB and TMT, with 55 and 54 uncommons, get the draft layout). These slot numbers are approximations of published pack structures, fixed here; only relative sizes matter to the model. Rarity per card comes from the card pool of each set (FRA: the official card list, rarity "land" excluded).

## Arms (28 sets, leave one set out, production model, seeds 20260922–24)
- B5 (A + C4 + C5) 2.2918 pp; B7b (C7b) 2.2921.
- **B7c = B5 + the 6 columns.** Candidate for the decision is B7c vs B5.
- Reported only: counts only (W, Wlvl, sup_cnt_set, sup_cnt_col); weighted only (W, Wlvl, sup_w_set, sup_w_col); **shuffled control** (the same 6 features with the tag labels of the 18 pairs randomly permuted, seed 20261004).

## Rule F7c (B7c vs B5)
Supported if (1) pooled MAE lower, (2) mean within-set Spearman higher, (3) lower MAE in ≥ 15 of 28 sets, (4) MAE gain > 0.01 pp, and (5) the shuffled control's MAE gain over B5 is less than half of B7c's. Third look at the same idea (C7, C7b before): a pass would still need an FRA confirmation before any adoption. If supported: freeze FRA predictions of B7c next to A, B, B5.
