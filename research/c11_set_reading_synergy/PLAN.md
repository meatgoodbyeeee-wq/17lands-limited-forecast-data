# C11: judging theme-dependent cards against the whole set list — pre-registered (Rule F12)

Research only; Pages and production unchanged. Written before any C11 judgement was made. FIN, MH3 and FRA outcomes are not used.

## Why
After B10, the largest misses are theme-dependent cards: of rares/mythics that C10 judged to depend on a build-around (SPEC ≥ 2), 11–17% miss by more than 5 pp in each direction (MAE 3.0–4.1 pp vs 2.5 for deck-independent rares). Examples: an anthem for a creature type that is a third of the set (+11.8 pp under-predicted), token and spell-copy payoffs whose enablers are missing (−12 pp over-predicted). Whether such a card is strong depends on the other cards of the set and on how often a drafter sees them. A crude count of same-type cards explained little (rank correlation with the residual 0.07–0.13), because it ignores indirect enablers (token makers, type granters, tutors), card quality and rarity. C11 lets an AI read the whole set list and judge each theme-dependent card against it, including indirect enablers and rarity frequency.

## Targets (`build.py`, `set_cards.csv.gz`)
Unique card texts per set (the 28 research sets from the pool plus FRA; basic lands excluded; 7,210 cards) whose C10 two-pass mean SPEC ≥ 1.5 (C10 targets only: rare/mythic or C9-disagreement cards): 1,067 targets, 25–57 per set. SPEC comes from card text only. Cards of the set list that have no 17Lands record are absent; the list is the pool the model sees plus FRA's 290.

## Judging
One reader per set per pass reads the full set list (names hidden, set code hidden by a random file code) with each card's rarity and `freq` (expected copies seen in 3 packs, booster layout as in C7c: draft layout C10/U3/R0.875/M0.125, play layout C7/U3.5/R1.3/M0.2 per pack), then answers for every target card (`RUBRIC.md`): PAY (0–10 strength in this set), EXP (expected enablers in a typical deck of its colours), D (direct enablers: cards it needs, rewards or counts) and I (indirect enablers: token makers, type/keyword granters, tutors, recursion, sacrifice/flicker/copy engines) as card ids or `T:<Subtype>`. Two independent passes s1, s2 by different agents (target order differs); no agent sees another pass. Caveat as before: readers may recognise historical sets; FRA is the clean test.

## Features (8 columns, no tuning; targeted cards only, others −1 with c11_flag 0)
- c11_flag, c11_pay (mean PAY), c11_exp (mean EXP), c11_dpay = |PAY s1 − PAY s2|.
- Computed from the listed enablers (`T:` expanded to all other cards of the set with that subtype; the target itself excluded; weighted by freq, i.e. rarity-aware): c11_dw = Σ freq of direct enablers; c11_dwc = the same restricted to enablers castable in the card's colours (share a colour or colourless; for a colourless card all); c11_iw, c11_iwc for indirect enablers. Each averaged over the two passes.

## Arms (28 sets, leave one set out, production model, ×1.25, seeds 20260922–24)
- B10 (2.2311 pp, Spearman 0.6248), the current best.
- **B12 = B10 + the 8 C11 columns** (3 seeds). Candidate for the decision is B12 vs B10.
- Reported only (1 seed): **shuffled control** (within each set the targets' 7 values are permuted among that set's targets, seed 20261010); **PAY only** (c11_pay + flag); MAE of B10 vs B12 for targets vs others, rare/mythic, by quartile of c11_dwc; and the cards named in the discussion (Avengers Assemble!, Chronicle of Victory, Necroduality).
- Reported: agreement between the two passes (Spearman of PAY, EXP, dw), mean number of listed enablers.

## Rule F12 (B12 vs B10)
Supported if (1) pooled MAE lower, (2) mean within-set Spearman higher, (3) lower MAE in ≥ 15 of 28 sets, (4) MAE gain > 0.01 pp, and (5) the shuffled control's MAE gain over B10 is less than half of B12's. If supported: freeze FRA predictions of B12 (FRA readings are the clean test) next to A, B, B5, B10 and add to PENDING_FRA. If not supported, the FRA readings are still kept (descriptive). Adoption is the user's decision.
