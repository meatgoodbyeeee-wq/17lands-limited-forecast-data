# C7b: strong synergy pairs only — pre-registered (Rule F7b)

Research only; Pages and production unchanged. Written before any C7b feature was computed or scored. FIN, MH3, FRA outcomes are not used.

## Why
C7 (108 pairs: 18 at +2, 83 at +1, 7 at −1) was not supported (B7 2.2914 vs B5 2.2918 pp, 14/28 sets). The user questioned several of the weaker pairs (e.g. counterspell × haste) and asked to test again with the +1 pairs and the −1 pairs removed. C7b keeps only the 18 pairs at +2 from the C7 table (`SYNERGY` in `../c7_tag_synergy/c7.py`, weight 2, unchanged): deathtouch × first strike / menace-trample / fight; lifelink × flying / menace-trample; flying × equipment; bounce × ETB; fight × +1/+1 counters; mass removal × indestructible etc.; recursion × sacrifice / flashback-type reuse; dies-trigger × sacrifice; ETB × copy; tokens × anthem / sacrifice; steal × sacrifice; repeatable ramp × mana sink; landfall × land fetch.

This is a second look at the same hypothesis after seeing the C7 result. The choice of subset was made by the user from plausibility, not from scores; the C7 pair table was written before any outcome. Because it is a second test of one idea, the shuffled control is mandatory.

## Features (4 columns; the other four C7 columns are constant or duplicated with only positive pairs)
Same construction as C7, tags counted as present (level ≥ 1): W (sum of pair weights on the card; equal to Wpos), Wlvl (weighted by the lower tag level), sup_set and sup_col (weighted share of other cards of the same set / of the same set sharing a colour that carry a partner tag, basic lands excluded). fric_*, Wneg are zero with only positive pairs and are dropped.

## Arms (28 sets, leave one set out, production model, seeds 20260922–24)
- B5 (A + C4 + C5) 2.2918 pp, B7 (all 108 pairs) 2.2914.
- **B7b = B5 + the 4 columns.** Candidate for the decision is B7b vs B5.
- Reported only: within-card (W, Wlvl) alone; set-context (sup_set, sup_col) alone; **shuffled control** (the same 18 pairs with tag labels randomly permuted, seed 20261004).

## Rule F7b (B7b vs B5)
Supported if (1) pooled MAE lower, (2) mean within-set Spearman higher, (3) lower MAE in ≥ 15 of 28 sets, (4) MAE gain > 0.01 pp, and (5) the shuffled control's MAE gain over B5 is less than half of B7b's. If supported: freeze FRA predictions of B7b next to A, B, B5. Adoption is the user's decision.
