# X1: expert pre-release grades (MTGAZone set reviews) as a B10 feature — pre-registered 2026-10-26

Motivation: the B10 error is ~83% card-specific (within set, colour, rarity). On FRA, MTGAZone's
pre-release 0–5 grades had Spearman +0.36 with the B10 residual and a FRA-fitted leave-one-out
combination lowered MAE 2.21 → 2.02 (FRA-fitted, so only a signal check; FRA is NOT the test).

Data: MTGAZone "Limited Set Review" grades per card (0–5, 0.5 steps; SB/NA → missing), collected
by WebFetch (names + numbers only) into grades/<SET>.csv. Sets: whichever of the 28 OOF sets have
such reviews. Publication dates are recorded; reviews must predate the 17Lands data.

Model (per set s, coefficients fitted on the OTHER grade sets only):
  y = 100·(GIH − set mean), p = 100·(B10 − set mean of B10), g = grade − set mean of grade
  graded cards:   ŷ = a + b·p + c·g      (OLS on the other sets' graded cards)
  ungraded cards: ŷ = p                  (B10 unchanged)
Evaluated on all scored cards of s with the set mean added back (MAE on raw GIH, as for B10).

Pass (all): pooled MAE over the grade sets improves ≥ 0.05 pp vs B10; within-set Spearman higher;
MAE lower in ≥ 2/3 of the grade sets. Reported: per set, by rarity, top-10% under-prediction,
B10S comparison, and FRA scored with coefficients fitted on the past sets only (out of sample).
Caveats: one source/reviewer family; incomplete pages (noted per set); name matching by front face.

## Amendment before any past-set result was computed (2026-10-26)
Collection showed some sections were published on/after the 17Lands window start (e.g. DFT
02-11..02-25 vs window 02-11; FDN 11-04..11-16 vs 11-12; TDM 04-08..04-14 vs 04-08). Primary arm:
grades from a section published AFTER the set's window_start date are treated as missing (B10 used).
Same-day publication counts as pre-release. Reported arm: all grades regardless of date.
Window starts for sets without a manifest here are taken from the 17Lands public dataset dates
(release day) and listed in release_dates.json.
- OTJ (4 cards) and LCI (1 card) whose grade came from the tier list (possibly post-release) were removed from grades/.
