#!/usr/bin/env python3
"""Print groups a..b (1-based gid numbers) blinded, labels A.. ; set name hidden."""
import json, sys
from pathlib import Path
import pandas as pd
HERE = Path(__file__).resolve().parent
g = json.loads((HERE / "groups.json").read_text())
d = pd.read_csv(HERE / "cards_blind.csv.gz", keep_default_na=False).set_index("key")
a, b = int(sys.argv[1]), int(sys.argv[2])
for grp in g[a - 1:b]:
    print(f"== {grp['gid']}")
    for lab, k in zip("ABCDEFGHIJKLMNOP", grp["keys"]):
        r = d.loc[k]
        print(f"{lab}| {r.mv} {r.colors or 'C'} | {r.type_line}{' | ' + r.pt if r.pt else ''} | {r.text.replace(chr(10), ' / ')}")
