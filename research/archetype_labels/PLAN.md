# Improvement 4 (redo): official-archetype labels for every card, then pair strength — pre-registered (Rule A)

Research only; Pages unchanged. Written before any label is read or feature computed.
Replaces the earlier proxy test (`research/archetype_roles`), which reused theme-dependence labels instead of real archetype labels.

## Labelling
- Cards: all non-basic cards of the 26 sets with pair WRs (~6,500).
- Per set, one labelling agent (Claude subagent, blind to every 17Lands number and to the pair WRs; sees card name, colours, mana value, type, P/T, rules text).
- Step 1: the agent finds the set's official archetypes (the 10 two-colour pairs, or the 5 designated ones for sets that have 5) with web search (design articles, Wizards' set guides), writes `defs/<SET>.md`: pair code, archetype name, one-line mechanical description, source URL. Three-colour archetypes (5-faction sets) are written with their colour code (e.g. WUB).
- Step 2: for each card: `primary` = the one archetype it fits best (colour code) or `none` (generic: fits any deck of its colours or none); `secondary` = optional other archetype codes; `role` = P (payoff/build-around: much better in that archetype), E (enabler/supports it), G (generic staple that happens to be in its colours). A card's labelled archetype must be consistent with its colours (a card cannot be labelled with an archetype needing a colour it lacks; colourless cards may take any).
- Output `raw/<SET>.csv`: id,primary,secondary,role.
Checks: all ids labelled, codes only from the set's definitions, share of `none`; labels not edited after the fact.

## Features (per set x pair, then centred within set; pair codes with 3 colours map to every pair they contain)
- A1 archetype density: rarity-pack-weighted share of the set's cards whose primary archetype is that pair and role is P or E.
- A2 archetype quality: mean production-OOF prediction of the pair's primary cards with role P or E (set mean if none).
- A3 balance: min(weighted P, weighted E) share for the pair.
- A4 depth: number of commons/uncommons with primary or secondary = pair.
- A5 payoff quality: mean OOF prediction of the pair's role-P cards (set mean if none).

## Model and Rule A
Same as `research/deck_model`: ridge alpha 3 on standardised features, leave one set out over the 26 sets x 10 pairs, target centred unsplashed pair WR. Arms: D (F1–F6) and A (F1–F6 + A1–A5), vs F0 (current formula).
A is supported if (1) mean within-set Spearman ≥ F0 + 0.05 and ≥ D, (2) better than F0 in ≥ 15 of 26 sets, (3) MAE lower than F0. Reported only: A1–A5 alone, per-feature Spearman, alpha 1/10, `none` share per set.

## Caveats stated in advance
The labeller knows these historical sets, so metagame knowledge could leak into labels; the blind-to-numbers rule reduces but does not remove this. Sets with definitions the agent could not source are flagged, not dropped.
