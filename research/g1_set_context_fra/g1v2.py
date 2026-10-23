#!/usr/bin/env python3
"""G1 plan v2: choose the cards to re-judge, build the judge inputs (environment sheet + card-specific SET INFO), check them for leaks, estimate the size.
No AI call is made here, and no FRA outcome is read anywhere.

  python3 g1v2.py sample        # units.csv: FRA (all non-vanilla cards) + past-set sample (type-referencing cards + 300 stratified others)
  python3 g1v2.py inputs        # input_v2/p1|p2|p3/<SET>_<k>.txt and batches.csv
  python3 g1v2.py leakcheck     # no card name, set name/code, rarity word, 17Lands word, real mechanic name in any input
  python3 g1v2.py estimate      # number of judgements, batches, tokens
  python3 g1v2.py examples      # examples_v2/: FRA and MSH sheets, Avengers Assemble! and Chronicle of Victory card blocks
  python3 g1v2.py check [p1|p2|p3]   # validate raw_v2/<pass>/<batch>.txt answers
"""
import gzip, json, math, random, re, sys
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import env_sheet as es  # noqa: E402
import g1_inputs as g1  # noqa: E402  (render() of the plan-v1 density line; unchanged)
import sc_extract as sx  # noqa: E402

C9 = HERE.parent / 'c9_power_questions'
SEED, N_OTHER, MAX_BATCH = 20261023, 300, 60
PASSES = ['p1', 'p2', 'p3']
MAX_REFS, N_EX = 3, 3
FIELDS, MAX = g1.FIELDS, g1.MAX
SET_NAMES = {  # set names for the leak check (names that must never appear in an input)
    'AFR': 'Adventures in the Forgotten Realms', 'BLB': 'Bloomburrow', 'BRO': "The Brothers' War", 'DFT': 'Aetherdrift', 'DMU': 'Dominaria United',
    'DSK': 'Duskmourn', 'ECL': 'Lorwyn Eclipsed', 'EOE': 'Edge of Eternities', 'FDN': 'Foundations', 'FRA': 'Reality Fracture', 'HOB': 'Hobbit',
    'KHM': 'Kaldheim', 'LCI': 'Lost Caverns of Ixalan', 'LTR': 'Lord of the Rings', 'MID': 'Midnight Hunt', 'MKM': 'Murders at Karlov Manor',
    'MOM': 'March of the Machine', 'MSH': 'Marvel', 'NEO': 'Kamigawa: Neon Dynasty', 'ONE': 'Phyrexia: All Will Be One', 'OTJ': 'Outlaws of Thunder Junction',
    'SNC': 'Streets of New Capenna', 'SOS': 'Strixhaven', 'STX': 'Strixhaven', 'TDM': 'Tarkir: Dragonstorm', 'TLA': 'Avatar', 'TMT': 'Teenage Mutant Ninja Turtles',
    'VOW': 'Crimson Vow', 'WOE': 'Wilds of Eldraine'}


def past_pool():
    """The 28 production sets: key, set, rarity, old C9 GRADE (3-pass mean), actual GIH win rate. Cached (past-set data only)."""
    f = HERE / 'past_pool.csv.gz'
    if f.exists():
        return pd.read_csv(f)
    sys.path.insert(0, str(C9))
    import c9  # noqa: E402
    pool, _, _ = c9.load_pool()
    d = pool[['key', 'set', 'name', 'rarity_ord', 'actual_gih', 'gih_games', 'c9_m_GRADE', 'c9_s_GRADE', 'type_line']].copy()
    d.to_csv(f, index=False, compression='gzip')
    return d


def sample():
    s, infos = es.load()
    R = pd.read_csv(HERE / 'refs.csv.gz')
    cards = pd.read_csv(C9 / 'cards.csv.gz', keep_default_na=False)
    auto = {k for r in cards.itertuples() if r.auto == 1 for k in r.keys.split(';')}
    pool = past_pool()
    pool = pool[~pool.key.isin(auto) & ~pool.type_line.str.startswith('Basic')].copy()
    sup = R[R.role == 'support']
    tref = set(sup[sup.kind.isin(['ctype', 'chosen_type'])].key)
    pool['type_ref'] = pool.key.isin(tref)
    A = pool[pool.type_ref].copy()
    A['group'] = 'type_ref'
    rest = pool[~pool.type_ref].copy()
    rest['cell'] = rest.set + '|' + rest.rarity_ord.astype(str)
    cnt = rest.cell.value_counts()
    ex = cnt / cnt.sum() * N_OTHER
    alloc = ex.astype(int)
    for c in (ex - alloc).sort_values(ascending=False).index[:N_OTHER - alloc.sum()]:
        alloc[c] += 1
    rng = random.Random(SEED)
    pick = []
    for c in sorted(alloc.index):
        keys = sorted(rest[rest.cell == c].key)
        pick += rng.sample(keys, int(alloc[c]))
    B = rest[rest.key.isin(pick)].copy()
    B['group'] = 'other'
    past = pd.concat([A, B])
    # FRA: every card of the FRA list except the vanilla creatures (auto = no rules text; they keep the neutral default as before)
    fra = []
    for r in cards.itertuples():
        for k in r.keys.split(';'):
            if k.startswith('FRA|') and r.auto == 0:
                fra.append(dict(key=k, set='FRA', id=r.id, group='fra'))
    F = pd.DataFrame(fra)
    keep = ['key', 'set', 'group', 'rarity_ord', 'c9_m_GRADE', 'actual_gih']
    U = pd.concat([past[keep], F.reindex(columns=keep).assign(key=F.key, set='FRA', group='fra')], ignore_index=True)
    U = U.sort_values(['set', 'key']).reset_index(drop=True)
    U.insert(0, 'n', np.arange(1, len(U) + 1))
    # old (v1) GRADE for FRA from c9 features
    f = pd.read_csv(C9 / 'c9_features.csv.gz')[['key', 'c9_m_GRADE']].rename(columns={'c9_m_GRADE': 'old_grade'})
    U = U.drop(columns=['c9_m_GRADE']).merge(f, on='key', how='left')
    U = U.drop(columns=['actual_gih'])      # outcomes are joined only by the evaluation script, never here
    U.to_csv(HERE / 'units.csv', index=False)
    print(U.groupby('group').size().to_dict(), 'past sets', past['set'].nunique(), 'type-ref cards', int(A.shape[0]), 'other', int(B.shape[0]))
    print('sampling cells', len(alloc), 'rarity of other sample', B.rarity_ord.value_counts().sort_index().to_dict())


# ---------------------------------------------------------------- card-specific SET INFO (plan v1 lines + what the matching cards look like)
def match_vector(g, ginf, kind, label):
    if kind == 'ctype':
        return np.array([x['is_creature'] and (label in x['ctypes'] or x['changeling']) for x in ginf]), 'creature'
    if kind == 'keyword':
        k, scope = label.split('|')
        return np.array([k in x['kws'] or (k == 'changeling' and x['changeling']) for x in ginf]), scope
    if kind == 'cardtype':
        f = {'instant': lambda x: 'Instant' in x['cardtypes'], 'sorcery': lambda x: 'Sorcery' in x['cardtypes'], 'artifact': lambda x: 'Artifact' in x['cardtypes'],
             'enchantment': lambda x: 'Enchantment' in x['cardtypes'], 'planeswalker': lambda x: 'Planeswalker' in x['cardtypes'], 'legendary': lambda x: x['legendary'],
             'noncreature': lambda x: x['noncreature']}[label]
        return np.array([f(x) for x in ginf]), 'nonland'
    return np.array([label in x['nc_sub'] or label in x['mk_tokens'] for x in ginf]), 'nonland'


def short(t, n=230):
    t = re.sub(r'\s+', ' ', re.sub(r'\s*\n\s*', ' / ', t)).strip()
    return t if len(t) <= n else t[:n - 1] + '…'


def match_detail(g, ginf, r, neut, n_ex):
    """Contents of the cards that satisfy the condition of one reference (plan v2 section 4): MV curve, commons/uncommons, average P/T, three example texts."""
    kind, label = r.kind, r.label
    if kind == 'chosen_type':
        kind, label = 'ctype', label.split('best type ')[1]
    vec, scope = match_vector(g, ginf, kind, label)
    nonland = ~g.is_land.to_numpy()
    sel = vec & nonland & (g.is_creature.to_numpy() if scope == 'creature' else True) & (g.key.to_numpy() != r.key)
    m = g[sel]
    if not len(m):
        return 'MATCHING CARDS: none.'
    curve = ', '.join(f'MV{lab} {int((m.mvb == b).sum())}' for b, lab in zip(range(1, 7), ['<=1', '2', '3', '4', '5', '6+']) if (m.mvb == b).any())
    cu = m[m.cu]
    s = f'MATCHING CARDS ({len(m)}; commons+uncommons {len(cu)}): by mana value {curve}.'
    cr = m[m.is_creature & m.pw.notna()]
    if len(cr):
        crc = cr[cr.cu]
        s += f' Creatures among them: {len(m[m.is_creature])}, average power/toughness {es.f1(cr.pw.mean())}/{es.f1(cr.tg.mean())}' + \
             (f' (commons+uncommons only {es.f1(crc.pw.mean())}/{es.f1(crc.tg.mean())})' if len(crc) else '') + '.'
    if len(cu):
        order = cu.sort_values(['mv', 'rtext'])
        idx = sorted({0, len(order) // 2, len(order) - 1}) if n_ex >= 3 else sorted({0, len(order) - 1})
        ex = order.iloc[idx[:n_ex]]
        parts = [f'[MV {int(x.mv)} {x.colors or "C"} | {x.type.split("//")[0].strip()}{" | " + x.pt if x.pt else ""}] ' + short(neut(x.text)) for x in ex.itertuples()]
        s += ' Examples (a common/uncommon with the lowest, a middle and the highest mana value): ' + ' || '.join('"' + p + '"' for p in parts)
    return s


def card_block(c, refs, g, ginf, neut):
    head = f'#{c["n"]} | MV {c["mv"]} {c["colors"] or "C"} | {c["type_line"]}' + (f' | {c["pt"]}' if c['pt'] else '')
    lines = [head, neut(c['btext'])]
    n_ex = N_EX if len(refs) == 1 else 2
    for r in refs:
        lines.append('SET INFO: ' + g1.render(r))
        lines.append('  ' + match_detail(g, ginf, r, neut, n_ex))
    return '\n'.join(lines)


def load_all():
    s, infos = es.load()
    infos = dict(enumerate(infos))
    mechs = es.detect_mechanics(s)
    R = pd.read_csv(HERE / 'refs.csv.gz')
    cards = pd.read_csv(C9 / 'cards.csv.gz', keep_default_na=False)
    ck = {}
    for r in cards.itertuples():
        for k in r.keys.split(';'):
            ck[k] = r
    return s, infos, mechs, R, ck


def build_inputs():
    s, infos, mechs, R, ck = load_all()
    U = pd.read_csv(HERE / 'units.csv')
    sheets, neuts, ginfs, gs = {}, {}, {}, {}
    for st in sorted(U.set.unique()):
        txt, neut, *_ = es.build_sheet(st, s, infos, R, mechs)
        sheets[st], neuts[st] = txt, neut
        gs[st] = s[s.set == st].copy()
        gs[st]['text'] = [neut(t) for t in gs[st].text]
        gs[st]['rtext'] = [neut(t) for t in gs[st].rtext]
        ginfs[st] = [infos[i] for i in gs[st].index]
    blocks = {}
    for u in U.itertuples():
        c = ck[u.key]
        c = dict(n=u.n, mv=c.mv, colors=c.colors, type_line=c.type_line, pt=c.pt, btext=c.btext)
        refs = g1.support_refs(R, u.key)
        blocks[u.n] = card_block(c, refs, gs[u.set], ginfs[u.set], neuts[u.set])
    rows = []
    for p in PASSES:
        d = HERE / 'input_v2' / p
        d.mkdir(parents=True, exist_ok=True)
        for old in d.glob('*.txt'):
            old.unlink()
        for st in sorted(U.set.unique()):
            ids = sorted(U[U.set == st].n)
            if p == 'p2':
                ids = ids[::-1]
            elif p == 'p3':
                random.Random(SEED + 3 + sum(map(ord, st))).shuffle(ids)
            nb = math.ceil(len(ids) / MAX_BATCH)
            sz = math.ceil(len(ids) / nb)
            for k in range(nb):
                part = ids[k * sz:(k + 1) * sz]
                name = f'{st}_{k}'
                body = sheets[st] + '\n\nCARDS (answer one line per card, in this order; ids are the numbers after #)\n\n' + '\n\n'.join(blocks[i] for i in part) + \
                    f'\n-- pass {p}, batch {name}: {len(part)} cards\n'
                (d / f'{name}.txt').write_text(body)
                rows.append(dict(pass_=p, batch=name, set=st, n_cards=len(part), chars=len(body), sheet_chars=len(sheets[st])))
    B = pd.DataFrame(rows).rename(columns={'pass_': 'pass'})
    B.to_csv(HERE / 'batches.csv', index=False)
    print(len(B), 'batch files;', B.groupby('pass').size().to_dict())


# ---------------------------------------------------------------- checks
def leakcheck():
    """Hard failures: a card name of the batch's own set (unless the name is quoted in another card's rules text of that set, e.g. a token's name), a set code or
    set name, a rarity word (rare, mythic), a 17Lands word, a real set-specific mechanic name. Names of cards of other sets that happen to be rules vocabulary
    (e.g. 'Flashback') are counted separately and are not failures."""
    s, infos, mechs, R, ck = load_all()
    byset = {}
    for k in ck:
        if '|' in k:
            byset.setdefault(k[:3], set()).add(k.split('|', 1)[1])
    texts = {st: '\n'.join(g.text) for st, g in s.groupby('set')}
    vocab = set(sx.build_vocab(s))
    allnames = sorted({n for v in byset.values() for n in v if not re.match(r'^(Plains|Island|Swamp|Mountain|Forest)$', n) and len(n) > 4})
    codes = sorted(s['set'].unique())
    setnames = sorted({v for v in SET_NAMES.values() if v not in ('Avatar',)})
    bad = info = 0
    for p in PASSES:
        for f in sorted((HERE / 'input_v2' / p).glob('*.txt')):
            t = f.read_text()
            st = f.name.split('_')[0]
            hits = []
            for n in allnames:
                if n in t and re.search(r'(?<![A-Za-z])' + re.escape(n) + r'(?![A-Za-z])', t):
                    own = n in byset[st]
                    quoted = len(re.findall(r'(?<![A-Za-z])' + re.escape(n) + r'(?![A-Za-z])', texts[st])) > 0
                    if all(w in vocab for w in n.split()):
                        quoted = True          # the name is just creature types (a type line such as 'Zombie Ogre')
                    if own and not quoted:
                        hits.append(('own-set card name', n))
                    else:
                        info += 1
            hits += [('set code', c) for c in codes if re.search(r'\b' + c + r'\b', t)]
            hits += [('set name', n) for n in setnames if n.lower() in t.lower()]
            hits += [('rarity/17Lands word', m) for m in re.findall(r'\b(?:rare|rares|mythic|mythics|GIH|ALSA|17Lands|win rate|win-rate)\b', t, re.I)]
            hits += [('real mechanic name', m['name']) for m in mechs.get(st, []) if mech_present(m['name'], t)]
            if hits:
                bad += len(hits)
                print(p, f.name, hits[:6])
    print('leakcheck: hard hits', bad, '| informational (other-set names that are rules vocabulary, or own-set names quoted in rules text):', info)
    return 1 if bad else 0


def mech_present(name, t):
    return bool(es.mech_regex(name).search(t))


def tok(chars):
    return int(chars / 3.6)


def estimate():
    B = pd.read_csv(HERE / 'batches.csv')
    U = pd.read_csv(HERE / 'units.csv')
    rub = len((HERE / 'RUBRIC_v2.md').read_text()) if (HERE / 'RUBRIC_v2.md').exists() else 7000
    out = {'units': len(U), 'by_group': U.groupby('group').size().to_dict(), 'judgements': int(len(U) * 3), 'batches_per_pass': int((B['pass'] == 'p1').sum()),
           'batches_total': len(B)}
    inp = (B.chars.sum() + rub * len(B))
    out['input_tokens_total'] = tok(inp)
    out['input_tokens_per_pass'] = tok(inp) // 3
    out['sheet_tokens_mean'] = tok(B.sheet_chars.mean())
    out['sheet_tokens_max'] = tok(B.sheet_chars.max())
    out['sheet_tokens_FRA'] = tok(len((HERE / 'sheets' / 'FRA.txt').read_text()))
    out['output_tokens_total'] = int(len(U) * 3 * 14)
    out['max_batch_tokens'] = tok(B.chars.max() + rub)
    out['mean_card_block_tokens'] = tok((B.chars - B.sheet_chars).sum() / B.n_cards.sum())
    print(json.dumps(out, indent=1))
    json.dump(out, open(HERE / 'estimate_v2.json', 'w'), indent=1)


def examples():
    s, infos, mechs, R, ck = load_all()
    d = HERE / 'examples_v2'
    d.mkdir(exist_ok=True)
    out = []
    for st in ('FRA', 'MSH'):
        txt, *_ = es.build_sheet(st, s, infos, R, mechs)
        (d / f'sheet_{st}.txt').write_text(txt + '\n')
    for key in ('MSH|Avengers Assemble!', 'ECL|Chronicle of Victory'):
        st = key[:3]
        txt, neut, *_ = es.build_sheet(st, s, infos, R, mechs)
        g = s[s.set == st].copy()
        g['text'] = [neut(t) for t in g.text]
        g['rtext'] = [neut(t) for t in g.rtext]
        ginf = [infos[i] for i in g.index]
        c = ck[key]
        c = dict(n=0, mv=c.mv, colors=c.colors, type_line=c.type_line, pt=c.pt, btext=c.btext)
        out.append(card_block(c, g1.support_refs(R, key), g, ginf, neut))
    (d / 'cards_AA_Chronicle.txt').write_text('\n\n'.join(out) + '\n')
    print('\n\n'.join(out))


def load_raw(p, batch):
    f = HERE / 'raw_v2' / p / f'{batch}.txt'
    if not f.exists():
        return {}, [f'{f} missing']
    out, errors = {}, []
    for n, line in enumerate(f.read_text().splitlines(), 1):
        if not line.strip():
            continue
        m = g1.LINE.match(line.strip())
        if not m:
            errors.append(f'{batch}:{n} bad format: {line!r}'); continue
        v = [int(x) for x in m.group(2).split()]
        if any(x < 0 or x > mx for x, mx in zip(v, MAX)):
            errors.append(f'{batch}:{n} out of range: {line!r}'); continue
        if int(m.group(1)) in out:
            errors.append(f'{batch}:{n} duplicate id')
        out[int(m.group(1))] = v
    return out, errors


def check(passes):
    B = pd.read_csv(HERE / 'batches.csv')
    U = pd.read_csv(HERE / 'units.csv')
    bad = False
    for p in passes:
        miss = extra = errs = 0
        for b in B[B['pass'] == p].itertuples():
            need = set(re.findall(r'^#(\d+) \|', (HERE / 'input_v2' / p / f'{b.batch}.txt').read_text(), re.M))
            need = {int(x) for x in need}
            raw, e = load_raw(p, b.batch)
            miss += len(need - set(raw)); extra += len(set(raw) - need); errs += len(e)
            for x in e[:5]:
                print(' ', x)
        print(f'{p}: units {len(U)}, missing {miss}, extra {extra}, format errors {errs}')
        bad |= bool(miss or extra or errs)
    return 1 if bad else 0


if __name__ == '__main__':
    c = sys.argv[1]
    if c == 'sample':
        sample()
    elif c == 'inputs':
        build_inputs()
    elif c == 'leakcheck':
        sys.exit(leakcheck())
    elif c == 'estimate':
        estimate()
    elif c == 'examples':
        examples()
    elif c == 'check':
        sys.exit(check(sys.argv[2:] or PASSES))
