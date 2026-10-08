"""C8 step 1: objective card profiles from card text (no AI, no outcomes).

  python3 extract.py            -> profiles.csv.gz (one row per unique card text), coverage.json, review_samples.md

Creature profile: P, T, MV and combat keywords.
Removal profile: list of removal effects (kind, amount, conditions, scope, speed) parsed sentence by sentence.
Reminder text is removed before parsing; card names are '~' in the text.
"""
import json, re, sys
from pathlib import Path
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'research/c5_atomic_effects'))
import check_raw as cr  # noqa: E402

NUM = {'a': 1, 'an': 1, 'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5, 'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10}
X_DEFAULT = 4      # an X in damage / -X/-X is taken as 4 (typical mid-game mana)
BITE_POWER = 3     # "deals damage equal to its power" / fight: typical own creature power
COLORS = ['white', 'blue', 'black', 'red', 'green']


def num(s):
    s = s.lower()
    if s == 'x':
        return X_DEFAULT
    return int(s) if s.isdigit() else NUM.get(s, None)


def strip(t):
    return re.sub(r'\([^)]*\)', ' ', t)


def faces(btext):
    return [f for f in re.split(r'//[^/\n]*//', btext)]


def pt(s):
    m = re.fullmatch(r'\s*([0-9*+X-]+)\s*/\s*([0-9*+X-]+)\s*', s or '')
    if not m:
        return None, None
    f = lambda v: float(v) if re.fullmatch(r'\d+', v) else (0.0 if v in ('*', 'X') else None)
    return f(m.group(1)), f(m.group(2))


KW = {
    'flying': r'\bflying\b', 'reach': r'\breach\b', 'first_strike': r'\bfirst strike\b|\bdouble strike\b',
    'double_strike': r'\bdouble strike\b', 'deathtouch': r'\bdeathtouch\b', 'lifelink': r'\blifelink\b',
    'trample': r'\btrample\b', 'menace': r'\bmenace\b|\bskulk\b|can\'t be blocked except by two',
    'unblockable': r"can't be blocked(?! except)", 'vigilance': r'\bvigilance\b', 'haste': r'\bhaste\b',
    'indestructible': r'\bindestructible\b', 'hexproof': r'\bhexproof\b|\bshroud\b', 'ward': r'\bward\b',
    'protection': r'protection from', 'defender': r'\bdefender\b', 'cant_block': r"(?<!creatures )can't block\b",
    'flash': r'\bflash\b',
}


def creature_profile(type_line, ptxt, front):
    is_cr = 'Creature' in type_line.split('//')[0]
    p, t = pt(ptxt) if is_cr else (None, None)
    txt = strip(front).lower()
    # keywords the creature itself has: lines that start with keywords, or "this creature has/gets ... <kw>"
    own = []
    for line in txt.split('\n'):
        line = line.strip()
        if not line:
            continue
        head = re.split(r'[.:]', line)[0]
        if len(head) < 60 and not re.search(r'\b(target|enchanted|equipped|creatures you control|other)\b', head):
            own.append(head)
        for m in re.finditer(r'(?:this creature|~) (?:has|gains|gets [^.]*? and has) ([^.]*)', line):
            own.append(m.group(1))
    own = ' | '.join(own)
    d = {'is_creature': int(is_cr), 'power': p, 'toughness': t}
    for k, pat in KW.items():
        d[f'kw_{k}'] = int(bool(re.search(pat, own))) if is_cr else 0
    return d


COND_PATS = {
    'mv_le': r'mana value (\d+) or less', 'mv_ge': r'mana value (\d+) or greater',
    'pow_ge': r'power (\d+) or greater', 'pow_le': r'power (\d+) or less',
    'tou_ge': r'toughness (\d+) or greater', 'tou_le': r'toughness (\d+) or less',
}


def conditions(s):
    c = {}
    for k, p in COND_PATS.items():
        m = re.search(p, s)
        if m:
            c[k] = int(m.group(1))
    if re.search(r'creature with flying|flying creature', s):
        c['flying_only'] = 1
    if re.search(r'creature without flying|nonflying', s):
        c['nonflying_only'] = 1
    if re.search(r'target tapped creature|tapped creature', s):
        c['tapped_only'] = 1
    if re.search(r'attacking or blocking|attacking creature|blocking creature|target attacking|target blocking', s):
        c['combat_only'] = 1
    m = re.search(r'target non(' + '|'.join(COLORS) + r')', s)
    if m:
        c['not_color'] = m.group(1)
    m = re.search(r'target (' + '|'.join(COLORS) + r') creature', s)
    if m:
        c['color_only'] = m.group(1)
    if re.search(r'creature token', s):
        c['token_only'] = 1
    if re.search(r'\bif you control\b|\bas long as you\b|\bif you\'ve\b|\bif there are\b|\bthreshold\b|\bdelirium\b|\braid\b', s):
        c['setup'] = 1
    return c


TGT_OPP = r"(?:up to (?:one|two|three) )?(?:another )?target (?:[a-z ,-]*?)(?:creature|permanent)(?! you control)(?! card)"


def removal_effects(btext, type_line):
    txt = strip(btext).lower()
    instant = 'Instant' in type_line or bool(re.search(r'^flash\b', txt, re.M))
    perm = not re.search(r'Instant|Sorcery', type_line)
    out = []
    sents = [x.strip() for x in re.split(r'(?<=[.\n])|•', txt)]
    for si, raw in enumerate(sents):
        s = raw.strip()
        nxt = ' '.join(sents[si + 1:si + 3])
        if not s or 'from a graveyard' in s or 'from your graveyard' in s or 'creature card' in s:
            continue
        s2 = s.replace('target creature you control', 'OWNTGT').replace('creatures you control', 'OWNALL')
        sweep_one = bool(re.search(r"creatures your opponents control|creatures you don't control|each creature (?:an opponent|your opponents) control", s2))
        sweep_one = sweep_one or bool(re.search(r'each creature target opponent controls', s2))
        sweep = sweep_one or bool(re.search(r'\beach creature\b|\ball (?:other )?creatures\b|\beach other creature\b|\beach non\w+ creature\b|\b(?:each|all) nonland permanents?\b|each player sacrifices', s2))
        tgt = bool(re.search(TGT_OPP, s2)) or 'any target' in s2 or 'enchanted creature' in s2
        e = None
        obj_ok = not re.search(r'target non(?:creature|land artifact)|noncreature (?:artifact|enchantment|permanent)', s2)
        exile_obj = re.search(r"\bexiles? (?:up to (?:\w+) |any number of )?(?:another |other )?target (?:[a-z ,-]*?)(?:creature|nonland permanent|permanent)|\bexile (?:all|each) (?:other )?(?:non\w+ )?(?:creatures?|nonland permanents?)", s2)
        destroy_obj = re.search(r"\bdestroy (?:up to (?:\w+) )?(?:another )?target (?:[a-z ,-]*?)(?:creature|nonland permanent|permanent)|\bdestroy (?:all|each) (?:other )?(?:non\w+ )?(?:creatures?|nonland permanents?)|\bdestroy (?:it|that creature)\b", s2)
        flicker = bool(re.search(r'return (?:that card|it|those cards|the exiled card|them) to the battlefield', s2 + ' ' + nxt))
        m = re.search(r'deals? (\d+|x|\w+) damage (?:divided [^.]*?among|to) ([^.]*)', s2)
        if m and re.search(r'creature|any target|planeswalker', m.group(2)) and not re.search(r'^(?:each opponent|target player|target opponent|you)\b', m.group(2)):
            e = {'kind': 'dmg', 'amount': num(m.group(1)) or 3}
        elif re.search(r"deals? damage equal to (?:its|that creature's|their|this creature's) power to", s2) or re.search(r'\bfights?\b', s2):
            if re.search(TGT_OPP, s2) or 'any target' in s2 or re.search(r'\bfights?\b', s2):
                e = {'kind': 'bite', 'amount': BITE_POWER}
        elif re.search(r'deals? damage equal to [^.]* to (?:up to one )?(?:another )?target (?:creature|attacking|blocking)|deals? damage equal to [^.]* to any target', s2):
            e = {'kind': 'dmg', 'amount': 3}
        elif destroy_obj and obj_ok:
            e = {'kind': 'destroy', 'amount': 99}
        elif exile_obj and obj_ok and not flicker:
            e = {'kind': 'exile', 'amount': 99, 'temporary': int(bool(re.search(r'until ~ leaves|until this \w+ leaves|for as long as', s2)))}
        elif re.search(r"gain control of (?:up to one )?target (?:[a-z ,-]*?)creature", s2) and not re.search(r'until end of turn', s2):
            e = {'kind': 'exile', 'amount': 99, 'steal': 1}
        elif re.search(r"owner puts it (?:on|into)[^.]*library|(?:put|puts) target [^.]*creature[^.]*(?:on the bottom|on top|into its owner's library)|shuffles? it into (?:its owner's|their) library", s2):
            e = {'kind': 'exile', 'amount': 99}
        elif re.search(r'gets? [+-]?(\d+|x)/-(\d+|x)', s2) and (tgt or sweep) and not re.search(r'gets? \+\d+/-\d+ (?:for each|as long)', s2):
            m = re.search(r'gets? [+-]?(\d+|x)/-(\d+|x)', s2)
            e = {'kind': 'shrink', 'amount': num(m.group(2))}
        elif re.search(r'put (\w+) -1/-1 counters? on (?:up to one )?(?:another )?target creature|-1/-1 counters? on each', s2):
            m = re.search(r'put (\w+) -1/-1 counters?', s2)
            e = {'kind': 'shrink', 'amount': (num(m.group(1)) if m else 1) or 1}
        elif re.search(r'(?:each opponent|target opponent|target player|each player|an opponent)s? (?:chooses|sacrifices|exiles) (?:a|an|one|two|three|x|half)\b[^.]*creature', s2):
            e = {'kind': 'edict', 'amount': 99}
        elif re.search(r"return (?:up to \w+ )?(?:another )?target (?:nonland permanent|creature|[a-z ,]*creature)[^.]*(?:owner's hand|to its owner)", s2):
            e = {'kind': 'bounce', 'amount': 0}
        elif re.search(r"enchanted creature (?:can't attack or block|can't attack|can't block|doesn't untap|loses all abilities)", s2) or \
                (re.search(r'(?:base power and toughness|becomes? a [^.]*?) (?:0/1|1/1)', s2) and (tgt or sweep_one or re.search(r'each creature target opponent controls', s2))):
            e = {'kind': 'pacify', 'amount': 0}
        elif re.search(r'\btap (?:up to \w+ )?target (?:creature|nonland permanent|permanent)|stun counter', s2):
            e = {'kind': 'tap', 'amount': 0}
        if e is None:
            continue
        if e['kind'] in ('dmg', 'shrink') and not (tgt or sweep or 'any target' in s2 or 'divided' in s2):
            continue
        e['scope'] = 'sweep_one_sided' if sweep_one else ('sweep' if sweep and not tgt else 'single')
        e['speed'] = 'instant' if instant else ('permanent' if perm else 'sorcery')
        e.update(conditions(s2))
        e['text'] = s[:160]
        out.append(e)
    return out


def main():
    u = pd.read_csv(HERE / 'cards.csv.gz', keep_default_na=False)
    raw, _ = cr.load_raw()
    rows = []
    for r in u.itertuples():
        if r.auto == 1:
            continue
        fr = faces(r.btext)[0]
        d = {'id': r.id, 'keys': r.keys, 'type_line': r.type_line, 'mv': r.mv, 'colors': r.colors, 'pt': r.pt}
        d.update(creature_profile(r.type_line, r.pt, fr))
        eff = removal_effects(r.btext, r.type_line)
        d['removal'] = json.dumps(eff)
        d['n_removal'] = len(eff)
        tags = raw[r.id][1] if r.id in raw else {}
        d['c5_removal_tag'] = int(bool(set(tags) & {'KD', 'KX', 'DM', 'MS', 'FT', 'ED', 'PA', 'SW'}))
        d['btext'] = r.btext
        rows.append(d)
    t = pd.DataFrame(rows)
    t.to_csv(HERE / 'profiles.csv.gz', index=False, compression='gzip')
    cov = {
        'cards': int(len(t)), 'creatures': int(t.is_creature.sum()),
        'creatures_without_numeric_pt': int(((t.is_creature == 1) & (t.power.isna() | t.toughness.isna())).sum()),
        'cards_with_parsed_removal': int((t.n_removal > 0).sum()),
        'c5_removal_tagged': int(t.c5_removal_tag.sum()),
        'c5_tagged_and_parsed': int(((t.c5_removal_tag == 1) & (t.n_removal > 0)).sum()),
        'c5_tagged_not_parsed': int(((t.c5_removal_tag == 1) & (t.n_removal == 0)).sum()),
        'parsed_not_c5_tagged': int(((t.c5_removal_tag == 0) & (t.n_removal > 0)).sum()),
    }
    kinds = {}
    for x in t.removal:
        for e in json.loads(x):
            kinds[e['kind']] = kinds.get(e['kind'], 0) + 1
    cov['effects_by_kind'] = kinds
    kws = {c: int(t[c].sum()) for c in t.columns if c.startswith('kw_')}
    cov['creature_keywords'] = kws
    json.dump(cov, open(HERE / 'coverage.json', 'w'), indent=1)
    print(json.dumps(cov, indent=1))


if __name__ == '__main__':
    main()
