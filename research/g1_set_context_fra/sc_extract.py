#!/usr/bin/env python3
"""G1 set-context extraction: what each card refers to, and how dense that is in its own set (pure counting, no AI, no outcomes).

Rules are fixed in PLAN.md (section 2) before any judging. Input: the set card lists of the 29 sets
(research/c11_set_reading_synergy/set_cards.csv.gz: card text with "~", type line, colours, rarity, freq = expected copies in 3 packs;
basic lands excluded; FRA list = the 290 cards of target.json.gz minus basics).

  python3 sc_extract.py            # writes refs.csv.gz (one row per card x reference) and sc_features.csv.gz (one row per set|card)
"""
import re, sys, json
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).resolve().parent
SRC = HERE.parent / 'c11_set_reading_synergy' / 'set_cards.csv.gz'

DECK_CREATURES, DECK_SPELLS = 15, 23          # typical 40-card deck: 17 lands, 23 spells of which ~15 creatures
SUPER = {'Legendary', 'Snow', 'Basic', 'World', 'Tribal', 'Kindred', 'Creature', 'Artifact', 'Enchantment', 'Land', 'Instant', 'Sorcery', 'Planeswalker'}
# non-creature subtypes that can be referred to (fixed list); Food/Clue/Treasure also count cards that create such a token
NC_SUB = ['Equipment', 'Aura', 'Vehicle', 'Saga', 'Lesson', 'Room', 'Class', 'Case', 'Spacecraft', 'Food', 'Clue', 'Treasure', 'Desert', 'Cave']
TOKEN_SUB = {'Food', 'Clue', 'Treasure'}
KEYWORDS = ['flying', 'first strike', 'double strike', 'deathtouch', 'defender', 'flash', 'haste', 'hexproof', 'indestructible', 'lifelink',
            'menace', 'reach', 'trample', 'vigilance', 'ward', 'prowess', 'changeling', 'convoke']
# card-type words (plural handled); 'noncreature' covers "noncreature spell(s)"
CARD_TYPES = {'instant': r'instants?', 'sorcery': r'sorcer(?:y|ies)', 'artifact': r'artifacts?', 'enchantment': r'enchantments?',
              'planeswalker': r'planeswalkers?', 'legendary': r'legendary', 'noncreature': r'noncreature'}
IRREG = {'Elf': ['Elves'], 'Wolf': ['Wolves'], 'Werewolf': ['Werewolves'], 'Dwarf': ['Dwarves'], 'Mouse': ['Mice'], 'Fungus': ['Fungi'],
         'Cyclops': ['Cyclopes'], 'Hero': ['Heroes'], 'Thief': ['Thieves'], 'Wolfir': ['Wolfir'], 'Merfolk': ['Merfolk'], 'Elk': ['Elk'],
         'Sheep': ['Sheep'], 'Fish': ['Fish'], 'Octopus': ['Octopuses', 'Octopi'], 'Sphinx': ['Sphinxes'], 'Lhurgoyf': ['Lhurgoyfs'],
         'Phoenix': ['Phoenixes', 'Phoenices'], 'Djinn': ['Djinn', 'Djinns'], 'Ox': ['Oxen'], 'Praetor': ['Praetors'], 'Leaf': ['Leaves']}


def strip_reminder(t):
    """Remove reminder text in parentheses (nested ones too: innermost first)."""
    while True:
        u = re.sub(r'\([^()]*\)', '', t)
        if u == t:
            return t
        t = u


def plural_forms(w):
    f = {w, w + 's', w + 'es'}
    if re.search(r'[^aeiou]y$', w):
        f.add(w[:-1] + 'ies')
    if w.endswith('f'):
        f.add(w[:-1] + 'ves')
    if w.endswith('fe'):
        f.add(w[:-2] + 'ves')
    f |= set(IRREG.get(w, []))
    return sorted(f, key=len, reverse=True)


def faces(type_line):
    return [x.strip() for x in type_line.split('//')]


def split_face(face):
    a, _, b = face.partition('—')
    return a.split(), b.split()


def card_info(r):
    """Static facts about one card of a set list."""
    fs = faces(r.type)
    ctypes, is_creature, is_land, supers_all, cardtypes = set(), False, False, set(), set()
    nc_sub = set()
    for f in fs:
        a, b = split_face(f)
        cardtypes |= set(a)
        if 'Creature' in a:
            is_creature = True
            ctypes |= {w for w in b if w not in SUPER}
        else:
            nc_sub |= {w for w in b}
        if 'Land' in a:
            is_land = True
    text = strip_reminder(r.text)
    lines = [l.strip().lower() for l in text.split('\n')]
    kws = set()
    for l in lines:
        if len(l) > 90:
            continue
        for ch in re.split(r'[,;]', l):
            ch = ch.strip()
            for k in KEYWORDS:
                if ch == k or ch.startswith(k + ' {') or ch.startswith(k + ' ') and len(ch) < len(k) + 12 and k in ('ward', 'prowess', 'convoke'):
                    kws.add(k)
    changeling = 'changeling' in kws or 'is every creature type' in text.lower()
    low = text.lower()
    mk_tokens = set()
    for t in TOKEN_SUB:
        if re.search(r'create[^.\n]*\b' + t.lower() + r' tokens?', low):
            mk_tokens.add(t)
    return dict(is_creature=is_creature, is_land=is_land, ctypes=ctypes, changeling=changeling, kws=kws, cardtypes=cardtypes,
                nc_sub=nc_sub & set(NC_SUB), mk_tokens=mk_tokens,
                legendary='Legendary' in r.type.split('—')[0], noncreature=(not is_creature) and not is_land)


def deck_options(colors):
    """Two-colour (or the card's own) decks that can contain the card: C13-style, fixed rule."""
    pairs = ['WU', 'WB', 'WR', 'WG', 'UB', 'UR', 'UG', 'BR', 'BG', 'RG']
    S = set(colors)
    if len(S) >= 2:
        return [S]
    if len(S) == 1:
        return [S | {c} for c in 'WUBRG' if c not in S]
    return [set(p) for p in pairs]


def castable(card_colors, deck):
    return set(card_colors) <= deck


def build_vocab(s):
    ct = set()
    for t in s['type']:
        for f in faces(t):
            a, b = split_face(f)
            if 'Creature' in a:
                ct |= {w for w in b if w not in SUPER}
    ct -= set(NC_SUB) | {'Shrine', 'Book', 'Plan', 'Sphere', 'Planet', 'Treasure', 'Adventure'}
    return sorted(ct)


def type_regex(ct):
    forms = []
    for w in ct:
        for f in plural_forms(w):
            forms.append((f, w))
    forms.sort(key=lambda x: -len(x[0]))
    rx = re.compile(r'(?<![A-Za-z\-])(' + '|'.join(re.escape(f) for f, _ in forms) + r')(?![A-Za-z])')
    back = {f: w for f, w in forms}
    return rx, back


TOK_MASK = re.compile(r'[Cc]reates?\b[^.\n]*?\btokens?\b(?: (?:with|that has|that have|that is|that\'s) [^.\n]*?(?= for each\b| where\b| equal to\b|\.|\n|$))?')
BECOME_MASK = re.compile(r'\bbecomes? an? [^.\n]*?\bcreature\b|\bis every creature type\b')
SELF_MASK = re.compile(r'\b(?:[Tt]his|[Tt]hat|[Ee]nchanted|[Ee]quipped|[Ff]ortified) (?:legendary |snow |nonland )?(?:artifact|enchantment|creature|planeswalker|permanent|spell|Equipment|Vehicle|Aura|Saga|Class|Case|Room|Spacecraft|card|land)\b|'
                       r'\b(?:as an? |at |only as an? |any time you could cast an? )(?:sorcery|instant)(?: speed)?\b|\binstant speed\b|\bsorcery speed\b')
DEP = re.compile(r'\bwhenever\b|\beach time\b|\bfor each\b|\bnumber of\b|\bequal to the (?:number|total|amount)\b|\bget[s]? [+\-\u2212\u2013]|\bas long as\b|\bspells? you cast\b|\bcards? you cast\b|'
                 r'\bcosts? \{?\w\}? less\b|\byou control (?:have|has|gain|get)\b|\bif you(?:\'ve)? (?:control|cast)\b|\byou control (?:with|that)\b|\bfirst (?:spell|instant|sorcery|artifact|creature)\b|\bsecond (?:spell|instant)\b')
CLAUSE_SPLIT = re.compile(r'[.\n;]')


def role_of(clause):
    c = clause.lower()
    tgt = re.search(r'\btarget\b|\bopponents?\b|\beach player\b|\bplayer controls\b', c)
    sup = re.search(r'\byou control\b|\byou cast\b|\byour\b|\byou\b(?!r)|\bchosen\b|\bchoose\b|\bother\b|\bentering\b|\benters\b|\bsacrifice\b', c)
    if tgt and not re.search(r'\byou control\b|\byou cast\b|\byour (?:graveyard|library|hand|team)\b|\bchosen\b', c):
        return 'target'
    return 'support' if sup or not tgt else 'target'


def extract_refs(r, rx, back):
    """List of (kind, label, role) the card refers to. Reminder text and token-creation clauses are ignored."""
    raw = strip_reminder(r.text)
    masked = BECOME_MASK.sub('becomes CREATURE', SELF_MASK.sub('SELF', TOK_MASK.sub('create TOKEN', raw)))
    out, seen = [], set()

    def add(kind, label, role):
        if (kind, label) not in seen:
            seen.add((kind, label)); out.append((kind, label, role))
        elif role == 'support':
            for i, (k, l, ro) in enumerate(out):
                if k == kind and l == label:
                    out[i] = (k, l, 'support')

    for cl in CLAUSE_SPLIT.split(masked):
        if not cl.strip():
            continue
        role = role_of(cl)
        # chosen creature type
        if re.search(r'choose a creature type|chosen (?:creature )?type|of the chosen type', cl, re.I):
            add('chosen_type', 'chosen', 'support')
        # specific creature types (case-sensitive: types are capitalised in rules text)
        for m in rx.finditer(cl):
            add('ctype', back[m.group(1)], role)
        low = cl.lower()
        # keyword abilities used as a reference (not as a grant)
        for k in KEYWORDS:
            kk = re.escape(k)
            if k == 'changeling':
                continue
            if (re.search(r'\bwith ' + kk + r'\b', low) or re.search(r'\bthat (?:has|have|had) ' + kk + r'\b', low) or
                    re.search(r'\b(?:non)?' + kk + r' (?:creatures?|spells?|permanents?|cards?)\b', low) or re.search(r'\bnon' + kk + r'\b', low)):
                scope = 'creature' if re.search(r'creature', low) else 'nonland'
                if DEP.search(low):
                    add('keyword', f'{k}|{scope}', role)
        # card types
        for k, p in CARD_TYPES.items():
            if re.search(r'(?<![a-z])' + p + r'(?![a-z])', low):
                if k == 'noncreature' and not re.search(r'noncreature (?:spell|card|permanent)', low):
                    continue
                if DEP.search(low):
                    add('cardtype', k, role)
        # non-creature subtypes (Equipment, Aura, ...)
        for k in NC_SUB:
            if re.search(r'\b' + k + r's?\b', cl) and not (k in ('Aura', 'Equipment') and re.search(r'\b(?:enchanted|equipped)\b', cl) and not re.search(r'\b' + k + r's? (?:you|spell|card)', cl)):
                if DEP.search(cl.lower()):
                    add('nc_sub', k, role)
    return out


def main():
    s = pd.read_csv(SRC, keep_default_na=False)
    ct = build_vocab(s)
    rx, back = type_regex(ct)
    infos = {r.key: card_info(r) for r in s.itertuples()}
    ART_TOK = re.compile(r'\bartifact\b|\b(?:Treasure|Clue|Food|Blood|Map|Powerstone|Incubator|Junk|Gold|Shard|Lander|Vehicle|Equipment)\b')
    for r in s.itertuples():       # cards that make tokens of a creature type / card type (reminder text included on purpose)
        mkc, mkt = set(), set()
        for m in re.finditer(r'[Cc]reates?\b[^.\n]*?\btokens?\b|\bincubate\b|\bempower\b', r.text):
            seg = m.group(0)
            for mm in rx.finditer(seg):
                mkc.add(back[mm.group(1)])
            if ART_TOK.search(seg) or seg.lower() in ('incubate',):
                mkt.add('artifact')
            if re.search(r'\benchantment\b|\bRole\b', seg):
                mkt.add('enchantment')
            if re.search(r'planeswalker', seg, re.I):
                mkt.add('planeswalker')
        if re.search(r'\bempower\b', r.text) and re.search(r'planeswalker token', r.text):
            mkt.add('planeswalker')
        infos[r.key]['mk_ctypes'] = mkc
        infos[r.key]['mk_cardtypes'] = mkt
    s['colors'] = s['colors'].astype(str)
    rows_ref, feats = [], []
    per_set = {}
    for st, g in s.groupby('set', sort=True):
        g = g.reset_index(drop=True)
        gi = [infos[k] for k in g['key']]
        per_set[st] = (g, gi)

    cast_cache = {}

    def denominators(g, gi, self_idx, deck, scope):
        """weights and masks for cards of the set castable in `deck`, non-land, excluding the card itself."""
        ck = (g['set'].iloc[0], ''.join(sorted(deck)), scope)
        if ck not in cast_cache:
            ok0 = np.array([(not gi[i]['is_land']) and castable(g.colors.iloc[i], deck) for i in range(len(g))])
            if scope == 'creature':
                ok0 &= np.array([gi[i]['is_creature'] for i in range(len(g))])
            cast_cache[ck] = ok0
        ok = cast_cache[ck].copy()
        ok[self_idx] = False
        return ok

    for st, (g, gi) in per_set.items():
        w = g['freq'].to_numpy(float)
        rar = g['rar'].to_numpy(int)
        n = len(g)
        creat = np.array([x['is_creature'] for x in gi])
        nonland = np.array([not x['is_land'] for x in gi])

        def match_vec(kind, label):
            if kind == 'ctype':
                return np.array([x['is_creature'] and (label in x['ctypes'] or x['changeling']) for x in gi]), 'creature'
            if kind == 'keyword':
                k, scope = label.split('|')
                return np.array([k in x['kws'] or (k == 'changeling' and x['changeling']) for x in gi]), scope
            if kind == 'cardtype':
                f = {'instant': lambda x: 'Instant' in x['cardtypes'], 'sorcery': lambda x: 'Sorcery' in x['cardtypes'],
                     'artifact': lambda x: 'Artifact' in x['cardtypes'], 'enchantment': lambda x: 'Enchantment' in x['cardtypes'],
                     'planeswalker': lambda x: 'Planeswalker' in x['cardtypes'], 'legendary': lambda x: x['legendary'],
                     'noncreature': lambda x: x['noncreature']}[label]
                return np.array([f(x) for x in gi]), 'nonland'
            if kind == 'nc_sub':
                return np.array([label in x['nc_sub'] or label in x['mk_tokens'] for x in gi]), 'nonland'
            raise ValueError(kind)

        # cache set-level type tables for 'chosen'
        types_in_set = sorted({t for x in gi for t in x['ctypes']})
        tmask = {t: match_vec('ctype', t)[0] for t in types_in_set}
        for i, r in enumerate(g.itertuples()):
            refs = extract_refs(r, rx, back)
            for kind, label, role in refs:
                opts = deck_options(r.colors)
                if kind == 'chosen_type':
                    best = (-1, None, None)
                    for t in types_in_set:
                        vec = tmask[t]
                        for d in opts:
                            ok = denominators(g, gi, i, d, 'creature')
                            den = w[ok].sum()
                            sh = (w[ok & vec].sum() / den) if den > 0 else 0.0
                            if sh > best[0]:
                                best = (sh, t, d)
                    share_deck, label_out = best[0], f'chosen -> best type {best[1]}'
                    vec, scope = tmask[best[1]], 'creature'
                    n_match = int((vec & creat).sum()) - (1 if (vec[i] and creat[i]) else 0)
                    n_den = int(creat.sum()) - (1 if creat[i] else 0)
                    # commons/uncommons
                    cu = rar <= 1
                    n_cu = int((vec & creat & cu).sum()) - (1 if (vec[i] and creat[i] and cu[i]) else 0)
                    d_cu = int((creat & cu).sum()) - (1 if (creat[i] and cu[i]) else 0)
                    E = share_deck * DECK_CREATURES
                    rows_ref.append(dict(key=r.key, set=st, id=r.id, kind=kind, label=label_out, role=role, scope=scope, n_match=n_match, n_den=n_den, n_mk=0,
                                         n_match_cu=n_cu, n_den_cu=d_cu, share_set=n_match / n_den if n_den else 0.0, share_deck=share_deck, exp_in_deck=E, exp_incl_mk=E,
                                         basis='best case (best type, best matching colour pair)'))
                    continue
                vec, scope = match_vec(kind, label)
                if kind == 'ctype':
                    mkvec = np.array([label in x['mk_ctypes'] for x in gi]) & ~vec
                elif kind == 'cardtype' and label in ('artifact', 'enchantment', 'planeswalker'):
                    mkvec = np.array([label in x['mk_cardtypes'] for x in gi]) & ~vec
                else:
                    mkvec = np.zeros(n, bool)
                mkvec[i] = False
                n_mk = int(mkvec.sum())
                den_vec = creat if scope == 'creature' else nonland
                self_in = bool(vec[i] and den_vec[i])
                n_match = int((vec & den_vec).sum()) - (1 if self_in else 0)
                n_den = int(den_vec.sum()) - (1 if den_vec[i] else 0)
                cu = rar <= 1
                n_cu = int((vec & den_vec & cu).sum()) - (1 if (self_in and cu[i]) else 0)
                d_cu = int((den_vec & cu).sum()) - (1 if (den_vec[i] and cu[i]) else 0)
                shs = []
                for d in opts:
                    ok = denominators(g, gi, i, d, 'creature' if scope == 'creature' else 'nonland')
                    den = w[ok].sum()
                    shs.append((w[ok & vec].sum() / den) if den > 0 else 0.0)
                share_deck = float(np.mean(shs))
                shi = []
                for d in opts:
                    ok = denominators(g, gi, i, d, 'nonland')
                    den = w[ok].sum()
                    shi.append((w[ok & (vec | mkvec)].sum() / den) if den > 0 else 0.0)
                E_incl = float(np.mean(shi)) * DECK_SPELLS
                E = share_deck * (DECK_CREATURES if scope == 'creature' else DECK_SPELLS)
                rows_ref.append(dict(key=r.key, set=st, id=r.id, kind=kind, label=label, role=role, scope=scope, n_match=n_match, n_den=n_den, n_mk=n_mk,
                                     n_match_cu=n_cu, n_den_cu=d_cu, share_set=n_match / n_den if n_den else 0.0, share_deck=share_deck, exp_in_deck=E, exp_incl_mk=E_incl,
                                     basis='average over the decks that can contain the card'))
    R = pd.DataFrame(rows_ref)
    R.to_csv(HERE / 'refs.csv.gz', index=False, compression='gzip')

    # ---- card-level features (support references only for the main columns; target references in their own columns)
    s['key'] = s['key']
    F = pd.DataFrame({'key': s['key']})
    sup = R[R.role == 'support']
    tgt = R[R.role == 'target']
    g_sup = sup.groupby('key')
    F = F.set_index('key')
    F['sc_n_sup'] = g_sup.size().reindex(F.index).fillna(0)
    F['sc_n_tgt'] = tgt.groupby('key').size().reindex(F.index).fillna(0)
    F['sc_sup_share_max'] = g_sup['share_deck'].max().reindex(F.index).fillna(0)
    F['sc_sup_share_min'] = g_sup['share_deck'].min().reindex(F.index).fillna(0)
    F['sc_sup_E_max'] = g_sup['exp_in_deck'].max().reindex(F.index).fillna(0)
    F['sc_sup_E_min'] = g_sup['exp_in_deck'].min().reindex(F.index).fillna(0)
    for kind, col in [('ctype', 'tribe'), ('chosen_type', 'chosen'), ('keyword', 'kw'), ('cardtype', 'ctyp'), ('nc_sub', 'ncsub')]:
        F[f'sc_{col}_share'] = sup[sup.kind == kind].groupby('key')['share_deck'].max().reindex(F.index).fillna(0)
    F['sc_sup_mk_n'] = g_sup['n_mk'].max().reindex(F.index).fillna(0)
    F['sc_tgt_share_max'] = tgt.groupby('key')['share_deck'].max().reindex(F.index).fillna(0)
    F = F.reset_index()
    F['id'] = s['id'].to_numpy()
    F['set'] = s['set'].to_numpy()
    F.to_csv(HERE / 'sc_features.csv.gz', index=False, compression='gzip')
    print('cards', len(s), 'refs', len(R))
    summ = []
    for st, g in s.groupby('set'):
        keys = set(g['key'])
        rs = R[R.key.isin(keys)]
        nonbasic_nonland = int((~g['type'].str.contains('Land')).sum())
        summ.append(dict(set=st, cards=len(g), nonland=nonbasic_nonland, with_support_ref=rs[rs.role == 'support'].key.nunique(),
                         with_target_only=len(set(rs[rs.role == 'target'].key) - set(rs[rs.role == 'support'].key))))
    S = pd.DataFrame(summ)
    S.to_csv(HERE / 'ref_counts_by_set.csv', index=False)
    print(S.to_string())
    print(R.groupby(['kind', 'role']).size().unstack(fill_value=0))


if __name__ == '__main__':
    main()
