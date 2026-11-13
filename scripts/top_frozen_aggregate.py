#!/usr/bin/env python3
"""Aggregate the public game data of a set whose top-player forecast is already frozen (TP3 stage 2).

Same aggregation as skill_compare_aggregate.py (which refuses FRA and TRK). This wrapper lifts the refusal only for a set
that has a frozen forecast file in research/top_player/tp3/frozen/ whose sha256 matches frozen.json, so the order
"freeze first, then look at the outcome" is enforced by the code.
  python3 scripts/top_frozen_aggregate.py --set FRA --out-dir research/top_player/tp3/actual [--local-file mock.csv.gz]
"""
import hashlib, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
FROZEN = HERE.parent / "research" / "top_player" / "tp3" / "frozen"
ALLOWED = {"FRA", "TRK"}


def check_frozen(code, frozen_dir=FROZEN):
    meta = json.loads((Path(frozen_dir) / "frozen.json").read_text())["sets"]
    if code not in ALLOWED or code not in meta:
        raise SystemExit(f"{code}: no frozen top-player forecast, refusing to aggregate")
    f = Path(frozen_dir) / meta[code]["file"]
    if hashlib.sha256(f.read_bytes()).hexdigest() != meta[code]["sha256"]:
        raise SystemExit(f"{code}: frozen file does not match frozen.json, refusing to aggregate")
    return meta[code]


def main():
    code = sys.argv[sys.argv.index("--set") + 1].upper()
    check_frozen(code)
    sys.path.insert(0, str(HERE))
    import skill_compare_aggregate as m
    m.REFUSE = set(m.REFUSE) - {code}
    m.main()


if __name__ == "__main__":
    main()
