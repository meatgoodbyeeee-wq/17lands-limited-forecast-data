#!/usr/bin/env python3
"""Validate C5 raw files against the queue (format, ranges, coverage)."""
import re, sys
from pathlib import Path
import pandas as pd

HERE = Path(__file__).resolve().parent
TAGS = "KD KX DM DA MS BN TP FT ED CS PA SW DR SC RC TU IM TK CL PC PT PP AN CP EQ FL MN FS DT LL HS VG RH IN FH DS ST MI DL TX RM FX CR SK CY ET AT DY UP SP LD SA CH KC RE SE DW CD RN SD".split()
LINE = re.compile(r"^(\d+) ([0-4]) ([0-3]) ([0-3]) \|(.*)$")


def parse(line):
    m = LINE.match(line.strip())
    if not m:
        return None, f"bad format: {line!r}"
    tags, seen = {}, set()
    for tk in m.group(5).split():
        mt = re.fullmatch(r"([A-Z]{2})([12])", tk)
        if not mt or mt.group(1) not in TAGS:
            return None, f"bad tag {tk!r}: {line!r}"
        if mt.group(1) in seen:
            return None, f"duplicate tag {tk!r}: {line!r}"
        seen.add(mt.group(1)); tags[mt.group(1)] = int(mt.group(2))
    return (int(m.group(1)), [int(m.group(2)), int(m.group(3)), int(m.group(4))], tags), None


def load_raw():
    out, errors = {}, []
    for f in sorted((HERE / "raw").glob("b*.txt")):
        for n, line in enumerate(f.read_text().splitlines(), 1):
            if not line.strip():
                continue
            r, err = parse(line)
            if err:
                errors.append(f"{f.name}:{n} {err}"); continue
            if r[0] in out:
                errors.append(f"{f.name}:{n} duplicate id {r[0]}")
            out[r[0]] = (r[1], r[2])
    return out, errors


if __name__ == "__main__":
    u = pd.read_csv(HERE / "cards.csv.gz", keep_default_na=False)
    raw, errors = load_raw()
    need = set(u.loc[u["auto"] == 0, "id"])
    miss, extra = sorted(need - set(raw)), sorted(set(raw) - need)
    print(f"cards to extract {len(need)}, extracted {len(raw)}, missing {len(miss)}, extra {len(extra)}, format errors {len(errors)}")
    for e in errors[:20]:
        print(e)
    sys.exit(1 if errors or miss or extra else 0)
