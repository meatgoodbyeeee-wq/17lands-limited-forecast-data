# Colour-hoser mixture adjustment: pre-registered backtest

This is research only: Pages does not change. This plan is committed before any counterfactual prediction is made.
Background: `research/hoser_metrics/NOTES.md`.
- The production model barely prices "works only against colour X".
- Historical hosers win about 4.2pp more when the opponent plays a target colour ("live") than when not ("dead").
- A hoser's overall GIH WR depends on what it does in dead games.

## Method
A card with a colour condition is predicted as a mixture of two versions of itself:

```
pred = s(k) × pred(live version) + (1 − s(k)) × pred(dead version)
```

- **`s(k)`, the share of games in which the opponent plays a target colour.** It is fixed by counting, not fitted.
  In a two-colour format, s(k) = 1 − C(5−k, 2) / C(5, 2), which gives **0.4 for one target colour and 0.7 for two**.
  The observed shares were AFR 0.40, SNC 0.56 (SNC decks often had three colours) and MOM 0.75.
- **`pred(...)`: the production model unchanged** (28 sets + C3, 3 seeds averaged). It is run on edited card text.
  - Features are rebuilt with `card_features` from the edited text, cost and mana value.
  - The C3 codes start from the card's own extraction; only the fields listed below change, following the rubric.
- **Bonus type** (the card works on anything and is better against the target colour): the dead version is the card without the bonus.
- **Only type** (the card does nothing against other colours; the FRA cycle): the dead version is a blank card, worth **set predicted mean − 8.61pp**.
  - 8.61pp is the mean dead-game GIH WR, against the set mean, of the four historical hosers with weak base effects (Change the Equation −7.00, Glistening Deluge −8.84, Lithomantic Barrage −6.17, Divine Smite −12.43).
  - A true blank is probably at least that bad.

## Backtest (bonus type; the 15 historical hosers)
Each set's five cards are predicted by models trained on the other 27 sets, the same folds as `research/production_c3/oof_28set.csv.gz`.
The current prediction is the model on the real text, in the same run.

| card | k | live version | dead version | C3 change (live / dead) |
|---|---|---|---|---|
| AFR Burning Hands | 1 | 6 damage to target creature or planeswalker | 2 damage | R2 / R1 |
| AFR Divine Smite | 1 | exile target creature or planeswalker an opponent controls | it phases out | R2 / R1 |
| AFR Hunter's Mark | 1 | costs {G} (mana value 1), no cost sentence | costs {3}{G} (mana value 4), no cost sentence | — |
| AFR Ray of Enfeeblement | 1 | −4/−4 | −4/−1 | R2 / R1 |
| AFR Ray of Frost | 1 | enters: tap it; it loses all abilities; it doesn't untap | only "doesn't untap" | R2 / R1 |
| SNC Bouncer's Beatdown | 1 | costs {G} (1), no cost sentence | costs {2}{G} (3) | — |
| SNC Knockout Blow | 1 | costs {W} (1) | costs {2}{W} (3) | — |
| SNC Out of the Way | 1 | costs {1}{U} (2) | costs {3}{U} (4) | — |
| SNC Torch Breath | 1 | deals X plus 2 damage | deals X damage | — |
| SNC Whack | 1 | costs {B} (1) | costs {3}{B} (4) | — |
| MOM Change the Equation | 2 | second mode counters any spell with mana value ≤ 6 | only "counter target spell with mana value 2 or less" | — / M0 |
| MOM Glistening Deluge | 2 | all creatures −1/−1, and creatures your opponents control an additional −2/−2 | all creatures −1/−1 | R3 S2 / R1 S1 |
| MOM Lithomantic Barrage | 2 | 5 damage | 1 damage | R2 / R1 |
| MOM Sandstalker Moloch | 2 | flash; enters: look at the top four cards, take a permanent (no condition) | flash only | C1 D0 / C0 D0 |
| MOM Surge of Salvation | 2 | hexproof, and prevent damage from sources your opponents control to your creatures | hexproof only | — |

**Rule H.** The mixture adjustment for the bonus type is supported if both hold:
1. MAE over the 15 cards (actual 28-day GIH WR) is lower than the current prediction's.
2. Set-level MAE over each set's five cards is lower in at least 2 of the 3 sets.

The following are reported but do not enter the decision:
- mean signed error
- the live-only and dead-only predictions
- within-set MAE and Spearman of AFR, SNC and MOM with the five adjusted cards swapped in

## FRA (only type)
The FRA predictions for the five cards (Essence Burn, Flourishing Grapple, Refute Destiny, Precise Redaction, Terminal Criticism) are frozen in this run:
- s = 0.7.
- The unrestricted version drops the colour condition. C3 changes: R2 for Essence Burn, Refute Destiny and Terminal Criticism; R1 stays for Flourishing Grapple (bite) and Precise Redaction (counterspell).

They are compared with the current forecasts once the FRA Public Game Data is available.
Whether the site uses them is the user's decision after Rule H. FIN, MH3 and FRA outcomes are not used.
