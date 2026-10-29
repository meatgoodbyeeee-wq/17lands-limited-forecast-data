"""G3 inputs for TRK (RESUME_PLAN_A.md Step 3).  python3 build_trk.py --run <preview|full> --cards <pages>/data/trk/target.json.gz   (deterministic)

--run keeps the two judgings apart: preview = provisional judging of the cards revealed so far (preview page only, user decision 2026-10-29),
full = the judging after every card is out (the forecast that is frozen). Each run has its own folder and key; export_b11g.py --g3-run picks one
and stops if the key does not match the current card list.
Judge folder TRK_<run>/: examples.txt (= the 858 expert-graded past cards every non-past training set saw, all/<SET>/examples.txt),
targets.txt (every non-automatic gallery card, same blinded card view as the training sets: name -> "~", no set or name).
Answer key keys_trk/TRK_<run>.csv (tid -> key, name) is NOT in the judge folder. MTGAZone's TRK review is not used (no expert grade for TRK).
Judging: 3 Opus passes, prompt_judge_trk.txt with {RUN} and {K} = 1, 2, 3 -> TRK_<run>/pass{K}.json. G3 for TRK = mean of the 3 passes
(training used 1 pass per set; documented in research/g3_retrain/PLAN.md).
Cards with an automatic label (basic lands, blank text) and cards marked as not in boosters are not judged; export_b11g.py gives them the set mean like training.
"""
import argparse, gzip, hashlib, json, sys
from pathlib import Path
import numpy as np, pandas as pd

H = Path(__file__).resolve().parent
R = H.parents[0]
sys.path.insert(0, str(R / 'trk_preview'))
import trk_label as t  # noqa: E402

KEYS = H / 'keys_trk'
RAR = {'common': 'C', 'land': 'C', 'uncommon': 'U', 'rare': 'R', 'mythic': 'M'}


def fmt(tag, rar, mv, col, typ, pt, txt):  # same as build.py
    return f"{tag} | {rar} | MV {mv} {col or 'C'} | {typ}{' | '+pt if pt else ''}\n{txt}"


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--cards', type=Path, required=True)
    ap.add_argument('--run', choices=['preview', 'full'], required=True)
    a = ap.parse_args()
    OUT = H / f'TRK_{a.run}'
    if any(OUT.glob('pass*.json')):
        raise SystemExit(f'{OUT.name} already has judge passes; move them away before rebuilding its inputs')
    gal = json.loads(gzip.open(a.cards, 'rt', encoding='utf-8').read())
    if not gal.get('complete'):
        print('warning: the gallery list is not marked complete', file=sys.stderr)
    q = pd.read_csv(t.LAB / 'cards.csv.gz', keep_default_na=False)
    byname = {}
    for r in q.itertuples():
        byname.setdefault(t.norm_name(r.name), r)
    miss = [c['name'] for c in gal['cards'] if t.norm_name(c['name']) not in byname]
    if miss:
        raise SystemExit(f'not in label/cards.csv.gz yet (run trk_label.py queue first): {miss[:20]}')
    seen, rows = set(), []
    for c in gal['cards']:
        r = byname[t.norm_name(c['name'])]
        if r.auto == 1 or c.get('booster') is False or t.norm_name(c['name']) in seen:
            continue
        seen.add(t.norm_name(c['name']))
        rows.append((c, r))
    ex = [H / 'all' / s / 'examples.txt' for s in ('AFR', 'KHM', 'MID')]
    if len({sha(p) for p in ex}) != 1:
        raise SystemExit('training examples differ between non-past sets')
    order = np.random.default_rng(3).permutation(len(rows))
    rows = [rows[i] for i in order]
    OUT.mkdir(exist_ok=True); KEYS.mkdir(exist_ok=True)
    (OUT / 'examples.txt').write_bytes(ex[0].read_bytes())
    (OUT / 'targets.txt').write_text('\n\n'.join(fmt(f'#T{i+1}', RAR[c['rarity']], r.mv, r.colors, r.type_line, r.pt, r.btext)
                                                for i, (c, r) in enumerate(rows)) + '\n')
    pd.DataFrame({'tid': [f'T{i+1}' for i in range(len(rows))], 'key': [r.key for _, r in rows], 'name': [c['name'] for c, _ in rows],
                  'rarity': [c['rarity'] for c, _ in rows]}).to_csv(KEYS / f'TRK_{a.run}.csv', index=False)
    meta = {'run': a.run, 'cards_file': str(a.cards.name), 'cards_retrieved_at': gal.get('retrieved_at'), 'cards_complete': bool(gal.get('complete')),
            'gallery_cards': len(gal['cards']), 'targets': len(rows), 'examples_sha256': sha(OUT / 'examples.txt'),
            'targets_sha256': sha(OUT / 'targets.txt')}
    json.dump(meta, open(KEYS / f'TRK_{a.run}.meta.json', 'w'), indent=1)
    print(json.dumps(meta))


if __name__ == '__main__':
    main()
