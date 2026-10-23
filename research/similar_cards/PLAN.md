# Similar-card selection: evaluation plan (pre-registered 2026-10-22, before any variant is scored)

Goal: choose how the site's "past similar cards" (3 per card, display only, never a model input) are picked.
Data: the 28-set training pool (research/c9_power_questions c9.load_pool, labels C3-C5, C9 means), actual 28-day GIH WR. No FRA/TRK/FIN/MH3 outcomes, no human evaluations.

Quality measure (outcome is used only to score a method, never to build a similarity):
for every pool card, take its top-3 neighbours among cards of OTHER sets; error = |mean(neighbour GIH) - own GIH| after subtracting each set's mean GIH. Cards/neighbours need GIH games >= 3000.
Also reported: Pearson r of that pair, share of neighbours with the same card class (land / creature / noncreature spell), mean |mana value diff|.

Variants (cosine similarity on L2-normalised blocks, weights text:basic:label):
 T   rules-text TF-IDF + type words + basic numbers (approximation of the current method, 1 : 0.5 : 0)
 TL  + AI labels (C3-C5, C9 means) 1 : 0.5 : 1
 L   labels dominate 0.5 : 0.5 : 1
 LL  labels only + basic numbers 0 : 0.5 : 1
 each with and without hard filters (same land/non-land, same creature/non-creature, |mv diff| <= 2)
 and the production method as run by the site code on its 22-set reference list (other sets only).
Rule: adopt the variant with the lowest mean error; if two are within 0.05 pp take the one with the higher same-class share.
Candidates: all 28 sets if that variant wins in the 28-set pool; otherwise the 22 sets. Display needs ALSA and Scryfall links, which the 6 extra sets lack until the reference build is extended.

## Addendum (2026-10-22, after the first run and before the second): production similarity is the real baseline
The first run's text-only variant T is a weaker stand-in than the production vector (production scores better than T on the same cards),
so the decision is made against production itself: eval2.py scores the site's own similarity (node dump of lib/predict.mjs, 22-set list, other sets only)
against production + w x (cosine of the standardised AI-label block), w in {0, .25, .5, 1, 2}, with and without the hard filters. Same rule as above.
