#!/usr/bin/env python3
"""FIN card features and texts from Scryfall only (no 17Lands data). Runs in Actions (fin_final_cards.yml).

Uses build_dev_features.fetch_set unchanged, so the columns match the research feature tables.
Writes data/fin_scryfall_features.csv.gz (all FIN cards) and data/fin_cards_text.csv.gz (text columns for blind C3).
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "scripts"))
import build_dev_features as b  # noqa: E402

TEXT_COLS = ["set", "name", "type_line", "oracle_text", "mv", "power", "toughness"] + [f"color_{c}" for c in "WUBRG"]


def main():
    f = b.fetch_set("FIN")
    f["set"] = "FIN"
    f["is_supplemental_power_set"] = 0
    f["is_premier_set"] = 1
    out = HERE / "data"
    out.mkdir(parents=True, exist_ok=True)
    f.to_csv(out / "fin_scryfall_features.csv.gz", index=False, compression="gzip")
    f[TEXT_COLS].to_csv(out / "fin_cards_text.csv.gz", index=False, compression="gzip")
    print("FIN Scryfall cards", len(f), "columns", len(f.columns))


if __name__ == "__main__":
    main()
