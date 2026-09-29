#!/usr/bin/env python3
"""Export the M5 GIH WR forecast range (winner under PLAN.md) for FRA Pages inference.

Fits on all 21 development sets' OOF residuals (no FIN, no MH3) and writes one radius per FRA card,
plus a rarity x type fallback table (M4) for cards whose preview text changes later.

Usage:
  python research/gih_interval/export_gih_range.py \
      --fra <pages>/data/target.json.gz --adopted-gih <pages>/data/adopted-gih-fra.json.gz \
      --out <pages>/data/gih-range-fra.json
"""
import argparse
import gzip
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "scripts"))
import gih_interval_research as g  # noqa: E402
from build_dev_features import card_features  # noqa: E402

VERSION = "gih-range-m5-21set-20260929"


def read_json(p: Path):
    return json.loads(gzip.open(p, "rt", encoding="utf-8").read() if p.suffix == ".gz" else p.read_text())


def symbols(m: re.Match) -> str:
    # Gallery "{o3oB}" / "{oT}" / "{o(g/w)}" -> Scryfall "{3}{B}" / "{T}" / "{G/W}"
    return "".join("{" + s.strip("()").upper() + "}" for s in m.group(1).split("o") if s)


def normalize(card: dict) -> dict:
    # Official gallery text uses curly apostrophes, CRLF and {oX} mana symbols; the Scryfall training text does not.
    c = dict(card)
    for k in ("oracle_text", "type_line", "name"):
        c[k] = re.sub(r"\{o([^}]*)\}", symbols, (c.get(k) or "").replace("’", "'").replace("\r\n", "\n"))
    if c.get("rarity") == "land":  # FRA land-slot cards; historical equivalents are Scryfall commons
        c["rarity"] = "common"
    return c


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fra", type=Path, required=True)
    ap.add_argument("--adopted-gih", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()

    d, cols = g.load()
    compare = json.loads((HERE / "compare.json").read_text())
    if compare["winner"] != "M5_normalized":
        raise SystemExit("compare.json winner is not M5; refusing to export")

    m5 = g.m5_fit(d, cols)          # q by set-grouped cross-fitting over all 21 sets, sigma model on all 21
    m4 = g.m4_fit(d, cols)          # fallback table

    fra = read_json(a.fra)["cards"]
    adopted = {c["id"]: c for c in read_json(a.adopted_gih)["cards"]}
    norm = [normalize(c) for c in fra]
    f = pd.DataFrame([card_features(c) for c in norm])
    f["pred_pp"] = [adopted[c["id"]]["gih"] for c in fra]
    if f["rarity_ord"].lt(0).any():
        raise SystemExit("unknown rarity in FRA cards")
    sigma = np.maximum(m5["model"].predict(f[cols]), g.SIGMA_FLOOR)
    radius = m5["q"] * sigma
    if len(radius) != len(fra) or not np.isfinite(radius).all() or not (radius > 0).all():
        raise SystemExit("invalid FRA radii")

    fallback = {}
    for rar in g.RARITY.values():
        fallback[rar] = {t: round(float(m4["cell"].get((rar, t), m4["rarity"][rar])), 4) for t in g.TYPES}

    loso = compare["methods"]["M5_normalized"]
    out = {
        "version": VERSION,
        "method": "M5 normalized conformal: ExtraTrees predicts |residual| of the adopted GIH model; range = pred ± q·sigma",
        "target_coverage": g.TARGET,
        "fin_used": False,
        "mh3_used": False,
        "training_sets": compare["sets"],
        "q": round(float(m5["q"]), 6),
        "sigma_floor": g.SIGMA_FLOOR,
        "loso": {k: loso[k] for k in ("coverage", "coverage_by_rarity", "coverage_by_type", "mean_width", "mean_interval_score")},
        "loso_current_fixed": {k: compare["methods"]["M0_current_fixed"][k] for k in ("coverage", "coverage_by_rarity", "coverage_by_type", "mean_width", "mean_interval_score")},
        "fallback_note": "M4 rarity x type radius (FRA 'land' rarity counts as common); used when a card's text no longer matches this file",
        "fallback": fallback,
        "cards": [
            {"id": c["id"], "name": c["name"], "oracle_text": c.get("oracle_text") or "", "type_line": c.get("type_line") or "",
             "mana_cost": c.get("mana_cost") or "", "radius": round(float(r), 4)}
            for c, r in zip(fra, radius)
        ],
    }
    a.out.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
    s = pd.Series(radius)
    print(json.dumps({"cards": len(radius), "q": out["q"], "radius_min": round(s.min(), 3), "radius_median": round(s.median(), 3),
                      "radius_max": round(s.max(), 3), "fin_used": False}))


if __name__ == "__main__":
    main()
