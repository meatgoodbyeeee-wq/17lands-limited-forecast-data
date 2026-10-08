# C9: how strong is the card — power judgement broken into questions, three independent passes — pre-registered (Rule F10)

Research only; Pages and production unchanged. Written before any C9 extraction. FIN, MH3, FRA outcomes are not used.

## Why
B5's error is about 80% card-specific (sampling noise 3.5%, set offset 5%, set × colour 7–9%); 28% of cards miss by more than 3 pp and make 58% of the absolute error; errors grow with card complexity (1.2 pp for cards without tags, 3.8 pp with 7 tags) and are not tied to particular effect types. C3–C5 describe WHAT a card does; only C5's three coarse scales (rate, clock, defence) say how strong. C9 asks how strong, broken into concrete questions, and asks three times independently to average out labelling noise.

## Extraction
Same blinded queue as C5 (7,010 unique card texts of the 28 production sets + 290 FRA cards, names as "~", no set, rarity or 17Lands numbers), 47 batches. Seven integers per card (`RUBRIC.md`): IMP immediate impact 0–4, UNA impact if unanswered 0–4, VAL card value 0–4, FLOOR worst case 0–4, FLEX flexibility 0–3, PLAY main-deck playability 0–4, GRADE overall Limited grade 0–10. Three passes p1, p2, p3 by different labelling agents; each pass sees the cards of a batch in a different order (as given, reversed, shuffled); no agent labels the same batch twice and no agent sees another pass. `check_raw.py` validates format, ranges, coverage. Caveat as before: the labeller may know historical cards; FRA is the clean test.

## Features (17 columns, no tuning)
Per card: the mean over the three passes of each of the 7 answers (7), the standard deviation over passes of each answer (7; disagreement as a signal of a hard-to-judge card), and 3 summaries of the means: IMP+UNA, VAL+FLOOR, GRADE − 1.25·PLAY (grade beyond playability, a bomb indicator). Cards with no text get the neutral values of the scale middles and sd 0.

## Arms (28 sets, leave one set out, production model ET 70% + TF-IDF/Ridge 30%, ×1.25, seeds 20260922–24)
- B5 = A + C4 + C5 (2.2918 pp, Spearman 0.6061), the current best.
- **B10 = B5 + the 17 C9 columns** (3 seeds). Candidate for the decision is B10 vs B5.
- Reported only (1 seed): B5 + pass-1 answers only (7 columns; the value of averaging); B5 + means only (7); A + C9 means without C4/C5 (7).
- Reported: inter-pass agreement (Spearman between passes for each answer), MAE by rarity and by C5 tag count.

## Rule F10 (B10 vs B5)
Supported if (1) pooled MAE lower, (2) mean within-set Spearman higher, (3) lower MAE in ≥ 15 of 28 sets, (4) MAE gain > 0.01 pp. If supported: freeze FRA predictions of B10 next to A, B, B5 and add them to PENDING_FRA. Adoption is the user's decision.
