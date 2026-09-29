#!/usr/bin/env python3
"""Validate raw extraction files against the queue (format, ranges, coverage)."""
import re
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
MAX = [3, 2, 3, 3, 2, 1, 3, 2, 1, 1]  # R S B C P M D X T K
DEPS = set("-TGAESKCLXHMO")
LINE = re.compile(r"^(\d+) ([0-9]{10}) (\S)$")


def load_raw():
    out = {}
    errors = []
    for f in sorted((HERE / "raw").glob("b*.txt")):
        for n, line in enumerate(f.read_text().splitlines(), 1):
            if not line.strip():
                continue
            m = LINE.match(line.strip())
            if not m:
                errors.append(f"{f.name}:{n} bad format: {line!r}")
                continue
            i, digits, dep = int(m.group(1)), m.group(2), m.group(3)
            vals = [int(c) for c in digits]
            if any(v > mx for v, mx in zip(vals, MAX)):
                errors.append(f"{f.name}:{n} out of range: {line}")
            if dep not in DEPS:
                errors.append(f"{f.name}:{n} bad dep: {line}")
            if i in out:
                errors.append(f"{f.name}:{n} duplicate id {i}")
            out[i] = (vals, dep)
    return out, errors


if __name__ == "__main__":
    u = pd.read_csv(HERE / "cards.csv.gz", keep_default_na=False)
    raw, errors = load_raw()
    todo = set(u.loc[u["auto"] == 0, "id"])
    extra = set(raw) - todo
    missing = sorted(todo - set(raw))
    for e in errors[:50]:
        print(e)
    print(f"annotated {len(raw)} / {len(todo)}; errors {len(errors)}; ids not in queue {sorted(extra)[:20]}")
    if len(sys.argv) > 1 and sys.argv[1] == "--missing":
        q = u[u["auto"] == 0].reset_index(drop=True)
        pos = {i: k // 150 for k, i in enumerate(q["id"])}
        by = {}
        for i in missing:
            by.setdefault(pos[i], []).append(i)
        print({b: len(v) for b, v in sorted(by.items())})
