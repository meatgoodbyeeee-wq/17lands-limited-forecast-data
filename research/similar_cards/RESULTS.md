# Similar-card selection (2026-10-22)

Pre-registered in PLAN.md (and its addendum) before scoring. Display only: nothing here feeds a forecast; no FRA/TRK/FIN/MH3 outcomes, no human evaluations.

## Step 1 (eval.py, 28-set pool, neighbours from other sets, GIH centred per set, >= 3000 games)
Mean |mean(top-3 neighbour GIH) - own GIH| in pp: random 3.08; text TF-IDF + basics (T) 2.61; + AI labels (TL) 2.43; labels-led (L) 2.41; labels only (LL) 2.41. Pearson 0.34 -> 0.47.
T was a weaker stand-in than the production vector (production beat T on the same cards), so the decision was made against production (addendum).

## Step 2 (eval2.py, production similarity from the site code, 22-set list, 4,919 cards)
| variant | filters | mean error pp | Pearson | same class | mean mv diff |
|---|---|---|---|---|---|
| production | no | 2.437 | 0.478 | 0.991 | 0.759 |
| production | yes | 2.448 | 0.471 | 1.000 | 0.688 |
| production + 0.25 x labels | yes | 2.356 | 0.516 | 1.000 | 0.712 |
| **production + 0.5 x labels** | **yes** | **2.351** | **0.514** | **1.000** | **0.727** |
| production + 0.5 x labels | no | 2.342 | 0.522 | 0.977 | 0.826 |
| production + 1 x labels | yes | 2.382 | 0.504 | 1.000 | 0.728 |
| labels only | yes | 2.552 | 0.418 | 1.000 | 0.764 |

Rule (lowest error; within 0.05 pp take the higher same-class share): production + 0.5 x labels with the hard filters. Gain over production: about 0.09 pp (4%), modest.
Candidates stay the 22-set list: the 6 extra sets lack ALSA and Scryfall links until the reference build is extended (the 28-set pool gave about 0.04 pp more in the labels-only test).
Implementation: data/similar-labels.json.gz (export_labels.py), lib/predict.mjs similarCardsLabelled; FRA recomputed with scripts/recompute-similar.mjs (predictions unchanged, checked field by field).
