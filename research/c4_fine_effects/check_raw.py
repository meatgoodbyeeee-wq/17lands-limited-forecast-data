#!/usr/bin/env python3
"""Validate C4 raw files against the queue (format, ranges, coverage)."""
import re, sys
from pathlib import Path
import pandas as pd

HERE = Path(__file__).resolve().parent
MAX = [4, 4, 3, 4, 3, 3, 3, 2, 2, 2, 5, 2, 3, 2]
ROLES = set("ADVFRTSNO")
LINE = re.compile(r"^(\d+) ([0-9]{14}) ([A-Z])$")


def load_raw():
    out, errors = {}, []
    for f in sorted((HERE / "raw").glob("b*.txt")):
        for n, line in enumerate(f.read_text().splitlines(), 1):
            if not line.strip():
                continue
            m = LINE.match(line.strip())
            if not m:
                errors.append(f"{f.name}:{n} bad format: {line!r}"); continue
            i, d, role = int(m.group(1)), m.group(2), m.group(3)
            v = [int(c) for c in d]
            if any(a > b for a, b in zip(v, MAX)) or role not in ROLES:
                errors.append(f"{f.name}:{n} out of range: {line}")
            if i in out:
                errors.append(f"{f.name}:{n} duplicate id {i}")
            out[i] = (v, role)
    return out, errors


if __name__ == "__main__":
    u = pd.read_csv(HERE / "cards.csv.gz", keep_default_na=False)
    raw, errors = load_raw()
    need = set(u.loc[u["auto"] == 0, "id"])
    miss, extra = sorted(need - set(raw)), sorted(set(raw) - need)
    print(f"cards to extract {len(need)}, extracted {len(raw)}, missing {len(miss)}, extra {len(extra)}, format errors {len(errors)}")
    for e in errors[:20]:
        print(e)
    if miss:
        print("missing ids (first 20):", miss[:20])
    sys.exit(1 if errors or miss or extra else 0)
