# Colour-hoser metrics (exploratory, 2026-09-29)

Historical cycles: AFR, SNC and MOM uncommons (15 cards). Source: official Premier Draft Public Game Data, same 28-day window as the model data.
`data/<SET>_hoser.json` is written by `hoser_split.py` (Actions workflow `hoser_metrics.yml`); `summary.csv` holds the derived values.

## Findings
- **Share of GIH games in which the opponent plays a target colour ("live"):**
  - one target colour: 38–65% (AFR mean 40%, SNC mean 56%)
  - two target colours (MOM): 70–78%
- **Live vs dead:** difference-in-differences against the other mono-coloured cards of the same colour, using the same opponent split.
  Hosers win 4.24pp more when live (weighted mean, se 0.21). All 15 are positive.
- **Two kinds:**
  - **Solid base effect:** SNC cost-reduction cycle; AFR Burning Hands, Hunter's Mark, Ray of Enfeeblement.
    - GIH WR in dead games is about the set average (−1 to +3pp).
    - They are maindecked like peer uncommons (≈15–29% of games of that colour).
    - Their overall GIH WR is above average.
  - **Weak base effect:** MOM Change the Equation, Glistening Deluge, Lithomantic Barrage; AFR Divine Smite.
    - GIH WR in dead games is −6 to −12pp versus the set mean.
    - Maindeck rate is only 1–7%, against peers at about 17%, so players treated them as sideboard cards.
- **FRA's cycle does nothing in dead games** but hits two colours.
  - With the production model, a counterfactual version of each card without the colour restriction is predicted only 0–0.9pp higher than the real card. The model barely prices the restriction.
  - Rough mixture: 0.75 × prediction without the restriction + 0.25 × a blank card (−9pp vs set mean; −7 to −12 as a range). This gives −1.0 to −1.7pp versus the FRA mean for the removal spells and −3.9pp for Precise Redaction.
  - Current forecasts are −1.8 to +0.8pp. See `fra_mixture.txt`.
