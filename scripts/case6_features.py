#!/usr/bin/env python3
"""Case 6: pre-release card features (Scryfall) for the post-TDM sets, joined to their case-6 aggregates.

Uses card_features / fetch_set from build_dev_features.py unchanged, so columns match data/features/dev_feature_22.csv.gz.
17Lands names that do not match a Scryfall name exactly are retried against the front face of double-faced cards.
FIN, MH3 and FRA are refused.
"""
import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_dev_features as b  # noqa: E402

REFUSE = {"FIN", "MH3", "FRA"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--aggregates", type=Path, required=True, help="directory with <SET>_case6_28d.csv")
    ap.add_argument("--sets", nargs="+", required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    sets = [s.upper() for s in a.sets]
    if set(sets) & REFUSE:
        raise SystemExit("refused set requested")
    frames, report = [], {}
    for s in sets:
        act = pd.read_csv(a.aggregates / f"{s}_case6_28d.csv").rename(columns={"card_name": "name", "gih_wr": "actual_gih"})
        feat = b.fetch_set(s)
        feat["front"] = feat["name"].str.split(" // ").str[0]
        exact = act.merge(feat.drop(columns=["front"]), on="name", how="inner")
        rest = act[~act["name"].isin(exact["name"])]
        f2 = feat[~feat["name"].isin(exact["name"])].drop_duplicates("front")
        front = rest.merge(f2.drop(columns=["name"]).rename(columns={"front": "name"}), on="name", how="inner")
        m = pd.concat([exact, front], ignore_index=True)
        report[s] = {"aggregate_cards": len(act), "matched_exact": len(exact), "matched_front_face": len(front),
                     "unmatched": sorted(set(act["name"]) - set(m["name"]))[:40]}
        print(s, report[s], flush=True)
        frames.append(m)
    out = pd.concat(frames, ignore_index=True)
    out["is_supplemental_power_set"] = 0
    out["is_premier_set"] = 1
    a.out.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(a.out, index=False, compression="gzip")
    # Text-only copy for blind C3 extraction (no outcome columns).
    text_cols = ["set", "name", "type_line", "oracle_text", "mv", "power", "toughness"] + [f"color_{c}" for c in "WUBRG"]
    out[text_cols].to_csv(a.out.parent / "new_cards_text.csv.gz", index=False, compression="gzip")
    (a.out.parent / "new_feature_match_report.json").write_text(pd.Series(report).to_json(indent=2))
    print("wrote", a.out, len(out))


if __name__ == "__main__":
    main()
