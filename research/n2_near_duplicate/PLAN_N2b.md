# N2b — near-duplicate correction, restricted by human review (pre-registered, written before any residual-based computation)

Follow-up to N2 (PLAN.md / RESULTS.md: Rule N2 failed). Offline re-scoring of EXISTING B10 OOF predictions. No model fits, no production / Pages / TRK file changes. FRA and TRK actuals are not read. Same branch, never merged.

## Origin of the definition (residuals were NOT looked at)
After N2 failed, the user judged auto-matched pairs by eye (`review/round1.json`, `review/round2.json`; 81 pairs; vote S = nearly the same, C = similar but different, D = different; `sim` = N2 TF-IDF cosine). Findings: non-creature non-land cards: cos >= 0.95 was 6/6 S, 0.90-0.95 was 3/6 S. Creatures: even cos 1.0 was rarely S; the only S creature pairs had both equal mana value and equal P/T. Lands: all S regardless of similarity. The definition below was fixed from these human votes only, not from the N2 residuals and not from FRA/TRK.

## Definition of pair (c in set S, d in another set)
Kept from N2: same card category (`prep.category`), different set, different card name, both texts >= 6 tokens, same TF-IDF/normalisation. N2's |mv_c - mv_d| <= 1 is also kept for non-creatures (my reading: the instruction listed four conditions to keep; the +-1 rule is an N2 condition not mentioned, and I keep it as the conservative choice; for creatures mv must be equal, which is stricter). Lands are excluded from the primary.
- **Primary (Rule N2b):** creature: cos >= 0.95 AND mv equal AND P/T string equal. Non-creature non-land: cos >= 0.95. Lands: not corrected.
- **Report-only arm (a):** as primary but non-creature threshold 0.90 (creature rule unchanged).
- **Report-only arm (b):** lands only, cos >= 0.80 (same as N2's 0.80 setting; mv +-1 as N2).
Nothing else is tried.

## Correction, judgement, bootstrap (same as N2)
corrected_pred_c = pred_c + n/(n+1) * mean_{d in M(c)} r_d (k = 1 fixed; r = set-centred OOF residual in pp). Rule N2b (all four): (1) MAE of corrected cards lower than B10; (2) paired |err| difference over corrected cards, bootstrap over cards, 10,000 resamples, seed 20261026, 95 % percentile CI upper < 0; (3) pooled MAE over 7,075 cards not worse; (4) mean within-set Spearman (28 sets) not lower by 0.0005 or more. Pass = "worth a follow-up" only.

## Expected share truly "nearly the same"
In the review sample, pairs satisfying the primary definition: 10 pairs, 10 are S (100 %; Wilson 95 % lower bound about 72 %). Caveat: the non-creature >= 0.95 pairs (6) are the same pairs the rule was derived from, so this is in-sample and optimistic. Arm (a) non-creature extra band: 14 pairs at >= 0.90 of which 11 S. Lands cos >= 0.80: 18/18 S.

## Reporting
Cards and pairs per category for primary and arms; Rule N2b numbers (primary judged, arms report-only); top gain/loss cards; corr(mean partner residual, target's own residual) over corrected cards (N2: -0.18).

## Known limitations
- Same as N2: neighbour OOF residuals come from models that saw the evaluated set (leak), which worked against N2.
- Review sample is small (81 pairs); the creature rule rests on 2 S pairs.
- Definition was set from past-set human judgement only, not FRA; no out-of-sample check here.
- Bootstrap resamples cards, not pairs (mutual use of residuals), so intervals may be optimistic.
