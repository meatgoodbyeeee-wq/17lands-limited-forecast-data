#!/usr/bin/env python3
"""L1: memory-leak test for C9 judgements (see PLAN.md).  Paths are relative to this file.

  python3 l1.py sample     # draw the sample, write sample_key.csv + input/lXX.txt (blinded)
  python3 l1.py run        # ask the model (claude CLI, one call per batch) -> raw/lXX.txt
  python3 l1.py score      # score names / sets -> scored.csv, accuracy tables
  python3 l1.py analyze    # leak effect on GRADE gap -> analysis tables, summary.json
"""
import json, re, subprocess, sys, unicodedata
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).resolve().parent
C9 = HERE.parent / 'c9_power_questions'
C5IN = HERE.parent / 'c5_atomic_effects' / 'input'
SEED = 20261023
NB = 2000
MODEL = 'claude-opus-5-5'
N_RM, N_CU, N_FRA, BATCH = 240, 120, 60, 60
FORCE = ['MSH|Avengers Assemble!', 'ECL|Chronicle of Victory']

YEAR = {'KHM': 2021, 'STX': 2021, 'AFR': 2021, 'MID': 2021, 'VOW': 2021, 'NEO': 2022, 'SNC': 2022, 'DMU': 2022, 'BRO': 2022,
        'ONE': 2023, 'MOM': 2023, 'LTR': 2023, 'WOE': 2023, 'LCI': 2023, 'MKM': 2024, 'OTJ': 2024, 'BLB': 2024, 'DSK': 2024,
        'FDN': 2024, 'DFT': 2025, 'TDM': 2025, 'EOE': 2025, 'TLA': 2025, 'ECL': 2026, 'TMT': 2026, 'SOS': 2026, 'MSH': 2026,
        'HOB': 2026, 'FRA': 2026}
NAMES = {'AFR': ['Adventures in the Forgotten Realms', 'Forgotten Realms'], 'BLB': ['Bloomburrow'], 'BRO': ["The Brothers' War", 'Brothers War'],
         'DFT': ['Aetherdrift'], 'DMU': ['Dominaria United'], 'DSK': ['Duskmourn', 'Duskmourn: House of Horror'],
         'ECL': ['Lorwyn Eclipsed'], 'EOE': ['Edge of Eternities'], 'FDN': ['Foundations'], 'HOB': ['The Hobbit', 'Hobbit', 'Tales of Middle-earth: The Hobbit'],
         'KHM': ['Kaldheim'], 'LCI': ['The Lost Caverns of Ixalan', 'Lost Caverns of Ixalan'], 'LTR': ['The Lord of the Rings: Tales of Middle-earth', 'Lord of the Rings', 'Tales of Middle-earth'],
         'MID': ['Innistrad: Midnight Hunt', 'Midnight Hunt'], 'MKM': ['Murders at Karlov Manor'], 'MOM': ['March of the Machine'],
         'MSH': ['Marvel Super Heroes', "Marvel's Super Heroes", 'Marvel'], 'NEO': ['Kamigawa: Neon Dynasty', 'Neon Dynasty'],
         'ONE': ['Phyrexia: All Will Be One', 'All Will Be One'], 'OTJ': ['Outlaws of Thunder Junction'], 'SNC': ['Streets of New Capenna', 'New Capenna'],
         'SOS': ['Secrets of Strixhaven'], 'STX': ['Strixhaven: School of Mages', 'Strixhaven', 'Strixhaven School of Mages'],
         'TDM': ['Tarkir: Dragonstorm', 'Tarkir Dragonstorm'], 'TLA': ['Avatar: The Last Airbender', 'Avatar The Last Airbender', 'Avatar'],
         'TMT': ['Teenage Mutant Ninja Turtles', 'TMNT'], 'VOW': ['Innistrad: Crimson Vow', 'Crimson Vow'], 'WOE': ['Wilds of Eldraine', 'Eldraine'],
         'FRA': []}


def norm(s):
    s = unicodedata.normalize('NFKD', str(s)).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+', '', s)


def faces(name):
    parts = [norm(p) for p in re.split(r'\s*//\s*', str(name))] + [norm(name)]
    return {p for p in parts if p}


def name_ok(answer, truth):
    return bool(faces(answer) & faces(truth))


ALIAS = {}
for code, lst in NAMES.items():
    for a in [code] + lst:
        ALIAS.setdefault(norm(a), code)
        ALIAS.setdefault(norm(re.sub(r'^the ', '', a.lower())), code)


def set_of(answer):
    n = norm(answer)
    if not n or n in ('unknown', 'fuming'):
        return None
    if n in ALIAS:
        return ALIAS[n]
    for a, c in sorted(ALIAS.items(), key=lambda x: -len(x[0])):
        if len(a) >= 6 and a in n:
            return c
    return None


# ---------------------------------------------------------------- sample
def pool():
    o = pd.read_csv(C9 / 'oof_B10.csv.gz'); o['key'] = o['set'] + '|' + o['name']
    c = pd.read_csv(C9 / 'cards.csv.gz', keep_default_na=False)
    c['nk'] = c['keys'].str.count(';') + 1
    c['key'] = c['keys'].str.split(';'); e = c.explode('key')
    e = e[(e['auto'] == 0) & (e['nk'] == 1)]          # drop text-less cards and reprints shared by several sets
    m = o.merge(e[['key', 'id']], on='key', how='inner')
    fra = e[e['key'].str.startswith('FRA|')].copy()
    fra['set'] = 'FRA'; fra['name'] = fra['key'].str.split('|', n=1).str[1]; fra['rarity_ord'] = -1
    return m, fra


def alloc(total, sets, rng):
    base, extra = divmod(total, len(sets))
    n = {s: base for s in sets}
    for s in rng.permutation(sets)[:extra]:
        n[s] += 1
    return n


def draw(m, sets, n, rng, rm):
    out = []
    for s in sets:
        p = m[(m['set'] == s) & ((m['rarity_ord'] >= 2) if rm else (m['rarity_ord'] < 2))]
        hi = (p['rarity_ord'] == (3 if rm else 1))
        k = n[s]
        k_hi = int(round(k * hi.mean())) if len(p) else 0
        if rm and hi.sum() and k_hi == 0:
            k_hi = 1
        if (not rm) and k >= 2:
            k_hi = k // 2
        forced = p[p['key'].isin(FORCE)]
        pick = [forced]
        for flag, kk in ((True, k_hi), (False, k - k_hi)):
            q = p[(hi == flag) & ~p['key'].isin(forced['key'])]
            need = kk - int((forced['rarity_ord'].isin([3] if rm else [1]) == flag).sum())
            if need > 0:
                pick.append(q.sample(n=min(need, len(q)), random_state=int(rng.integers(1 << 31))))
        out.append(pd.concat(pick))
    return pd.concat(out)


def blocks():
    b = {}
    for f in sorted(C5IN.glob('b*.txt')):
        txt = f.read_text().split('\n-- batch')[0]
        for c in re.split(r'\n(?=#\d+ \|)', txt):
            c = c.strip()
            if c.startswith('#'):
                b[int(re.match(r'#(\d+)', c).group(1))] = c
    return b


def make_sample():
    rng = np.random.default_rng(SEED)
    m, fra = pool()
    sets = sorted(m['set'].unique())
    rm = draw(m, sets, alloc(N_RM, sets, rng), rng, True); rm['grp'] = 'RM'
    cu = draw(m, sets, alloc(N_CU, sets, rng), rng, False); cu['grp'] = 'CU'
    fr = fra.sample(n=N_FRA, random_state=SEED); fr['grp'] = 'FRA'
    cols = ['key', 'set', 'name', 'rarity_ord', 'id', 'grp']
    s = pd.concat([rm[cols], cu[cols], fr[cols]]).reset_index(drop=True)
    assert s['key'].is_unique and all(k in set(s['key']) for k in FORCE)
    s = s.sample(frac=1, random_state=SEED).reset_index(drop=True)
    s['qid'] = np.arange(1, len(s) + 1); s['batch'] = (s['qid'] - 1) // BATCH
    s.to_csv(HERE / 'sample_key.csv', index=False)
    bl = blocks()
    (HERE / 'input').mkdir(exist_ok=True)
    for b, g in s.groupby('batch'):
        txt = '\n\n'.join(re.sub(r'^#\d+', f'#{q}', bl[i], count=1) for q, i in zip(g['qid'], g['id']))
        (HERE / 'input' / f'l{b:02d}.txt').write_text(txt + '\n')
    print(s.groupby('grp').size().to_dict(), 'batches', s['batch'].nunique())


# ---------------------------------------------------------------- run
PROMPT = """You are an expert on Magic: The Gathering cards from every era. Below are {n} cards, each shown as: #number | mana value, colours | type line | power/toughness, then rules text. The card's own name has been replaced by "~" and the set and rarity are hidden.

For EACH card, try to recall which real card it is. Use all of your knowledge. Give:
- the exact card name (English, as printed),
- the set it comes from (full set name or the 3-4 letter set code),
- your confidence 0-3 (0 = pure guess or no idea, 1 = weak hunch, 2 = fairly sure, 3 = certain).

If you cannot identify the card, write UNKNOWN for both name and set and 0 for confidence. Do not invent names just to fill the answer; wrong guesses are worse than UNKNOWN, but a name you actually believe in should be given.

Output exactly one line per card, in this fixed format and nothing else (no commentary, no code fence):
#number | card name | set | confidence

Cards:

{cards}
"""


def run():
    (HERE / 'raw').mkdir(exist_ok=True)
    work = Path('/tmp/l1_isolated'); work.mkdir(exist_ok=True)
    procs = []
    for f in sorted((HERE / 'input').glob('l*.txt')):
        out = HERE / 'raw' / f.name
        if out.exists():
            continue
        cards = f.read_text()
        n = len(re.findall(r'^#\d+ \|', cards, flags=re.M))
        p = subprocess.Popen(['claude', '-p', '--model', MODEL, '--tools=', '--strict-mcp-config', '--disable-slash-commands',
                              '--system-prompt', 'You are a helpful assistant.', '--setting-sources', ''],
                             stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=work)
        p.stdin.write(PROMPT.format(n=n, cards=cards)); p.stdin.close()
        procs.append((p, out))
    for p, out in procs:
        o = p.stdout.read(); p.wait()
        out.write_text(o)
        print(out.name, p.returncode, len(o.splitlines()))


# ---------------------------------------------------------------- score
LINE = re.compile(r'^#?(\d+)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*([0-3])\s*$')


def parse():
    rows, bad = {}, []
    for f in sorted((HERE / 'raw').glob('l*.txt')):
        for ln in f.read_text().splitlines():
            if not ln.strip():
                continue
            m = LINE.match(ln.strip())
            if m:
                rows[int(m.group(1))] = (m.group(2), m.group(3), int(m.group(4)))
            else:
                bad.append((f.name, ln))
    return rows, bad


def score():
    s = pd.read_csv(HERE / 'sample_key.csv')
    rows, bad = parse()
    s['ans_name'] = s['qid'].map(lambda q: rows.get(q, ('', '', -1))[0])
    s['ans_set'] = s['qid'].map(lambda q: rows.get(q, ('', '', -1))[1])
    s['conf'] = s['qid'].map(lambda q: rows.get(q, ('', '', -1))[2])
    s['answered'] = s['conf'] >= 0
    s['unknown'] = s['ans_name'].map(lambda x: norm(x) in ('unknown', ''))
    s['name_ok'] = [(not u) and name_ok(a, t) for a, t, u in zip(s['ans_name'], s['name'], s['unknown'])]
    s['set_pred'] = s['ans_set'].map(set_of)
    s['set_ok'] = s['set_pred'] == s['set']
    s['year'] = s['set'].map(YEAR)
    s.to_csv(HERE / 'scored.csv', index=False)
    print('unparsed lines:', len(bad), bad[:5], ' unanswered:', int((~s['answered']).sum()))
    t = s.groupby('grp').agg(n=('qid', 'size'), name_acc=('name_ok', 'mean'), set_acc=('set_ok', 'mean'),
                             unknown=('unknown', 'mean'), name_or_set=('name_ok', lambda x: np.nan))
    t['name_or_set'] = s.groupby('grp').apply(lambda g: (g['name_ok'] | g['set_ok']).mean())
    t.to_csv(HERE / 'accuracy_by_group.csv'); print(t.round(3))
    conf = s.groupby(['grp', 'conf']).agg(n=('qid', 'size'), name_acc=('name_ok', 'mean'), set_acc=('set_ok', 'mean')).reset_index()
    conf.to_csv(HERE / 'confidence_dist.csv', index=False); print(conf.round(3))
    yr = s[s['grp'] != 'FRA'].groupby(['year']).agg(n=('qid', 'size'), name_acc=('name_ok', 'mean'), set_acc=('set_ok', 'mean')).reset_index()
    yr.to_csv(HERE / 'accuracy_by_year.csv', index=False); print(yr.round(3))
    st = s.groupby(['set']).agg(n=('qid', 'size'), name_acc=('name_ok', 'mean'), set_acc=('set_ok', 'mean')).reset_index()
    st.to_csv(HERE / 'accuracy_by_set.csv', index=False)
    print(s[s['key'].isin(FORCE)][['key', 'ans_name', 'ans_set', 'conf', 'name_ok', 'set_ok']].to_string())


# ---------------------------------------------------------------- analyze
def spear(a, b):
    if len(a) < 4 or np.std(a) == 0 or np.std(b) == 0:
        return np.nan
    return pd.Series(a).rank().corr(pd.Series(b).rank())


def gap_table():
    o = pd.read_csv(C9 / 'oof_B10.csv.gz'); o['key'] = o['set'] + '|' + o['name']
    c = pd.read_csv(C9 / 'cards.csv.gz', keep_default_na=False)
    c['key'] = c['keys'].str.split(';'); c = c.explode('key')[['key', 'auto']]
    f = pd.read_csv(C9 / 'c9_features.csv.gz')[['key', 'c9_m_GRADE']]
    d = o.merge(c, on='key', how='left').merge(f, on='key', how='left')
    d = d[d['auto'] == 0].copy()
    d['act_rel'] = (d['actual_gih'] - d.groupby('set')['actual_gih'].transform('mean')) * 100
    d['rm'] = d['rarity_ord'] >= 2
    d['gap'] = np.nan
    for m in (d['rm'], ~d['rm']):                       # same definition as D1: leave-one-set-out linear fit GRADE -> act_rel
        for s in sorted(d['set'].unique()):
            tr = d[m & (d['set'] != s)]; te = m & (d['set'] == s)
            b, a = np.polyfit(tr['c9_m_GRADE'], tr['act_rel'], 1)
            d.loc[te, 'gap'] = d.loc[te, 'act_rel'] - (a + b * d.loc[te, 'c9_m_GRADE'])
    return d[['key', 'c9_m_GRADE', 'act_rel', 'gap']]


def stats(g):
    return dict(n=len(g), abs_gap=g['gap'].abs().mean(), gap=g['gap'].mean(), rho=spear(g['c9_m_GRADE'].values, g['act_rel'].values))


def analyze():
    s = pd.read_csv(HERE / 'scored.csv')
    d = s.merge(gap_table(), on='key', how='left')
    d = d[d['grp'] != 'FRA'].copy()
    assert d['gap'].notna().all()
    d['detD'] = d['name_ok']; d['detD2'] = d['name_ok'] | d['set_ok']
    rng = np.random.default_rng(SEED + 1)
    sets = sorted(d['set'].unique()); bysets = {k: g for k, g in d.groupby('set')}
    res = []
    for grp in ('RM', 'CU', 'ALL'):
        dd = d if grp == 'ALL' else d[d['grp'] == grp]
        for dcol in ('detD', 'detD2'):
            def comp(x):
                a, b = x[x[dcol]], x[~x[dcol]]
                sa, sb = stats(a), stats(b)
                return sa, sb, {k: sa[k] - sb[k] for k in ('abs_gap', 'gap', 'rho')}
            sa, sb, df = comp(dd)
            boots = []
            for _ in range(NB):
                pick = rng.choice(sets, len(sets))
                x = pd.concat([dd[dd['set'] == k] for k in pick])
                if x[dcol].sum() < 3 or (~x[dcol]).sum() < 3:
                    continue
                a, b, dif = comp(x)
                boots.append({**{f'D_{k}': a[k] for k in ('abs_gap', 'gap', 'rho')}, **{f'N_{k}': b[k] for k in ('abs_gap', 'gap', 'rho')}, **{f'diff_{k}': dif[k] for k in dif}})
            B = pd.DataFrame(boots)
            row = dict(stratum=grp, definition=dcol, n_det=sa['n'], n_non=sb['n'], boot_valid=len(B))
            for k in ('abs_gap', 'gap', 'rho'):
                for tag, v in (('D', sa[k]), ('N', sb[k]), ('diff', df[k])):
                    col = f'{tag}_{k}' if tag != 'diff' else f'diff_{k}'
                    lo, hi = np.nanpercentile(B[col], [2.5, 97.5]) if len(B) else (np.nan, np.nan)
                    row[f'{col}'] = v; row[f'{col}_lo'] = lo; row[f'{col}_hi'] = hi
            res.append(row)
    R = pd.DataFrame(res); R.to_csv(HERE / 'leak_effect.csv', index=False)
    pd.set_option('display.width', 250); pd.set_option('display.max_columns', 50)
    print(R.round(3).T.to_string())
    # per-card table for the detected cards (for the write-up)
    d[d['detD']][['key', 'grp', 'c9_m_GRADE', 'act_rel', 'gap', 'conf']].to_csv(HERE / 'detected_cards.csv', index=False)
    sa = s[s['grp'] == 'RM']
    acc = sa['name_ok'].mean()
    summ = dict(rm_name_acc=acc, rm_name_n=int(sa['name_ok'].sum()), rm_n=len(sa))
    json.dump(summ, open(HERE / 'summary.json', 'w'), indent=1); print(summ)


if __name__ == '__main__':
    {'sample': make_sample, 'run': run, 'score': score, 'analyze': analyze}[sys.argv[1]]()
