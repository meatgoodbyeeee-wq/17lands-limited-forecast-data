#!/usr/bin/env python3
"""Build the plan-1 judge inputs for the FRA cards that carry a set-context reference (+ 30 reference-free anchor cards), and validate raw answers.

  python3 g1_inputs.py inputs          # writes input/p1.txt, p2.txt, p3.txt and judge_cards.csv (no AI call is made here)
  python3 g1_inputs.py leakcheck       # the inputs contain no card name, set name, rarity word or 17Lands number
  python3 g1_inputs.py check [p1|p2|p3]   # validate raw/p*.txt (format, ranges, coverage) like research/c9_power_questions/check_raw.py
  python3 g1_inputs.py examples        # prints the SET INFO that Avengers Assemble! (MSH) and Chronicle of Victory (ECL) would receive
"""
import gzip, json, random, re, sys
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).resolve().parent
C9 = HERE.parent / 'c9_power_questions'
FIELDS = ['IMP', 'UNA', 'VAL', 'FLOOR', 'FLEX', 'PLAY', 'GRADE']
MAX = [4, 4, 4, 4, 3, 4, 10]
LINE = re.compile(r'^(\d+)((?: \d+){7})\s*$')
PASSES = ['p1', 'p2', 'p3']
N_ANCHOR, SEED = 30, 20261023
MAX_REFS = 3
MIN_MK = 3          # the 'other cards also make such tokens' sentence is printed only when at least 3 other cards do


def pct(a, b):
    return f'{100 * a / b:.0f}%' if b else '0%'


def render(r):
    """One SET INFO line for one reference row (pure formatting of counted numbers)."""
    k, lab = r.kind, r.label
    cu = f'{int(r.n_match_cu)} of {int(r.n_den_cu)} at common/uncommon'
    if k == 'ctype':
        s = (f'"{lab}" creatures: {int(r.n_match)} of {int(r.n_den)} creature cards in the set ({pct(r.n_match, r.n_den)}), {cu}. '
             f'A typical deck that can play this card has about {r.exp_in_deck:.1f} of its 15 creatures of this type.')
        if r.n_mk >= MIN_MK:
            s += f' {int(r.n_mk)} other cards also make such creature tokens (counting them, about {r.exp_incl_mk:.1f} of the 23 spells).'
        return s
    if k == 'chosen_type':
        t = lab.split('best type ')[1]
        return (f'the creature type is chosen when the card is played: the best type for this card\'s colours has {int(r.n_match)} of {int(r.n_den)} '
                f'creature cards in the set ({pct(r.n_match, r.n_den)}), {cu}; in its best two-colour pair a deck built around that type has about '
                f'{r.exp_in_deck:.1f} of its 15 creatures of one type (best case; an ordinary deck has fewer).')
    if k == 'keyword':
        kw, scope = lab.split('|')
        if scope == 'creature':
            return (f'creatures with {kw}: {int(r.n_match)} of {int(r.n_den)} creature cards in the set ({pct(r.n_match, r.n_den)}), {cu}. '
                    f'A typical deck that can play this card has about {r.exp_in_deck:.1f} of its 15 creatures with {kw}.')
        return (f'cards with {kw}: {int(r.n_match)} of {int(r.n_den)} nonland cards in the set ({pct(r.n_match, r.n_den)}), {cu}. '
                f'A typical deck has about {r.exp_in_deck:.1f} of its 23 spells with {kw}.')
    name = {'noncreature': 'noncreature spells', 'legendary': 'legendary (nonland) cards', 'sorcery': 'sorcery cards', 'instant': 'instant cards'}.get(lab, f'{lab} cards')
    if k == 'nc_sub':
        name = f'{lab} cards (including cards that make one)'
    s = (f'{name}: {int(r.n_match)} of {int(r.n_den)} nonland cards in the set ({pct(r.n_match, r.n_den)}), {cu}. '
         f'A typical deck that can play this card has about {r.exp_in_deck:.1f} of its 23 spells like this.')
    if r.n_mk >= MIN_MK:
        s += f' {int(r.n_mk)} other cards also make such tokens (counting them, about {r.exp_incl_mk:.1f} of the 23 spells).'
    return s


def card_block(row, refs):
    head = f'#{row.id} | MV {row.mv} {row.colors or "C"} | {row.type_line}' + (f' | {row.pt}' if row.pt else '')
    lines = [head, row.btext]
    for r in refs:
        lines.append('SET INFO: ' + render(r))
    return '\n'.join(lines)


def support_refs(R, key):
    g = R[(R.key == key) & (R.role == 'support')]
    return list(g.drop_duplicates(['kind', 'label']).head(MAX_REFS).itertuples())


def build():
    u = pd.read_csv(C9 / 'cards.csv.gz', keep_default_na=False)
    R = pd.read_csv(HERE / 'refs.csv.gz')
    rows = []
    for r in u.itertuples():
        for k in str(r.keys).split(';'):
            if k.startswith('FRA|'):
                rows.append((k, r))
    fra_cards = {}
    for k, r in rows:
        fra_cards.setdefault(r.id, (k, r))          # one entry per unique card text (id)
    have = {}
    for cid, (k, r) in fra_cards.items():
        if r.auto == 1:
            continue
        have[cid] = (k, r, support_refs(R, k))
    ref_ids = sorted(c for c, v in have.items() if v[2])
    non = sorted(c for c, v in have.items() if not v[2])
    anchors = sorted(random.Random(SEED).sample(non, N_ANCHOR))
    ids = sorted(ref_ids + anchors)
    blocks = {c: card_block(have[c][1], have[c][2]) for c in ids}
    pd.DataFrame({'id': ids, 'key': [have[c][0] for c in ids], 'is_anchor': [int(c in anchors) for c in ids],
                  'n_info': [len(have[c][2]) for c in ids]}).to_csv(HERE / 'judge_cards.csv', index=False)
    (HERE / 'input').mkdir(exist_ok=True)
    for i, p in enumerate(PASSES):
        order = list(ids)
        if p == 'p2':
            order = order[::-1]
        elif p == 'p3':
            random.Random(SEED + 3).shuffle(order)
        (HERE / 'input' / f'{p}.txt').write_text('\n\n'.join(blocks[c] for c in order) + f'\n-- pass {p}: {len(order)} cards\n')
    print(f'FRA unique card texts {len(fra_cards)}, with text {len(have)}, with a support reference {len(ref_ids)}, anchors {len(anchors)}, inputs {len(ids)} cards')


def load_raw(p):
    out, errors = {}, []
    f = HERE / 'raw' / f'{p}.txt'
    if not f.exists():
        return out, [f'{f} missing']
    for n, line in enumerate(f.read_text().splitlines(), 1):
        if not line.strip():
            continue
        m = LINE.match(line.strip())
        if not m:
            errors.append(f'{p}:{n} bad format: {line!r}'); continue
        v = [int(x) for x in m.group(2).split()]
        if any(x < 0 or x > mx for x, mx in zip(v, MAX)):
            errors.append(f'{p}:{n} out of range: {line!r}'); continue
        cid = int(m.group(1))
        if cid in out:
            errors.append(f'{p}:{n} duplicate id {cid}')
        out[cid] = v
    return out, errors


def check(passes):
    need = set(pd.read_csv(HERE / 'judge_cards.csv')['id'])
    bad = False
    for p in passes:
        raw, errors = load_raw(p)
        miss, extra = sorted(need - set(raw)), sorted(set(raw) - need)
        print(f'{p}: cards {len(need)}, answered {len(raw)}, missing {len(miss)}, extra {len(extra)}, format errors {len(errors)}')
        for e in errors[:10]:
            print('  ', e)
        bad |= bool(errors or miss or extra)
    return 1 if bad else 0


def leakcheck():
    names = [c['name'] for c in json.loads(gzip.open(HERE.parents[2].parent / 'limited-forecast-pages/data/target.json.gz', 'rt', encoding='utf-8').read())['cards']] \
        if (HERE.parents[2].parent / 'limited-forecast-pages/data/target.json.gz').exists() else []
    bad = 0
    for p in PASSES:
        t = (HERE / 'input' / f'{p}.txt').read_text()
        hits = [n for n in names if len(n) > 4 and n in t]
        pats = re.findall(r'\b(?:FRA|Reality Fracture|common|uncommon|rare|mythic|GIH|WR|ALSA|17Lands|win rate)\b', t, re.I)
        # "common/uncommon" inside SET INFO is a count label, not a rarity of the card: allowed
        pats = [x for x in pats if x.lower() not in ('common', 'uncommon')]
        print(p, 'card-name hits', hits[:5], 'other hits', pats[:5])
        bad += len(hits) + len(pats)
    return 1 if bad else 0


def examples():
    R = pd.read_csv(HERE / 'refs.csv.gz')
    u = pd.read_csv(C9 / 'cards.csv.gz', keep_default_na=False)
    for key in ['MSH|Avengers Assemble!', 'ECL|Chronicle of Victory']:
        r = [x for x in u.itertuples() if key in str(x.keys).split(';')][0]
        print(card_block(r, support_refs(R, key)), '\n')


if __name__ == '__main__':
    c = sys.argv[1]
    if c == 'inputs':
        build()
    elif c == 'check':
        sys.exit(check(sys.argv[2:] or PASSES))
    elif c == 'leakcheck':
        sys.exit(leakcheck())
    elif c == 'examples':
        examples()
