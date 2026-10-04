# C6: vocabulary gap tags on top of C5 — pre-registered (Rule F6)

Research only; Pages and production unchanged. Written before any C6 feature was computed or scored. FIN, MH3 and FRA outcomes are not used.

## Why
Checking the C5 tags on cards (not on outcomes) showed mechanics that the 58-tag vocabulary cannot express: e.g. a Toxic creature got no tag at all. The probe compared mechanics found in card text with the tags the cards received, and with the production baseline columns (which already hold keyword flags for flying, first/double strike, deathtouch, haste, hexproof, lifelink, menace, reach, trample, vigilance, ward, plus aura/equipment/vehicle/planeswalker type flags). Those are not repeated. Gaps that neither C5 nor the baseline can express:

poison (Toxic, poison counters, Infect, corrupted) · proliferate · −1/−1 counters · defender · transform / day-night / double-faced prepared spells · graveyard hate · removal of noncreature permanents · damage prevention · monarch / initiative / the Ring / goad · alternative or shifted casting costs (evoke, dash, blitz, emerge, escape, disturb, madness, miracle, overload, spectacle, mutate, foretell, plot, warp, sneak, ninjutsu, prototype, unearth, offspring) · face-down creatures (manifest, cloak, disguise, morph) · sagas · classes and rooms · lifegain (you gain life) · protection / indestructible / regenerate · legendary.

## Method
These are keyword-level facts in the rules text, so they are set by fixed text rules, not by AI re-extraction (exact, repeatable, no labeller variance). The rules are in `c6.py` (`RULES`), committed with this plan and not changed after seeing any score. Reminder text in parentheses is removed before matching. Each tag is 0/1; 16 columns. Per-tag prevalence is reported. Basic lands are zeros.

## Arms (28 sets, leave one set out, production model, seeds 20260922–24)
- A production (2.392 pp), B = A + C4 (2.353), B5 = A + C4 + C5 (2.292).
- **B6 = B5 + 16 gap tags.** Candidate for the decision is B6 vs B5.
- Reported only: A + C5 + gap tags without C4; B5 + gap tags with at most the 8 tags whose prevalence is ≥ 1%.

## Rule F6 (B6 vs B5)
Supported if (1) pooled MAE lower, (2) mean within-set Spearman higher, (3) lower MAE in ≥ 15 of 28 sets, (4) MAE gain > 0.01 pp. If not supported, B5 stays the best card model and the gap tags are not carried forward. If supported, freeze FRA predictions of B6 next to A, B, B5. Adoption is the user's decision.
