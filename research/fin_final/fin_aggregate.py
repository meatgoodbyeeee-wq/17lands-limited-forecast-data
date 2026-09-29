#!/usr/bin/env python3
"""FIN only: the same download and aggregation as scripts/case6_aggregate.py (which refuses FIN).

Used once, by fin_final_score.yml, after the plan, code and C3 extraction are committed.
Prints only counts (no card outcomes).
"""
import argparse
import json
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "scripts"))
import case6_aggregate as ca  # noqa: E402

SET = "FIN"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", type=Path, required=True)
    a = ap.parse_args()
    a.out_dir.mkdir(parents=True, exist_ok=True)
    raw = a.out_dir / f"game_data_public.{SET}.{ca.FMT}.csv.gz"
    ca.download(SET, raw)
    rows, man = ca.aggregate(SET, raw, 28, 500, 20000)
    pd.DataFrame(rows).to_csv(a.out_dir / f"{SET}_case6_28d.csv", index=False)
    (a.out_dir / f"{SET}_case6_manifest.json").write_text(json.dumps(man, indent=2))
    raw.unlink(missing_ok=True)
    print(json.dumps({"set": SET, "cards_output": man["cards_output"], "games": man["group_games"]["all"],
                      "window_start": man["window_start"], "last_draft_time_in_window": man["last_draft_time_in_window"]}))


if __name__ == "__main__":
    main()
