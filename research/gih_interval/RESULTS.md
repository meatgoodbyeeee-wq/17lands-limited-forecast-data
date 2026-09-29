# GIH WR forecast range: results (2026-09-29)

Script: `gih_interval_research.py` (local run, frozen inputs only). FIN and MH3 not used. Point predictions unchanged.
Per-card LOSO ranges: `loso_ranges.csv.gz`. Full metrics: `compare.json`.

## Leave-one-set-out comparison (21 sets, 5,344 cards, nominal 80%)

| method | coverage | common | uncommon | rare | mythic | creature | spell | other perm. | land | mean width | interval score |
|---|---|---|---|---|---|---|---|---|---|---|---|
| M0 current ±3.684 | 0.777 | 0.885 | 0.769 | 0.644 | 0.599 | 0.799 | 0.760 | 0.639 | 0.962 | 7.37 | 11.88 |
| M1 global | 0.800 | 0.903 | 0.797 | 0.666 | 0.630 | 0.822 | 0.786 | 0.663 | 0.971 | 7.82 | 11.87 |
| M2 rarity | 0.801 | 0.800 | 0.800 | 0.802 | 0.805 | 0.834 | 0.738 | 0.702 | 0.971 | 7.98 | 11.39 |
| M3 rarity asym. | 0.797 | 0.794 | 0.799 | 0.798 | 0.794 | 0.829 | 0.734 | 0.697 | 0.974 | 7.95 | 11.43 |
| M4 rarity × type | 0.806 | 0.804 | 0.804 | 0.814 | 0.799 | 0.805 | 0.797 | 0.790 | 0.870 | 8.04 | 11.11 |
| **M5 normalized** | **0.802** | 0.805 | 0.805 | 0.796 | 0.791 | 0.810 | 0.794 | 0.795 | 0.791 | 7.99 | **11.00** |

Mean width by rarity for M5: common 6.0, uncommon 8.0, rare 10.5, mythic 11.8pp (current: 7.4 for all).
Per-set coverage still ranges about 0.69–0.87 for every method; that comes from set-level bias, which no range method here addresses.

## Verdict under the pre-registered rule (PLAN.md)
- Rule 1 (pooled 0.78–0.82): M1–M5 pass; M0 fails (0.777).
- Rule 2 (each rarity ±0.05): M2–M5 pass.
- Rule 3 (each type group ±0.07): only M5 passes. M4 misses on land (0.870, off by 0.0702).
- **Winner: M5.** It also has the lowest interval score (−7.5% vs current).

## What M5 learned
The |residual| model leans on rarity (importance 0.37), then land / creature / enchantment type, predicted value and mana value.
Widest ranges go to rare/mythic build-around enchantments and conditional spells; narrowest to basic lands and plain common creatures/removal.

## Export for FRA
`export_gih_range.py` fits M5 on all 21 sets (q = 1.6006) and writes `data/gih-range-fra.json` in the Pages repo:
one radius per FRA card (median 3.83pp, 2.02–8.41) and the M4 rarity × type table as the fallback when a card's text no longer matches.
FRA gallery text is normalized before feature building (curly apostrophes, CRLF and `{oX}` symbols → Scryfall style), because the training text is Scryfall style.
