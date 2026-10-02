# C4: finer card-effect features for GIH WR — pre-registered (Rule F)

Research only; Pages and production unchanged. Written before any extraction. FIN, MH3, FRA outcomes are not used.

## Why
C3's gain came from its 10 raw fields (removing them costs 0.032 pp); regrouping, composites and archetype labels add nothing (research/gih_archetype). The next gain must come from reading card effects in more detail. C4 adds fields the existing baseline features cannot see from keywords and regexes: removal magnitude/breadth/timing, immediate board stats, evasion class, when the card matters, how often the main effect is dead, scaling, tempo, vulnerability to being answered, number of independent effects, help to other cards, life swing, mana help, and a one-letter role.

## Extraction
Same procedure as C3: blinded (name → `~`, no set, no rarity, no 17Lands numbers), shuffled, 7,010 unique card texts of the 28 production sets plus the 290 FRA cards, extracted in 47 batches by blind labelling agents following `RUBRIC.md` exactly; format and range checked by `check_raw.py`. The extractor sees the text only. Caveat as before: the extractor knows these historical cards; FRA is the clean test.

## Features
14 integer fields (DMG TGT SPD SWG EVA TURN DEAD SCALE TEMPO VULN STACK SYNO DRAIN MANA) and 9 role one-hots (A D V F R T S N O) = 23 columns, no composites. Cards with no text are zeros.

## Arms (28 sets, leave one set out, production model ET 70% + TF-IDF/Ridge 30%, ×1.25, seeds 20260922–24)
- A: production (baseline + C3). B: baseline + C3 + C4 (23 columns).
Reported only: C4 groups (numbers only / roles only) and a C4-only-in-place-of-C3 arm (seed 20260922), importance of the 14 numeric fields.

## Rule F (B vs A)
Supported if (1) pooled MAE lower, (2) mean within-set Spearman higher, (3) lower MAE in ≥ 15 of 28 sets, (4) the MAE gain exceeds 0.01 pp.
If supported: freeze FRA predictions of B (3 seeds) next to production before FRA outcomes are used. Adoption is the user's decision.
