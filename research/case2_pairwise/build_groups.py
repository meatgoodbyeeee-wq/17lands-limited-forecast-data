#!/usr/bin/env python3
"""Build blinded ranking groups for HOB, MSH (case-6 evaluated cards) and FRA (Pages target)."""
import gzip, json, sys
from pathlib import Path
import numpy as np, pandas as pd
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "research/gih_llm_extract"))
from build_input import blind, fmt_num
import c3_research as c3
SEED, SIZE, REPS = 20261001, 8, 3

def cards():
    t = pd.read_csv(ROOT / "research/case6/data/new_cards_text.csv.gz", keep_default_na=False)
    o = pd.read_csv(ROOT / "research/case6/forward_oof.csv.gz")
    keep = set(zip(o.set, o.name))
    t = t[np.array([k in keep for k in zip(t.set, t.name)]) & t.set.isin(["HOB", "MSH"])].drop_duplicates(["set", "name"])
    rows = []
    for r in t.itertuples():
        col = "".join(c for c in "WUBRG" if str(getattr(r, f"color_{c}")) in ("1", "1.0"))
        pt = f"{fmt_num(r.power)}/{fmt_num(r.toughness)}"
        rows.append(dict(set=r.set, key=f"{r.set}|{r.name}", mv=fmt_num(r.mv), colors=col, type_line=r.type_line,
                         pt="" if pt == "/" else pt, text=blind(str(r.oracle_text), r.name, r.type_line)))
    fra = json.loads(gzip.open("/home/claude/limited-forecast-pages/data/target.json.gz", "rt").read())["cards"]
    for c in fra:
        n = c3.normalize(c)
        pt = f"{c.get('power') or ''}/{c.get('toughness') or ''}"
        rows.append(dict(set="FRA", key=f"FRA|{c['id']}", mv=fmt_num(c.get("cmc")), colors="".join(c.get("colors") or []),
                         type_line=n["type_line"], pt="" if pt == "/" else pt, text=blind(n["oracle_text"], n["name"], n["type_line"])))
    return pd.DataFrame(rows)

def main():
    d = cards()
    rng = np.random.default_rng(SEED)
    groups = []
    for s, g in d.groupby("set"):
        keys = g.key.tolist()
        for rep in range(REPS):
            p = [keys[i] for i in rng.permutation(len(keys))]
            chunks = [p[i:i + SIZE] for i in range(0, len(p), SIZE)]
            if len(chunks) > 1 and len(chunks[-1]) < SIZE:
                last = chunks.pop(); chunks[-1] = chunks[-1] + last
            groups += [(s, rep, ch) for ch in chunks]
    order = rng.permutation(len(groups))
    out = [{"gid": f"G{j+1:04d}", "set": groups[i][0], "rep": groups[i][1], "keys": groups[i][2]} for j, i in enumerate(order)]
    (HERE / "groups.json").write_text(json.dumps(out, indent=0))
    d.to_csv(HERE / "cards_blind.csv.gz", index=False, compression="gzip")
    print(len(d), d.groupby("set").size().to_dict(), "groups", len(out))

if __name__ == "__main__":
    main()
