# Card GIH: official-archetype features and C3 feature optimisation — pre-registered (Rule G)

Research only; Pages and production unchanged. Written before any model with these features is run.
FIN, MH3 and FRA outcomes are not used.

## Labels
- 26 sets already labelled (`research/archetype_labels/raw`). KHM, STX (to complete the 28 production sets) and FRA (for a prospective freeze) are labelled now with the same procedure and prompt (blind to all 17Lands numbers; colour rule: card colours inside the archetype's colours).
- FRA ids map to Pages card ids via `research/archetype_labels/fra_id_map.csv`.

## Archetype features (ARCH, 9 columns, card level, built mechanically from the labels)
Let k = card's primary archetype; "count" = number of commons/uncommons in the set, divided by the set's commons/uncommons count.
1. `arch_in`: primary is not none.
2. `arch_P`: role P. 3. `arch_E`: role E.
4. `arch_n`: number of archetypes the card fits (primary + secondaries).
5. `arch_support`: count of other cards with primary or secondary k and role E (0 if none).
6. `arch_payoffs`: count of other cards with primary k and role P.
7. `arch_P_x_support`: `arch_P` × `arch_support` (a payoff is better when enablers are plentiful).
8. `arch_gold_fit`: card has exactly the colours of its primary archetype and ≥ 2 colours.
9. `arch_colour_flex`: number of the set's archetypes whose colours contain all of the card's colours (lands/colourless: number of archetypes).

## Arms (28 sets, leave one set out, production model ET 70% + TF-IDF/Ridge 30%, ×1.25, seeds 20260922–24 averaged)
- **A**: production (baseline + C3). Its OOF is `research/production_c3/oof_28set.csv.gz`; one fold is re-run to confirm it reproduces.
- **B**: baseline + C3 + ARCH (main candidate).
Reported only (do not decide): C3 group ablations on arm A, each dropping one group — raw 10 fields; 12 dependency one-hots; 4 composites — to show where C3's gain comes from; ARCH without the set-context features 5–7.

## Rule G (for B vs A)
B is supported if (1) pooled MAE is lower, (2) mean within-set Spearman is higher, (3) MAE is lower in ≥ 15 of 28 sets, and (4) the MAE gain exceeds 0.01 pp (the C3 baseline's seed-to-seed range was 0.0013 pp).
If supported: freeze FRA predictions of B next to production before any FRA outcome is used, and score them on FRA's 28-day data with the other frozen checks. Adoption is the user's decision.

## Caveat stated in advance
The labelling agents know the historical sets, so knowledge of how archetypes performed could leak into labels; FRA (after the knowledge cutoff) is the clean test. Ablation results are exploratory, because choosing a subset on the same 28 sets would overfit.
