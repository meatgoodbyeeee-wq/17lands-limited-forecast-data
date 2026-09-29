# Production export: final GIH model (28 sets + C3)

On 2026-09-29 the user adopted the final candidate confirmed by the FIN check in `research/fin_final` (Rule F).
This folder produces the Pages files for it.

- **Model:** the adopted GIH model is unchanged: ET 70% + TF-IDF/Ridge 30%, ×1.25 around the training mean.
  - Features: the baseline plus C3 (`research/gih_llm_extract`).
  - Training sets: the 21 research sets plus EOE, TLA, ECL, TMT, SOS, MSH and HOB.
  - FIN, MH3 and FRA outcomes are not used.
  - Seeds 20260922–24 are averaged.
- **Pages files:**
  - `data/adopted-gih-fra.json.gz`: FRA predictions. The explanation split into structured part and text part is the same as before.
  - `data/gih-range-fra.json`: per-card 80% ranges. The method (M5 in `research/gih_interval`) is unchanged; it is refit on this model's 28-set out-of-fold residuals.
- **Out-of-fold check (28 sets, LOSO; `oof_metrics.json`):** within-set MAE 2.396pp, Spearman 0.562.
- **Range check (`range_loso.json`):**
  - LOSO coverage is 80.0% overall, and 78.6–80.2% by rarity.
  - Mean width is 7.67pp; the previous model's range was 7.99pp wide.
  - q = 1.5905.

```
python export_gih_c3_28set.py oof
python export_gih_c3_28set.py adopted --fra <pages>/data/target.json.gz --out <pages>/data/adopted-gih-fra.json.gz
python export_gih_c3_28set.py range --fra <pages>/data/target.json.gz --adopted <pages>/data/adopted-gih-fra.json.gz --out <pages>/data/gih-range-fra.json
```

Each new set needs the blind C3 extraction of its cards, done before release, and then a re-export.
The previous production model was trained on 22 sets including MH3, without C3 (`gih-github-22set-ensemble-20260923`).
