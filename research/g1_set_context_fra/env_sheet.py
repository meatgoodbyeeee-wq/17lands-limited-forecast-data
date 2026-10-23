#!/usr/bin/env python3
"""G1 plan v2: the ENVIRONMENT SHEET (one per set) and the per-card SET INFO, both made only by counting the card list (no AI, no outcomes).

Rules are fixed in PLAN_v2.md before any judging. Input: research/c11_set_reading_synergy/set_cards.csv.gz (29 sets; text, type, colours, rarity,
mana value, P/T; no outcome data) and refs.csv.gz (the support references found by sc_extract.py, unchanged from plan v1).

  python3 env_sheet.py sheets            # writes sheets/<SET>.txt for the 29 sets and mechanics.csv
  python3 env_sheet.py mechanics         # prints the mechanics found per set and the neutral label of each
"""
import re, sys, collections
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import sc_extract as sx  # noqa: E402  (card_info, reference extraction, vocabulary: plan v1 rules, unchanged)

SRC = sx.SRC
COLS = ['W', 'U', 'B', 'R', 'G', 'M', 'C']                  # M = two or more colours, C = colourless
COLNAME = {'W': 'W', 'U': 'U', 'B': 'B', 'R': 'R', 'G': 'G', 'M': 'gold', 'C': 'colourless'}
PAIRS = ['WU', 'UB', 'BR', 'RG', 'GW', 'WB', 'UR', 'BG', 'RW', 'GU']
MECH_MAX_SETS, MECH_MIN_CARDS = 4, 3
LETTERS = 'ABCDEFGHIJKLMNOP'


def norm(t):
    return t.replace('−', '-').replace('–', '-')


def strip_rem(t):
    return sx.strip_reminder(t)


# ---------------------------------------------------------------- card table
def load():
    s = pd.read_csv(SRC, keep_default_na=False)
    s['colors'] = s['colors'].astype(str)
    infos = [sx.card_info(r) for r in s.itertuples()]
    s['is_creature'] = [i['is_creature'] for i in infos]
    s['is_land'] = [i['is_land'] for i in infos]
    s['cu'] = s['rar'] <= 1
    s['cg'] = [c if len(c) == 1 else ('C' if len(c) == 0 else 'M') for c in s['colors']]
    pw = s['pt'].astype(str).str.extract(r'^(\d+|\*)/(\d+|\*)')
    s['pw'] = pd.to_numeric(pw[0], errors='coerce')
    s['tg'] = pd.to_numeric(pw[1], errors='coerce')
    s['mvb'] = s['mv'].astype(float).clip(lower=1, upper=6).astype(int)      # buckets: <=1, 2, 3, 4, 5, 6+
    s['rtext'] = [norm(strip_rem(t)) for t in s['text']]                    # text without reminder text, minus signs normalised
    s['faces0'] = [x.split('//')[0] for x in s['type']]
    return s, infos


# ---------------------------------------------------------------- set mechanics (neutral labels)
STOP_FIRST = set('you your this that these those it its each target another all any when whenever at if as then create put draw tap untap activate return search exile '
                 'destroy gain gains lose deal deals discard sacrifice choose reveal look mill add pay remove attach cast play counter copy get gets have has can '
                 'creatures creature spells spell cards card enchant equipped enchanted up one two three x the a an and or not only to from of in on with for by be '
                 'is are was were do does don\'t until during may must instead also'.split())
ROMAN = re.compile(r'^[IVX]+(?:, [IVX]+)*$')
STOP_FIRST |= {"it's", '~', "that's"}
TRIM_TAIL = STOP_FIRST | {'card', 'tapped', 'cards'}
EVERGREEN = set(sx.KEYWORDS) | {'equip', 'kicker', 'crew', 'scry', 'surveil', 'flashback', 'cycling', 'landcycling', 'basic landcycling', 'typecycling', 'reach', 'banding', 'hexproof'}


def clean_name(words):
    while len(words) > 1 and words[-1] in TRIM_TAIL:
        words = words[:-1]
    return ' '.join(words)


def mech_candidates(row):
    """Names of keyword actions / ability words on one card: (name, kind, example line). Reminder text is the signal for keywords, an em dash for ability words."""
    out = []
    for line in row.text.split('\n'):
        line = line.strip()
        if not line:
            continue
        m = re.match(r"^([A-Z][A-Za-z'\-]+(?: [A-Za-z'\-]+){0,2}) — ", line)
        if m and not ROMAN.match(m.group(1)) and not m.group(1).lower().startswith('choose'):
            if m.group(1).lower() not in EVERGREEN:
                out.append((m.group(1).lower(), 'ability word', line))
        for pm in re.finditer(r'\(([^()]*)\)', line):
            pre = line[:pm.start()].strip()
            if not pre:
                continue
            seg = [x for x in re.split(r'[.,;:]\s*', pre) if x.strip()]
            if not seg:
                continue
            seg = re.sub(r'^(?:you may|may) ', '', seg[-1].strip(), flags=re.I)
            mm = re.match(r'^(?:this creature|~|this \w+) (?:enters|becomes) (\w+)$', seg, re.I)
            if mm:
                out.append((mm.group(1).lower(), 'keyword', line)); continue
            words = []
            for i, w in enumerate(seg.split()):
                if re.search(r'[\d{\[]', w) or (i > 0 and w[:1].isupper()):
                    break
                words.append(w.strip('!').lower())
                if len(words) == 3 or w.endswith('!'):
                    break
            if not words or words[0] in STOP_FIRST:
                continue
            nm = clean_name(words)
            if nm in EVERGREEN or nm.endswith('cycling'):
                continue
            out.append((nm, 'keyword', line))
    return out


def detect_mechanics(s):
    """{set: [(name, label, kind, n_cards, annotation_example)]}: names that appear (with reminder text or as an ability word) on >= 3 cards of the set
    and in at most 4 of the 29 sets. Everything else (flying, kicker, cycling, landfall ...) is common vocabulary and keeps its real name."""
    per = collections.defaultdict(lambda: collections.defaultdict(list))
    for r in s.itertuples():
        seen = set()
        for name, kind, line in mech_candidates(r):
            if name not in seen:
                seen.add(name)
                per[name][r.set].append((r, kind, line))
    res = {st: [] for st in s['set'].unique()}
    for name, d in per.items():
        if len(d) > MECH_MAX_SETS:
            continue
        for st, lst in d.items():
            if len(lst) >= MECH_MIN_CARDS:
                lst.sort(key=lambda x: (x[0].mv, x[0].text))
                res[st].append([name, lst[0][1], len(lst), lst[0][2], lst])
    out = {}
    for st, items in res.items():
        items.sort(key=lambda x: (-x[2], x[0]))
        # drop a name that is a prefix/substring of a longer detected name with at least the same count (e.g. 'basic' vs 'basic landcycling')
        keep = []
        for it in items:
            if any(it[0] != o[0] and re.search(r'\b' + re.escape(it[0]) + r'\b', o[0]) and o[2] >= it[2] for o in items):
                continue
            keep.append(it)
        out[st] = [dict(name=it[0], label='Mechanism ' + LETTERS[i], kind=it[1], n=it[2], example=it[3], cards=[x[0] for x in it[4]])
                   for i, it in enumerate(keep[:len(LETTERS)])]
    return out


def mech_regex(name):
    return re.compile(r'\b' + re.escape(name) + r'(?:s|ed|d|ing)?\b', re.I)


def make_neutralizer(mechs):
    pats = [(mech_regex(m['name']), m['label']) for m in sorted(mechs, key=lambda m: -len(m['name']))]

    def f(t):
        for rx, lab in pats:
            t = rx.sub(lab, t)
        return t
    return f


# ---------------------------------------------------------------- rules: removal, evasion, instant-speed interventions
def _own(phrase):
    return bool(re.search(r"\byou control\b", phrase)) and not re.search(r"don't control|do not control", phrase)


def _creature_phrase(p):
    return bool(re.search(r'creature|nonland permanent|\bpermanent', p)) and not re.search(r'creature cards?|permanent cards?|from a graveyard|spell', p)


REMOVAL_KINDS = ['destroy', 'damage', 'exile', 'bounce', 'minus', 'fight', 'bind']
KIND_NAME = {'destroy': 'destroy', 'damage': 'damage', 'exile': 'exile', 'bounce': 'bounce/tuck', 'minus': '-X/-X', 'fight': 'fight/bite', 'bind': 'lock-down', 'sweeper': 'sweeper'}


def removal_kinds(r):
    """Which kinds of creature removal a card (usable on an opponent's creature) has. Text without reminder text. Enchantment/artifact-only removal is not counted."""
    t = r.rtext.lower()
    t = re.sub(r'\bthis (?:creature|artifact|enchantment|spell|permanent|card)\b', '~', t)
    kinds, sweep = set(), False
    sents = [x.strip() for x in re.split(r'[.\n]', t) if x.strip()]
    for sn in sents:
        # destroy / exile (creature or nonland permanent targets; enchantment-only / artifact-only / land-only removal is not counted)
        m = re.search(r'\b(destroy|exile) (?:up to \w+ )?(?:another )?(target|each|all) ([^;]*)', sn)
        if m:
            ph = m.group(3)[:90]
            if _creature_phrase(ph) and not _own(ph):
                if m.group(2) == 'target':
                    kinds.add(m.group(1))
                else:
                    sweep = True
        # damage to a creature / any target
        if re.search(r'\bdeals? (?:\d+|x|twice x|that much|damage equal to|\w+ damage)', sn) or 'damage' in sn:
            if re.search(r'damage equal to (?:its|~\'s|that creature\'s|target creature\'s|his|her|their) power|damage to [^.]*? equal to (?:its|that creature\'s) power', sn) \
                    or re.search(r'\bfights?\b', sn):
                kinds.add('fight')
            elif re.search(r'damage[^.]*? to (?:up to \w+ )?(?:any target|target (?:[a-z\-]+ )*creature|target (?:[a-z\-]+ )*permanent|any number of target creatures|up to \w+ target creatures)', sn) \
                    and not re.search(r'to target creature you control', sn):
                kinds.add('damage')
            elif re.search(r'damage[^.]*? to (?:each|all) (?:other )?(?:non[a-z]+ )?creatures?(?! you control)', sn) and not re.search(r'you control', sn):
                sweep = True
            elif re.search(r'damage divided as you choose among', sn):
                kinds.add('damage')
        if re.search(r'\bfights?\b', sn) and 'fight' not in kinds and re.search(r'target creature', sn):
            kinds.add('fight')
        # bounce / tuck
        m = re.search(r"\b(?:return|put|shuffle) (?:up to \w+ )?(target|each|all) ([^.;]*?)(?: to | into | on top of | on the bottom of )(?:its|their|that player's|the) ?(?:owner's|owners') (hand|library)", sn)
        if m and _creature_phrase(m.group(2)) and not _own(m.group(2)) and 'card' not in m.group(2):
            (sweep := True) if m.group(1) in ('each', 'all') else kinds.add('bounce')
        # -X/-X
        if re.search(r'-(?:\d+|x)/-(?:[1-9]\d*|x)', sn) or re.search(r'put (?:a|an|two|three|\d+|x|that many) -1/-1 counters? on (?:up to \w+ )?target', sn):
            mm = re.search(r'((?:target|each|all|up to)[^,]*?)(?:gets?|get|put)', sn)
            if (re.search(r'target [^,]*?creature', sn) or re.search(r'-1/-1 counters? on (?:up to \w+ )?target', sn)) and not re.search(r'target creature you control', sn) \
                    and not re.search(r'creatures? you control (?:get|gets)', sn):
                kinds.add('minus')
            elif re.search(r'(?:each|all) (?:other )?(?:non[a-z]+ )?creatures?(?! you control)[^,]*? gets?', sn) and not re.search(r'you control', sn.split('get')[0]):
                sweep = True
    if re.search(r'\bfights?\b|fights? up to one', r.rtext.lower()) and 'fight' not in kinds and re.search(r'target creature', r.rtext.lower()):
        kinds.add('fight')
    if lockdown(r):
        kinds.add('bind')
    return kinds, sweep


def lockdown(r):
    """Lock-down ("拘束型") on an opponent's creature: only Aura / non-creature Enchantment / non-creature Artifact (not instants or sorceries):
    (a) the enchanted / targeted / opposing creature can't attack (or block), (b) doesn't untap, (c) its activated abilities can't be activated,
    (d) a repeatable tap ability ('{T}'-type cost : tap target creature). Auras that also give a bonus (+N/+N) or enchant 'creature you control' are not counted."""
    faces = r.faces0
    if r.is_creature or not re.search(r'Enchantment|Artifact|Aura', faces) or re.search(r'Instant|Sorcery|Land', faces):
        return False
    t = r.rtext.lower()
    if 'aura' in faces.lower():
        if re.search(r'enchant creature you control|enchant (?:land|artifact|permanent you)', t):
            return False
        if re.search(r'enchanted creature (?:gets|has|gains) \+', t):
            return False
    opp = (r"(?:enchanted creature|target creature|creatures? (?:your )?opponents? control|each creature your opponents control|creatures? you don't control|"
           r"creatures? an opponent controls|nonland permanents? your opponents control|that creature|it)")
    if re.search(opp + r"[^.\n]*? (?:can't|cannot) attack", t) or re.search(r"(?:can't|cannot) attack(?: or block)?[^.\n]*", t) and 'enchanted creature can' in t:
        return True
    if re.search(opp + r"[^.\n]*?doesn't untap|doesn't untap during (?:its|their) controller", t):
        return True
    if re.search(r"activated abilities of (?:enchanted creature|creatures? (?:your )?opponents? control|target creature)[^.\n]*can't be activated|enchanted creature's activated abilities can't", t) \
            or re.search(r"enchanted creature[^.\n]*activated abilities[^.\n]*can't be activated", t):
        return True
    if re.search(r'(?:^|\n)[^.\n]*:[^.\n]*\btap target (?:\w+ )?creature(?! you control)(?: an opponent controls)?', t) and not re.search(r'tap target creature you control', t):
        return True
    return False


EVADE_LINE = [('flying', r'^flying$'), ('protection', r'^protection from'), ('unblockable', r"can't be blocked(?! by more than one)"), ('shadow', r'^shadow$'),
              ('other', r'^(?:fear|intimidate|horsemanship|skulk)$|walk$|^islandwalk|^swampwalk|^forestwalk|^mountainwalk|^plainswalk|^landwalk')]


def evasion(r):
    """Native evasion of a creature: set of {'flying','protection','unblockable','shadow','other'}. Menace and trample are NOT evasion here. Reach is counted separately."""
    if not r.is_creature:
        return set(), False
    t = r.rtext.lower()
    ev, reach = set(), False
    for line in t.split('\n'):
        for seg in re.split(r'[,;]\s*', line.strip()):
            seg = seg.strip()
            if seg == 'reach':
                reach = True
            if seg == 'flying':
                ev.add('flying')
            elif seg.startswith('protection from'):
                ev.add('protection')
            elif seg == 'shadow':
                ev.add('shadow')
            elif seg in ('fear', 'intimidate', 'horsemanship', 'skulk') or re.fullmatch(r'\w*walk', seg):
                ev.add('other')
    for line in t.split('\n'):
        if re.search(r"(?:^|, )(?:~|this creature) can't be blocked(?! by more than one)", line.strip()) or re.match(r"^can't be blocked(?! by more than one)", line.strip()):
            ev.add('unblockable')
    return ev, reach


def hand_kinds(r):
    """Instant-speed interventions: ('instant','flash','hand_ability','unblocked_swap','cycle_trigger').
    hand_ability = an activated ability usable from hand whose cost discards the card itself (channel-like / FRA 'Discard this card: ...'), except cycling-family
    keywords and abilities whose effect is only draw / search / scry / surveil / gain life (pure card selection). unblocked_swap = ninjutsu / sneak (return an unblocked attacker).
    cycle_trigger = a cycling card with a 'when you cycle' effect."""
    k = set()
    faces = r.faces0
    t = r.rtext.lower()
    raw = norm(r.text).lower()
    if re.search(r'\bInstant\b', faces):
        k.add('instant')
    if re.search(r'(?:^|\n|, )flash(?:$|\n|,| \()', t) or re.search(r'(?:^|\n)flash\b', t):
        k.add('flash')
    for line in t.split('\n'):
        line = line.strip()
        if re.match(r'^(?:basic )?(?:\w*)cycling\b', line) or re.match(r'^typecycling', line):
            continue
        m = re.search(r'^([^:\n]*discard (?:this card|~)[^:\n]*):(.*)$', line)
        if m:
            eff = m.group(2).strip()
            if not re.match(r'^(?:draw (?:a|one|two|\d+) cards?|search your library|scry|surveil|you gain \d+ life|look at)', eff):
                k.add('hand_ability')
    if re.search(r'return an unblocked attacker you control to (?:its owner\'s |your )?hand', raw):
        k.add('unblocked_swap')
    if re.search(r'when(?:ever)? you cycle (?:this card|~|a card)|when you discard this card|when you cycle or discard', t):
        k.add('cycle_trigger')
    return k


# ---------------------------------------------------------------- formatting helpers
def f1(x):
    return f'{x:.1f}'.rstrip('0').rstrip('.') if x == x else '-'


def mvlist(mvs):
    return ','.join(str(int(m)) for m in sorted(mvs))


def tiers(g):
    return g[g.cu], g[~g.cu]


def cnt_line(g):
    """'W 3|1 U 0|0 ...' counts as commons-uncommons|rares-mythics, nonzero colours only."""
    parts = []
    for c in COLS:
        h = g[g.cg == c]
        a, b = int(h.cu.sum()), int((~h.cu).sum())
        if a or b:
            parts.append(f'{COLNAME[c]} {a}|{b}')
    return ', '.join(parts) if parts else 'none'


# ---------------------------------------------------------------- the sheet
def creature_table(g):
    cr = g[g.is_creature & ~g.is_land]
    lines = []
    for title, sub in (('all cards', cr), ('commons and uncommons only', cr[cr.cu])):
        lines.append(f'Creatures, {title} (count, average power/toughness; "MV<=1" includes MV0):')
        for c in COLS:
            h = sub[sub.cg == c]
            if not len(h):
                lines.append(f'  {COLNAME[c]}: none')
                continue
            cells = []
            for b, lab in zip(range(1, 7), ['MV<=1', 'MV2', 'MV3', 'MV4', 'MV5', 'MV6+']):
                x = h[h.mvb == b]
                if len(x):
                    pt = f' {f1(x.pw.mean())}/{f1(x.tg.mean())}' if x.pw.notna().any() else ''
                    cells.append(f'{lab} {len(x)}{pt}')
            tot = f' | total {len(h)}' + (f' avg {f1(h.pw.mean())}/{f1(h.tg.mean())}' if h.pw.notna().any() else '')
            lines.append(f'  {COLNAME[c]}: ' + '; '.join(cells) + tot)
    return lines


def removal_table(g, rk):
    lines = ['Removal that can hit an opponent\'s creature, by colour; each entry "C/U n (MVs) | R/M n (MVs)" (a card with two kinds is counted in both; "any" = distinct cards):']
    for c in COLS:
        h = g[g.cg == c]
        ents = []
        for k in REMOVAL_KINDS + ['sweeper']:
            sel = [i for i in h.index if (k in rk[i][0] if k != 'sweeper' else rk[i][1])]
            if not sel:
                continue
            x = g.loc[sel]
            a, b = x[x.cu], x[~x.cu]
            ents.append(f'{KIND_NAME[k]} {len(a)} ({mvlist(a.mv)}) | {len(b)} ({mvlist(b.mv)})')
        anyc = [i for i in h.index if rk[i][0] or rk[i][1]]
        x = g.loc[anyc]
        lines.append(f'  {COLNAME[c]}: any {int(x.cu.sum())}|{int((~x.cu).sum())}' + ('; ' + '; '.join(ents) if ents else ''))
    return lines


def evasion_table(g, ev):
    cr = g[g.is_creature & ~g.is_land]
    lines = ['Evasion (menace and trample are not counted) and blockers for fliers; "C/U|R/M" counts of creature cards:']
    for c in COLS:
        h = cr[cr.cg == c]
        if not len(h):
            lines.append(f'  {COLNAME[c]}: no creatures'); continue

        def cn(f):
            x = h[[f(ev[i]) for i in h.index]]
            return f'{int(x.cu.sum())}|{int((~x.cu).sum())}'
        gf = [i for i in g[g.cg == c].index if grants_flying_row(g.loc[i])]
        lines.append(f'  {COLNAME[c]}: creatures {int(h.cu.sum())}|{int((~h.cu).sum())}; flying {cn(lambda e: "flying" in e[0])}; '
                     f'protection {cn(lambda e: "protection" in e[0])}; unblockable-type {cn(lambda e: "unblockable" in e[0])}; shadow {cn(lambda e: "shadow" in e[0])}; '
                     f'other (fear, skulk, landwalk ...) {cn(lambda e: "other" in e[0])}; any evasion {cn(lambda e: bool(e[0]))}; reach {cn(lambda e: e[1])}; '
                     f'can block fliers (flying or reach) {cn(lambda e: "flying" in e[0] or e[1])}; other cards that give flying {int(g.loc[gf].cu.sum())}|{int((~g.loc[gf].cu).sum())}')
    return lines


def grants_flying_row(r):
    t = r.rtext.lower()
    if not re.search(r'\b(?:gains?|have|has) flying\b', t):
        return False
    return True


def hand_table(g, hk):
    lines = ['Instant-speed interaction by colour ("C/U|R/M" card counts): instant = Instant cards; flash = cards with flash; hand = ability you activate from hand by discarding '
             'the card itself (not pure draw/search/scry/gain-life); swap = return an unblocked attacker to put the card onto the battlefield; cyc-trigger = effect when the card is cycled/discarded:']
    for c in COLS:
        h = g[g.cg == c]
        ents = []
        for k, lab in (('instant', 'instant'), ('flash', 'flash'), ('hand_ability', 'hand'), ('unblocked_swap', 'swap'), ('cycle_trigger', 'cyc-trigger')):
            x = h[[k in hk[i] for i in h.index]]
            ents.append(f'{lab} {int(x.cu.sum())}|{int((~x.cu).sum())}')
        anyc = h[[bool(hk[i]) for i in h.index]]
        lines.append(f'  {COLNAME[c]}: ' + ', '.join(ents) + f' ; any {int(anyc.cu.sum())}|{int((~anyc.cu).sum())}')
    return lines


def type_table(g):
    cr = g[g.is_creature & ~g.is_land]
    cnt = collections.Counter()
    memb = collections.defaultdict(list)
    for r in cr.itertuples():
        for ty in {w for w in r.type.split('//')[0].split('—')[-1].split() if w not in sx.SUPER}:
            cnt[ty] += 1
            memb[ty].append(r.Index)
    lines = ['Top creature types (cards; colours "C/U|R/M"):']
    for ty, n in sorted(cnt.items(), key=lambda kv: (-kv[1], kv[0]))[:10]:
        lines.append(f'  {ty} {n}: ' + cnt_line(g.loc[memb[ty]]) + f' (commons+uncommons {int(g.loc[memb[ty]].cu.sum())})')
    return lines


def mech_table(g, mechs, neut):
    if not mechs:
        return ['Set mechanics: none that are specific to this set were detected.']
    lines = ['Set mechanics (names replaced by neutral labels; the same labels are used in the card texts you are shown):']
    for m in mechs:
        cs = g.loc[g.index.intersection([c.Index for c in m['cards']])]
        ex = m['example']
        lab = m['label']
        ex = neut(ex)
        ex = re.sub(r'\s+', ' ', ex)[:260]
        lines.append(f'  {lab} ({m["kind"]}; {len(cs)} cards, commons+uncommons {int(cs.cu.sum())}; colours C/U|R/M: {cnt_line(cs)}). Example text of a card: "{ex}"')
    return lines


def gold_pair_cards(g, pair):
    sel = g[(g.colors.apply(lambda c: set(c) == set(pair))) & (g.rar == 1) & ~g.is_land]
    return sel.sort_values(['mv', 'text']).head(2)


GENERIC = {'+1/+1 counters': r'\+1/\+1 counters?', 'tokens': r'\btokens?\b', 'life gain': r'\bgain(?:s|ed)? (?:\w+ )?life\b|\blifelink\b',
           'the graveyard': r'\bgraveyard\b', 'sacrifice': r'\bsacrifice'}


def themes_of(row, infos_row, refs_key, mechs, nz):
    """Themes a gold uncommon points at, in priority order: set mechanics, creature types, keywords/card types/subtypes (support references of plan v1), generic themes."""
    th = []
    txt = norm(row.text).lower()
    for m in mechs:
        if mech_regex(m['name']).search(row.text):
            th.append(('mech', m['label'], m))
    for r in refs_key:
        if r.role == 'support' and r.kind == 'ctype':
            th.append(('ctype', r.label, None))
    for r in refs_key:
        if r.role == 'support' and r.kind in ('keyword', 'cardtype', 'nc_sub'):
            th.append((r.kind, r.label, None))
    rt = row.rtext.lower()
    for lab, rx in GENERIC.items():
        if re.search(rx, rt):
            th.append(('generic', lab, None))
    seen, out = set(), []
    for t in th:
        if (t[0], t[1]) not in seen:
            seen.add((t[0], t[1])); out.append(t)
    return out[:3]


def theme_counts(g, infos, refsby, kind, label, mech):
    """have = the card is / has the thing; refer = another card whose text depends on it (plan v1 support reference). Lands excluded."""
    have, refer = [], []
    for i, r in g.iterrows():
        if r.is_land:
            continue
        inf = infos[i]
        rt = r.rtext.lower()
        h = False
        if kind == 'mech':
            h = bool(mech_regex(mech['name']).search(r.text))
        elif kind == 'ctype':
            h = inf['is_creature'] and (label in inf['ctypes'] or inf['changeling'])
        elif kind == 'keyword':
            kw = label.split('|')[0]
            h = kw in inf['kws']
        elif kind == 'cardtype':
            ct = {'instant': 'Instant', 'sorcery': 'Sorcery', 'artifact': 'Artifact', 'enchantment': 'Enchantment', 'planeswalker': 'Planeswalker'}
            h = (ct[label] in inf['cardtypes']) if label in ct else (inf['legendary'] if label == 'legendary' else inf['noncreature'])
        elif kind == 'nc_sub':
            h = label in inf['nc_sub'] or label in inf['mk_tokens']
        elif kind == 'generic':
            h = bool(re.search(GENERIC[label], rt))
        if h:
            have.append(i)
            continue
        if kind in ('ctype', 'keyword', 'cardtype', 'nc_sub'):
            for rr in refsby.get(r.key, []):
                if rr.role == 'support' and rr.kind == kind and rr.label == label:
                    refer.append(i); break
    return have, refer


def archetype_table(g, infos, R, mechs):
    refsby = collections.defaultdict(list)
    for rr in R.itertuples():
        refsby[rr.key].append(rr)
    lines = ['Archetypes (the ten two-colour pairs). For each pair: the gold uncommon(s) of that pair, then for the themes they point at, how many cards of the set are involved: '
             '"have" = the card is / has the thing, "refer" = another card whose text depends on it; counts by colour as "C/U|R/M":']
    for pair in PAIRS:
        golds = gold_pair_cards(g, pair)
        head = f'  {pair}:'
        if not len(golds):
            lines.append(head + ' no gold uncommon in the list.'); continue
        lines.append(head)
        allth, seen = [], set()
        for r in golds.itertuples():
            lines.append(f'    gold uncommon (MV {int(r.mv)} {r.colors}, {r.faces0.strip()}{" " + r.pt if r.pt else ""}): ' + re.sub(r'\s+', ' ', re.sub(r'\s*\n\s*', ' / ', norm(r.text))).strip())
            for t in themes_of(r, infos[r.Index], refsby.get(r.key, []), mechs, None):
                if (t[0], t[1]) not in seen:
                    seen.add((t[0], t[1])); allth.append(t)
        allth = allth[:3]
        if not allth:
            lines.append('    involved cards: no theme could be extracted by the rules (counts not given).')
        for kind, label, mech in allth:
            have, refer = theme_counts(g, infos, refsby, kind, label, mech)
            nice = {'ctype': f'creature type {label}', 'keyword': f'{label.split("|")[0]} (keyword)', 'cardtype': f'{label} cards', 'nc_sub': f'{label} cards (incl. makers)',
                    'mech': label, 'generic': label}[kind]
            ln = f'    theme "{nice}": have {len(have)} [{cnt_line(g.loc[have])}]'
            if kind in ('ctype', 'keyword', 'cardtype', 'nc_sub'):
                ln += f'; refer {len(refer)} [{cnt_line(g.loc[refer])}]'
            lines.append(ln)
    return lines


def build_sheet(st, s, infos, R, mechs_all):
    idx = s.index[s.set == st]
    g = s.loc[idx]
    mechs = mechs_all.get(st, [])
    neut = make_neutralizer(mechs)
    g = g.copy()
    # the text the judge sees: mechanic names -> neutral labels (also used by the tables so labels match)
    g['text'] = [neut(t) for t in g['text']]
    g['rtext'] = [neut(t) for t in g['rtext']]
    ginf = {i: infos[i] for i in idx}
    nl = g[~g.is_land]
    rk = {i: removal_kinds(r) for i, r in nl.iterrows()}
    ev = {i: evasion(r) for i, r in nl.iterrows()}
    hk = {i: hand_kinds(r) for i, r in nl.iterrows()}
    nlg = nl
    out = [f'ENVIRONMENT SHEET (counted by a script from the complete card list of the set the cards come from; the set is not named). '
           f'Cards in list: {len(g)}, nonland {len(nl)}, creatures {int(nl.is_creature.sum())}, commons+uncommons {int(nl.cu.sum())}. '
           f'"C/U" = commons and uncommons, "R/M" = the two higher rarities; "gold" = two or more colours.']
    out += creature_table(nlg)
    out += removal_table(nlg, rk)
    out += evasion_table(nlg, ev)
    out += mech_table(nlg, mechs, neut)
    out += archetype_table(g, ginf, R[R.key.isin(set(g.key))], mechs)
    out += type_table(nlg)
    out += hand_table(nlg, hk)
    return '\n'.join(out), neut, rk, ev, hk


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'sheets'
    s, infos = load()
    infos = dict(enumerate(infos))
    mechs_all = detect_mechanics(s)
    if cmd == 'mechanics':
        for st in sorted(mechs_all):
            print(st, [(m['label'], m['name'], m['n']) for m in mechs_all[st]])
        return
    R = pd.read_csv(HERE / 'refs.csv.gz')
    (HERE / 'sheets').mkdir(exist_ok=True)
    rows = []
    for st in sorted(s['set'].unique()):
        txt, *_ = build_sheet(st, s, infos, R, mechs_all)
        (HERE / 'sheets' / f'{st}.txt').write_text(txt + '\n')
        rows += [dict(set=st, label=m['label'], name=m['name'], kind=m['kind'], n_cards=m['n']) for m in mechs_all[st]]
        print(st, len(txt), 'chars')
    pd.DataFrame(rows).to_csv(HERE / 'mechanics.csv', index=False)


if __name__ == '__main__':
    main()
