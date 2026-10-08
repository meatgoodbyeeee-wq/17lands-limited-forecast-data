"""C8 step 1b: other performance flags from card text (no AI, no outcomes).

  python3 perf.py      -> adds perf columns to profiles.csv.gz, writes perf_coverage.json and review_profiles.csv
  python3 audit.py     -> coverage against the C5 tags (an independent AI reading), used to find missed wordings

The full rules text is read INCLUDING reminder text (reminder text spells out what keyword mechanics do:
mobilize, amass, offspring, prowess, battle cry, cycling, convoke, ...), sentence by sentence; '~' = this card.
Numbers: 'a'/'an' = 1, X = 3 (typical), "half" / "equal to ..." / "for each ..." = 2 unless stated otherwise.
The removal profile (extract.py, step 1) is unchanged and still reads the text without reminder text.
"""
import json, re
from pathlib import Path
import pandas as pd

HERE = Path(__file__).resolve().parent
NUM = {'a': 1, 'an': 1, 'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5, 'six': 6, 'seven': 7, 'eight': 8, 'nine': 9,
       'ten': 10, 'x': 3, 'twice': 2, 'half': 2}
N = r'(a|an|one|two|three|four|five|six|seven|eight|nine|ten|x|half|\d+)'
SELF = r'(?:this creature|~|it|this vehicle|this artifact|this enchantment)'
KWS = r'flying|trample|menace|haste|double strike|first strike|deathtouch|lifelink|vigilance|indestructible|hexproof|ward|reach|can\'t be blocked'


def num(s, default=1):
    s = (s or '').lower()
    return int(s) if s.isdigit() else NUM.get(s, default)


PERF = ['draw_n', 'loot', 'select_n', 'impulse_n', 'token_n', 'token_stats', 'token_evasive', 'artifact_token_n',
        'counters_n', 'trick_p', 'trick_t', 'team_pump', 'pump_activated', 'pump_other', 'anthem', 'anthem_kw',
        'aura_equip_p', 'aura_equip_t', 'aura_equip_kw', 'vehicle', 'protect', 'counterspell',
        'lifegain_n', 'drain_n', 'face_dmg', 'ramp', 'fixing', 'land_search', 'recur_hand', 'recur_bf', 'recur_self',
        'discard_opp', 'mill_opp', 'mill_self', 'evasion_grant', 'n_activated', 'mana_sink', 'n_triggers', 'etb',
        'dies_trigger', 'attack_trigger', 'repeatable_value', 'enters_tapped', 'self_sacrifice', 'symmetric',
        'cost_reduction', 'alt_cost', 'cycling', 'modal']


TOKEN_REMINDER = r"this token|it's an artifact with|it's an? [a-z ]*artifact|it's a [a-z ]*enchantment with|discard this card: draw a card|discard this card: search"


def sentences(btext):
    """rules text + reminder text, split into sentences; reminder sentences that only describe a token's or cycling's
    own ability are dropped (the token itself is counted, its ability is not counted again)."""
    t = btext.lower().replace('“', '"').replace('”', '"')
    parts = re.split(r'(\([^)]*\))', t)
    out = []
    for p in parts:
        if p.startswith('(') and re.search(TOKEN_REMINDER, p):
            continue
        p = p.strip('()')
        out += [x.strip(' ."') for x in re.split(r'(?<=[.\n])|•|"', p) if x.strip(' ."')]
    return out


def pump_amount(s):
    m = re.search(r'gets? \+(\d+|x)/\+(\d+|x)', s)
    if m:
        return num(m.group(1)), num(m.group(2))
    m = re.search(r'base power and toughness (\d+)/(\d+) until end of turn', s)
    if m:
        return max(int(m.group(1)) - 2, 0), max(int(m.group(2)) - 2, 0)
    return None


def perf_profile(btext, type_line):
    sents = sentences(btext)
    low = btext.lower()
    instantish = 'Instant' in type_line or bool(re.search(r'^flash\b', low, re.M))
    d = {k: 0 for k in PERF}
    for i, s in enumerate(sents):
        nxt = ' '.join(sents[i + 1:i + 3])
        activated = bool(re.match(r'^\s*(?:[a-z\'\- ]+ — )?(?:\{[^}]+\}|[a-z]+ [a-z ]*?\{t\}|tap an untapped)[^:]{0,80}:', s)) and ':' in s
        rep = activated or bool(re.search(r'^\s*(?:whenever|at the beginning of)', s))
        # ---- card flow
        for m in re.finditer(r'(?<!opponent )(?<!opponents )\bdraws? ' + N + r' (?:additional )?cards?', s):
            d['draw_n'] += num(m.group(1)); d['repeatable_value'] += int(rep)
        if re.search(r'draws? (?:cards equal to|that many cards|a card for each|\d+ˣ cards|x cards)', s):
            d['draw_n'] += 2
        m = re.search(r'put ' + N + r' of (?:them|those cards) into your hand|put (?:a|one|that) (?:[a-z ]*)?card[^.]* into your hand|put (?:any number|up to \w+) of them into your hand', s)
        if m:
            d['draw_n'] += num(m.group(1)) if m.group(1) else 1
        if re.search(r'\bdraw[^.]*\b(?:then|and) discard|^then discard|discard[^.]*:\s*draw|discard[^.]*, then draw|\brummage\b|\bconnives?\b|\blearn\b', s) or \
                (re.search(r'\bdraws? ', s) and re.match(r'^\s*then discard', nxt)):
            d['loot'] = 1
        for m in re.finditer(r'\b(?:scry|surveil) (\d+|x)', s):
            d['select_n'] += num(m.group(1))
        m = re.search(r'(?:look at|reveal) the top ' + N + r' cards? of your library', s)
        if m:
            d['select_n'] += num(m.group(1))
        m = re.search(r'exile the top ' + N + r' cards? of your library', s)
        if m and re.search(r'you may (?:play|cast)', s + ' ' + nxt):
            d['impulse_n'] += num(m.group(1))
        if re.search(r'\bdiscover \d+|\bdiscover x|\bcascade\b', s):
            d['impulse_n'] += 1
        # ---- tokens
        for m in re.finditer(r'\bcreates? ' + N + r' (?:tapped )?(?:and attacking )?(?:(\d+|x)/(\d+|x) )?([^.]*?)creature tokens?', s):
            n = num(m.group(1)); p, t = (num(m.group(2), 1), num(m.group(3), 1)) if m.group(2) else (2, 2)
            d['token_n'] += n; d['token_stats'] += n * (p + t)
            d['token_evasive'] += n * int(bool(re.search(r'flying|menace|trample', m.group(4) + ' ' + s[m.end():m.end() + 40])))
            d['repeatable_value'] += int(rep)
        m = re.search(r'\bcreates? [a-z\' -]+, an? (?:legendary )?(\d+)/(\d+) [^.]*creature token', s)
        if m:
            d['token_n'] += 1; d['token_stats'] += int(m.group(1)) + int(m.group(2))
        m = re.search(r'\bcreates? (?:a|an|one) (\d+)/(\d+) token copy|token that\'s a copy|token copy of', s)
        if m:
            d['token_n'] += 1; d['token_stats'] += (int(m.group(1)) + int(m.group(2))) if m.lastindex and m.group(1) else 4
        m = re.search(r'\bamass [a-z]+ (\d+|x)|\bincubate (\d+|x)', s)
        if m:
            d['token_n'] += 1; d['counters_n'] += num(m.group(1) or m.group(2))
        for m in re.finditer(r'\bcreates? (?:' + N + r' )?(?:tapped )?(?:[a-z]+ )?(treasure|food|clue|blood|map|powerstone|gold|junk|lander|mutagen|heartwood|role) tokens?', s):
            d['artifact_token_n'] += num(m.group(1)) if m.group(1) else 1
        if re.search(r'\binvestigate\b', s):
            d['artifact_token_n'] += 2 if re.search(r'investigate (?:twice|x times)', s) else 1
        # ---- counters and pumps
        for m in re.finditer(r'put ' + N + r' \+1/\+1 counters?', s):
            d['counters_n'] += num(m.group(1)) * (2 if re.search(r'each (?:other )?creature you control', s) else 1)
        if re.search(r'put a number of \+1/\+1 counters|distribute (\w+) \+1/\+1 counters|double the number of \+1/\+1 counters|\bproliferate\b|\+1/\+1 counters? equal to', s):
            m = re.search(r'distribute (\w+) \+1/\+1', s)
            d['counters_n'] += num(m.group(1)) if m else 2
        m = re.search(r'enters with ' + N + r' (?:additional )?\+1/\+1 counters?', s)
        if m:
            d['counters_n'] += num(m.group(1))
        pa = pump_amount(s)
        if pa and 'until end of turn' in (s + ' ' + nxt[:60]):
            team = re.search(r'creatures you control get|[a-z]+s? you control get|each other attacking creature gets|attacking creatures you control get', s)
            tgt = re.search(r'target (?:attacking |blocking )?(?:[a-z]+ )?creature', s)
            if team:
                d['team_pump'] = max(d['team_pump'], sum(pa))
            elif activated:
                d['pump_activated'] = max(d['pump_activated'], sum(pa))
            elif tgt and instantish and not re.search(r'^\s*(?:when|whenever|at the beginning)', s):
                d['trick_p'] = max(d['trick_p'], pa[0]); d['trick_t'] = max(d['trick_t'], pa[1])
            else:
                d['pump_other'] = max(d['pump_other'], sum(pa))
        m = re.search(r'(?:you control get|creature you control gets|creatures you control get) \+(\d+|x)/\+(\d+|x)', s)
        if m and 'until end of turn' not in s and not re.search(r'^\s*(?:when|whenever)', s):
            d['anthem'] = max(d['anthem'], num(m.group(1)) + num(m.group(2)))
        if re.search(r'(?:other )?[a-z ]*?(?:creatures|[a-z]+s) you control[^.]{0,40}? (?:have|gain) [^.]*\b(?:' + KWS + r')\b', s) and 'until end of turn' not in s:
            d['anthem_kw'] = 1
        m = re.search(r'(?:equipped|enchanted) (?:creature|permanent)[^.]*?gets \+(\d+|x)/\+(\d+|x)', s)
        if m and 'until end of turn' not in s:
            d['aura_equip_p'] = max(d['aura_equip_p'], num(m.group(1))); d['aura_equip_t'] = max(d['aura_equip_t'], num(m.group(2)))
        if re.search(r'(?:equipped|enchanted) creature (?:gets [^.]*? and )?(?:has|gains) [^.]*\b(?:' + KWS + r')\b', s):
            d['aura_equip_kw'] = 1
        if re.search(r'\breconfigure\b', s):
            d['aura_equip_kw'] = 1
        if re.search(r'\b(?:plot|sneak|warp|foretell|evoke|dash|madness|miracle|ninjutsu|prototype|emerge|spectacle|surge|overload|bestow|mutate|disguise|morph|cloak)\b', s):
            d['alt_cost'] = 1
        if 'Vehicle' in type_line or re.search(r'\bcrew \d', s):
            d['vehicle'] = 1
        # ---- protection / interaction
        if re.search(r'(?:target creature you control|creatures you control|target creature|another target creature|target permanent you control|target [a-z]+ you control)[^.]*\b(?:gains?|have|has|get [^.]*and gain)\b[^.]*\b(?:hexproof|indestructible|protection from|shroud)\b', s) \
                or re.search(r"can't be the targets? of|\bphase out\b", s):
            d['protect'] = 1
        if re.search(r'\bcounter target (?:[a-z ,]*)?(?:spell|ability)', s):
            d['counterspell'] = 1
        # ---- life
        for m in re.finditer(r'\byou gain ' + N + r' life|\bgains? ' + N + r' life', s):
            d['lifegain_n'] += num(m.group(1) or m.group(2)); d['repeatable_value'] += int(rep)
        if re.search(r'you gain life equal|gain that much life', s) and 'lifelink' not in s:
            d['lifegain_n'] += 2
        for m in re.finditer(r'(?:each opponent|target opponent|target player|that player|defending player|its controller|each player)[^.]{0,40}? loses? ' + N + r' life', s):
            d['drain_n'] += num(m.group(1))
        for m in re.finditer(r'deals? ' + N + r' damage to (?:each opponent|each of your opponents|target player|target opponent|that player|any target|defending player|each player)', s):
            d['face_dmg'] += num(m.group(1))
        # ---- mana
        if 'Land' not in type_line and (re.search(r'\{t\}[^:]*: add|lands you control have "?\{t\}|\badd \{[wubrgc]\}|adds? (?:an )?additional|create[^.]*(?:treasure|powerstone)', s)):
            d['ramp'] = 1
        if re.search(r'add (?:one mana of any color|\{[wubrg]\} or \{[wubrg]\}|\{[wubrg]\}, \{[wubrg]\}|mana of any|two mana in any combination)', s) or \
                re.search(r'create[^.]*treasure', s):
            d['fixing'] = 1
        if re.search(r'search your library for (?:a|an|up to \w+|two)[^.]*?(?:land|forest|island|swamp|mountain|plains|gate|desert|cave|town)', s) or \
                re.search(r'land card[^.]* into your hand|landcycling|\b[a-z]+cycling \{', s) or re.search(r'put (?:a|up to one) land card [^.]*onto the battlefield', s):
            d['land_search'] = 1
        if re.search(r'costs? \{\d+\} less|costs? \{x\} less|less to cast for each|\bconvoke\b|\baffinity for\b|\bimprovise\b|\bdelve\b|spells you cast cost', s):
            d['cost_reduction'] = 1
        # ---- graveyard / opponent resources
        if re.search(r'return [^.]* from your graveyard to your hand|return (?:that card|it) to your hand', s) and not re.search(r'return (?:this card|~) from', s):
            d['recur_hand'] = 1
        if re.search(r'(?:return|put) [^.]*card[^.]* from (?:your|a|their|defending player\'s|an opponent\'s) graveyard (?:to|onto) the battlefield|return (?:that card|it) to the battlefield under (?:your|its owner\'s) control', s) \
                and not re.search(r'return (?:that card|it) to the battlefield under its owner\'s control at the beginning', s):
            d['recur_bf'] = 1
        if re.search(r'return (?:~|this card) from your graveyard|cast (?:~|this card|this spell) from your graveyard|\b(?:flashback|escape|unearth|disturb|harmonize|embalm|eternalize|renew|retrace|jump-start|encore|blitz)\b', s):
            d['recur_self'] = 1
        m = re.search(r'(?:target|each) (?:opponent|player) discards ' + N + r'|discards (?:half|that card|a card)|discards the chosen|exile [^.]* from their hand|you choose [^.]*card from it', s)
        if m and 'you discard' not in s:
            d['discard_opp'] += num(m.group(1)) if m.lastindex and m.group(1) else 1
        m = re.search(r'(target players?|target opponent|each opponent|defending player|that player|you|each player)?(?: each)?\s*mills? ' + N + r' cards?', s) or \
            re.search(r'(you)(?: may)? mill (x) cards|(you)(?: may)? mill cards equal', s)
        if m:
            d['mill_self' if (m.group(1) or 'you') == 'you' else 'mill_opp'] += num(m.group(2)) if m.lastindex and m.lastindex >= 2 and m.group(2) else 2
        elif re.search(r'(?:opponent|player) (?:mills|exiles cards from the top of their library)|mills cards equal|mills half', s):
            d['mill_opp'] += 2
        # ---- evasion granted to others
        if re.search(r'(?:target creature|creatures you control|equipped creature|enchanted creature|other [a-z]+ you control|that creature)[^.]*\b(?:gains?|has|have)\b[^.]*\b(?:flying|trample|menace|can\'t be blocked)', s) \
                or re.search(r"target creature can't be blocked this turn|that creature can't be blocked", s):
            d['evasion_grant'] = 1
        # ---- structure
        if activated and not re.search(r'\{t\}[^:]*: add', s):
            d['n_activated'] += 1
            if re.search(r'\{\d+\}|\{x\}|\{[wubrg](?:/[wubrgp])?\}', s.split(':')[0]):
                d['mana_sink'] = 1
        if re.search(r'^\s*(?:[a-z\'\- ]+ — )?(?:whenever|at the beginning of|when)\b', s):
            d['n_triggers'] += 1
        if re.search(r'when(?:ever)? ' + SELF + r' (?:enters|or another [^.]* enters|enters or)|when this \w+ enters|when you unlock this door|enters prepared', s):
            d['etb'] = 1
        if re.search(r'when(?:ever)? (?:this creature|~|enchanted creature|equipped creature) (?:dies|is put into)|enters or dies|or dies\b|leaves the battlefield|whenever (?:one or more )?(?:another |other )?[a-z ]*creatures? (?:you control )?(?:with [a-z]+ )?dies?\b|whenever a creature dies', s):
            d['dies_trigger'] = 1
        if re.search(r'whenever [^.]*?\battacks?\b|enters or attacks|deals? combat damage to (?:a player|an opponent|one or more)|whenever (?:equipped|enchanted) creature attacks', s):
            d['attack_trigger'] = 1
        if re.search(r'(?:this creature|~|this land|this artifact|this permanent) enters tapped|enters the battlefield tapped', s):
            d['enters_tapped'] = 1
        if re.search(r'sacrifice (?:this creature|~)(?: at| unless)|at the beginning of [^.]*sacrifice (?:this|~)|you lose the game', s):
            d['self_sacrifice'] = 1
        if re.search(r'\beach player\b|\ball players\b|all creatures have', s):
            d['symmetric'] = 1
    if re.search(r'\b[a-z]*cycling\b', low):
        d['cycling'] = 1
    if re.search(r'choose (?:one|two|three|one or both|any number|up to)|\bspree\b|worth of modes|enters prepared|\bprototype\b|\bomen\b|\badventure\b', low) or '//' in btext:
        d['modal'] = 1
    return d


JA = {'draw_n': 'ドロー枚数', 'loot': 'ルーター', 'select_n': '占術・諜報・上を見る枚数', 'impulse_n': '衝動的ドロー枚数',
      'token_n': 'クリーチャー・トークン数', 'token_stats': 'トークンのP+T合計', 'token_evasive': '回避能力付きトークン数',
      'artifact_token_n': '宝物/食物/手がかり等の数', 'counters_n': '+1/+1カウンター数', 'trick_p': 'インスタント強化のP',
      'trick_t': 'インスタント強化のT', 'team_pump': '全体一時強化(P+T)', 'pump_activated': '起動型の強化(P+T)', 'pump_other': 'その他の一時強化(P+T)',
      'anthem': '常在の全体強化(P+T)', 'anthem_kw': '自軍へのキーワード付与(常在)',
      'aura_equip_p': '装備/オーラのP', 'aura_equip_t': '装備/オーラのT', 'aura_equip_kw': '装備/オーラのキーワード付与', 'vehicle': '機体',
      'protect': '自軍を守る(呪禁・破壊不能等)', 'counterspell': '打ち消し', 'lifegain_n': 'ライフ獲得量', 'drain_n': '相手のライフ喪失量',
      'face_dmg': 'プレイヤーへのダメージ', 'ramp': 'マナ加速', 'fixing': '色マナ補正', 'land_search': '土地サーチ',
      'recur_hand': '墓地→手札', 'recur_bf': '墓地→戦場', 'recur_self': '自身を墓地から再利用',
      'discard_opp': '相手の手札破壊枚数', 'mill_opp': '相手の切削枚数', 'mill_self': '自分の切削枚数', 'evasion_grant': '回避能力の付与',
      'n_activated': '起動型能力の数', 'mana_sink': 'マナの使い道あり', 'n_triggers': '誘発型能力の数', 'etb': 'ETB効果',
      'dies_trigger': '死亡・離脱時誘発', 'attack_trigger': '攻撃/戦闘ダメージ誘発', 'repeatable_value': '繰り返し得られる価値の数',
      'enters_tapped': 'タップ状態で戦場に出る', 'self_sacrifice': '自身を失うデメリット', 'symmetric': '対称効果', 'cost_reduction': 'コスト軽減', 'cycling': 'サイクリング', 'alt_cost': '代替コスト(予告・ワープ等)',
      'modal': 'モード選択・両面'}
FLAGS = {'loot', 'anthem_kw', 'aura_equip_kw', 'vehicle', 'protect', 'counterspell', 'ramp', 'fixing', 'land_search', 'recur_hand',
         'recur_bf', 'recur_self', 'evasion_grant', 'mana_sink', 'etb', 'dies_trigger', 'attack_trigger', 'enters_tapped',
         'self_sacrifice', 'symmetric', 'cost_reduction', 'alt_cost', 'cycling', 'modal'}


# Fallback for wordings the rules cannot read: where the independent C5 AI reading has the matching tag but the
# rules found nothing, the field is filled from C5 (presence = 1; counts = the C5 level, 1 minor / 2 main).
FALLBACK = {'DR': 'draw_n', 'SC': 'select_n', 'TK': 'token_n', 'CL': 'artifact_token_n', 'PC': 'counters_n', 'PT': 'pump_other',
            'AN': 'anthem', 'EQ': 'aura_equip_kw', 'CS': 'counterspell', 'RC': 'recur_hand', 'DS': 'discard_opp', 'MI': 'mill_opp',
            'DL': 'drain_n', 'RM': 'ramp', 'FX': 'fixing', 'CR': 'cost_reduction', 'SK': 'mana_sink', 'ET': 'etb', 'DY': 'dies_trigger',
            'AT': 'attack_trigger', 'CH': 'modal'}
RELATED = {'SC': ['select_n', 'loot'], 'TK': ['token_n'], 'PT': ['trick_p', 'trick_t', 'team_pump', 'pump_activated', 'pump_other'],
           'AN': ['anthem', 'anthem_kw'], 'EQ': ['aura_equip_p', 'aura_equip_t', 'aura_equip_kw', 'vehicle'], 'RC': ['recur_hand', 'recur_bf', 'recur_self'],
           'DL': ['drain_n', 'face_dmg'], 'FX': ['land_search', 'fixing'], 'CR': ['cost_reduction', 'alt_cost']}


def fallback(f, ids):
    import sys
    sys.path.insert(0, str(HERE.parents[0] / 'c5_atomic_effects'))
    import check_raw as cr
    raw, _ = cr.load_raw()
    filled = [[] for _ in range(len(f))]
    for i, cid in enumerate(ids):
        tags = raw.get(cid, ([], {}))[1]
        for tag, col in FALLBACK.items():
            lv = tags.get(tag, 0)
            if lv and not any(f.at[i, c] for c in RELATED.get(tag, [col])):
                f.at[i, col] = lv if col not in FLAGS else 1
                if tag == 'TK':
                    f.at[i, 'token_stats'] = 4 * lv
                filled[i].append(col)
    return f, filled


def main():
    p = pd.read_csv(HERE / 'profiles.csv.gz', keep_default_na=False)
    p = p[[c for c in p.columns if c not in PERF and c not in ('pump_activated', 'pump_other')]]
    f = pd.DataFrame([perf_profile(b, t) for b, t in zip(p['btext'], p['type_line'])])
    rule_only = f.copy()
    f, filled = fallback(f, p['id'].tolist())
    f['filled_from_c5'] = [';'.join(x) for x in filled]
    p = p[[c for c in p.columns if c != 'filled_from_c5']]
    p = pd.concat([p.reset_index(drop=True), f], axis=1)
    print('fields filled from C5:', sum(len(x) for x in filled), 'cards:', sum(bool(x) for x in filled))
    p.to_csv(HERE / 'profiles.csv.gz', index=False, compression='gzip')
    cov = {JA[k]: {'cards': int((f[k] > 0).sum()), 'share': round(float((f[k] > 0).mean()), 3),
                   'by_rules': int((rule_only[k] > 0).sum())} for k in PERF}
    json.dump(cov, open(HERE / 'perf_coverage.json', 'w'), indent=1, ensure_ascii=False)
    r = pd.read_csv(HERE / 'review_profiles.csv', encoding='utf-8-sig')
    r = r[[c for c in r.columns if c != 'その他の性能']]
    summ = lambda row: ' / '.join(JA[k] if k in FLAGS else f'{JA[k]}={int(row[k])}' for k in PERF if row[k])
    r.insert(r.columns.get_loc('本文'), 'その他の性能', f.apply(summ, axis=1).to_numpy())
    r = r[[c for c in r.columns if c != 'C5から補完した項目']]
    r.insert(r.columns.get_loc('本文'), 'C5から補完した項目', [' / '.join(JA[c] for c in x) for x in filled])
    r.to_csv(HERE / 'review_profiles.csv', index=False, encoding='utf-8-sig')


if __name__ == '__main__':
    main()
