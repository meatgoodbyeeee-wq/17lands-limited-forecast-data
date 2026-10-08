"""C8 step 1b: other performance flags from card text (no AI, no outcomes).

  python3 perf.py      -> adds perf columns to profiles.csv.gz, writes perf_coverage.json and review_profiles.csv

Everything is read from the rules text with reminder text removed ('~' = this card), sentence by sentence.
Numbers: 'a'/'an' = 1, X = 3 (typical), "equal to ..." = 2 unless stated otherwise.
"""
import json, re
from pathlib import Path
import pandas as pd

HERE = Path(__file__).resolve().parent
NUM = {'a': 1, 'an': 1, 'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5, 'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10, 'x': 3}
N = r'(a|an|one|two|three|four|five|six|seven|eight|nine|ten|x|\d+)'
SELF = r'(?:this creature|~|it)'


def num(s, default=1):
    s = (s or '').lower()
    return int(s) if s.isdigit() else NUM.get(s, default)


def strip(t):
    return re.sub(r'\([^)]*\)', ' ', t)


PERF = ['draw_n', 'loot', 'select_n', 'impulse_n', 'token_n', 'token_stats', 'token_evasive', 'artifact_token_n',
        'counters_n', 'trick_p', 'trick_t', 'team_pump', 'anthem', 'aura_equip_p', 'aura_equip_t', 'protect', 'counterspell',
        'lifegain_n', 'drain_n', 'face_dmg', 'ramp', 'land_search', 'recur_hand', 'recur_bf', 'discard_opp', 'mill_opp', 'mill_self',
        'evasion_grant', 'n_activated', 'mana_sink', 'n_triggers', 'etb', 'dies_trigger', 'attack_trigger', 'repeatable_value',
        'enters_tapped', 'self_sacrifice', 'symmetric', 'cost_reduction', 'modal']


def perf_profile(btext, type_line):
    txt = strip(btext).lower()
    sents = [x.strip() for x in re.split(r'(?<=[.\n])|•', txt) if x.strip()]
    instantish = 'Instant' in type_line or bool(re.search(r'^flash\b', txt, re.M))
    d = {k: 0 for k in PERF}
    for s in sents:
        rep = bool(re.search(r'^\s*(?:whenever|at the beginning of)|^\s*[^:]*\{t\}[^:]*:|^\s*\{[0-9wubrgcx/]+\}[^:]*:', s))
        # card flow
        for m in re.finditer(r'\b(?<!opponent )(?<!opponents )draws? ' + N + r' cards?', s):
            d['draw_n'] += num(m.group(1))
            d['repeatable_value'] += int(rep)
        if re.search(r'draw cards equal to|draws cards equal to', s):
            d['draw_n'] += 2
        if re.search(r'draw[^.]*, then discard|discard[^.]*, then draw|\brummage\b|\bconnives?\b', s):
            d['loot'] = 1
        for m in re.finditer(r'\b(?:scry|surveil) (\d+|x)', s):
            d['select_n'] += num(m.group(1))
        m = re.search(r'exile the top ' + N + r' cards? of your library[^.]*', s)
        if m and re.search(r'you may (?:play|cast)', s + ' ' + txt[txt.find(s) + len(s): txt.find(s) + len(s) + 120]):
            d['impulse_n'] += num(m.group(1))
        # tokens
        for m in re.finditer(r'\bcreates? ' + N + r' (?:tapped )?(?:(?:and attacking )?)(?:(\d+|x)/(\d+|x) )?([^.]*?)creature tokens?', s):
            n = num(m.group(1))
            p, t = (num(m.group(2), 1), num(m.group(3), 1)) if m.group(2) else (2, 2)
            d['token_n'] += n
            d['token_stats'] += n * (p + t)
            d['token_evasive'] += n * int(bool(re.search(r'flying|menace|trample', s)))
            d['repeatable_value'] += int(rep)
        for m in re.finditer(r'\bcreates? (?:' + N + r' )?(?:tapped )?(treasure|food|clue|blood|map|powerstone|gold|junk|lander) tokens?', s):
            d['artifact_token_n'] += num(m.group(1)) if m.group(1) else 1
        if re.search(r"create a token that's a copy|create (?:a|one) (?:tapped )?token copy", s):
            d['token_n'] += 1; d['token_stats'] += 4
        # counters, pumps
        for m in re.finditer(r'put ' + N + r' \+1/\+1 counters? on', s):
            d['counters_n'] += num(m.group(1)) * (2 if re.search(r'each (?:other )?creature you control', s) else 1)
        m = re.search(r'enters with ' + N + r' (?:additional )?\+1/\+1 counters?', s)
        if m:
            d['counters_n'] += num(m.group(1))
        m = re.search(r'\b(?:up to one )?(?:another )?target (?:attacking |blocking )?creature(?: you control)? gets \+(\d+|x)/\+(\d+|x)[^.]*until end of turn', s) or \
            re.search(r'until end of turn, (?:up to one )?(?:another )?target (?:attacking |blocking )?creature(?: you control)? gets \+(\d+|x)/\+(\d+|x)', s)
        if m and (instantish or 'Instant' in type_line):
            d['trick_p'] = max(d['trick_p'], num(m.group(1))); d['trick_t'] = max(d['trick_t'], num(m.group(2)))
        m = re.search(r'(?:creatures|[a-z]+s) you control get \+(\d+|x)/\+(\d+|x)[^.]*until end of turn', s)
        if m:
            d['team_pump'] = max(d['team_pump'], num(m.group(1)) + num(m.group(2)))
        m = re.search(r'(?:other )?(?:[a-z]+ )?(?:creatures|[a-z]+s) you control get \+(\d+)/\+(\d+)(?! until)', s)
        if m and 'until end of turn' not in s:
            d['anthem'] = max(d['anthem'], int(m.group(1)) + int(m.group(2)))
        m = re.search(r'(?:equipped|enchanted) creature gets \+(\d+|x)/\+(\d+|x)', s)
        if m and 'until end of turn' not in s:
            d['aura_equip_p'] = max(d['aura_equip_p'], num(m.group(1))); d['aura_equip_t'] = max(d['aura_equip_t'], num(m.group(2)))
        # protection / interaction
        if re.search(r'(?:target creature you control|creatures you control|target creature|another target creature|target permanent you control)[^.]*\b(?:gains?|have|has)\b[^.]*\b(?:hexproof|indestructible|protection from|shroud|ward)\b', s) \
                or re.search(r"can't be the targets? of", s):
            d['protect'] = 1
        if re.search(r'\bcounter target (?:[a-z ]*)?(?:spell|ability)', s):
            d['counterspell'] = 1
        # life
        for m in re.finditer(r'\byou gain ' + N + r' life|\bgains? ' + N + r' life', s):
            d['lifegain_n'] += num(m.group(1) or m.group(2))
            d['repeatable_value'] += int(rep)
        for m in re.finditer(r'(?:each opponent|target opponent|target player|that player|defending player) loses ' + N + r' life', s):
            d['drain_n'] += num(m.group(1))
        for m in re.finditer(r'deals? ' + N + r' damage to (?:each opponent|target player|target opponent|that player|any target|defending player)', s):
            d['face_dmg'] += num(m.group(1))
        # mana
        if re.search(r'\{t\}: add', s) and 'Land' not in type_line:
            d['ramp'] = 1
        if re.search(r'search your library for (?:a|up to \w+) (?:basic )?(?:land|forest|island|swamp|mountain|plains)', s):
            d['land_search'] = 1
        if re.search(r'(?:costs?|cost) \{\d\} less to cast|spells you cast cost', s):
            d['cost_reduction'] = 1
        # graveyard / opponent resources
        if re.search(r'return [^.]*card[^.]* from your graveyard to your hand', s):
            d['recur_hand'] = 1
        if re.search(r'return [^.]*creature card[^.]* from (?:your|a) graveyard to the battlefield', s):
            d['recur_bf'] = 1
        m = re.search(r'(?:target|each) opponent discards ' + N + r' cards?|target player discards ' + N + r' cards?', s)
        if m:
            d['discard_opp'] += num(m.group(1) or m.group(2))
        m = re.search(r'(target player|target opponent|each opponent|you|each player)?\s*mills? ' + N + r' cards?', s)
        if m:
            who = m.group(1) or 'you'
            d['mill_self' if who == 'you' else 'mill_opp'] += num(m.group(2))
        # evasion granted to others
        if re.search(r'(?:target creature|creatures you control|equipped creature|enchanted creature|other [a-z]+ you control)[^.]*\b(?:gains?|has|have)\b[^.]*\b(?:flying|trample|menace|can\'t be blocked)', s) \
                or re.search(r"target creature can't be blocked this turn", s):
            d['evasion_grant'] = 1
        # structure
        if re.match(r'^\s*(?:\{[^}]+\}|[^:]{0,40}\{t\})[^:]*:', s) and not re.search(r'\{t\}: add', s):
            d['n_activated'] += 1
            if re.search(r'\{\d+\}|\{x\}|\{[wubrg]\}', s.split(':')[0]):
                d['mana_sink'] = 1
        if re.search(r'^\s*(?:whenever|at the beginning of|when)\b', s):
            d['n_triggers'] += 1
        if re.search(r'^\s*when(?:ever)? ' + SELF + r' enters|^\s*when(?:ever)? ' + SELF + r' (?:enters|or another)', s) or re.search(r'when this \w+ enters', s):
            d['etb'] = 1
        if re.search(r'when(?:ever)? (?:this creature|~) dies', s):
            d['dies_trigger'] = 1
        if re.search(r'whenever (?:this creature|~) attacks|whenever (?:this creature|~) deals combat damage', s):
            d['attack_trigger'] = 1
        if re.search(r'(?:this creature|~|this land|this artifact) enters tapped', s):
            d['enters_tapped'] = 1
        if re.search(r'sacrifice (?:this creature|~)(?: at| unless)|at the beginning of [^.]*sacrifice (?:this|~)', s):
            d['self_sacrifice'] = 1
        if re.search(r'\beach player\b|\ball players\b', s):
            d['symmetric'] = 1
    if re.search(r'choose (?:one|two|one or both|any number)|\bspree\b', txt) or '//' in btext:
        d['modal'] = 1
    return d


JA = {'draw_n': 'ドロー枚数', 'loot': 'ルーター', 'select_n': '占術・諜報の枚数', 'impulse_n': '衝動的ドロー枚数',
      'token_n': 'クリーチャー・トークン数', 'token_stats': 'トークンのP+T合計', 'token_evasive': '回避能力付きトークン数',
      'artifact_token_n': '宝物/食物/手がかり等の数', 'counters_n': '+1/+1カウンター数', 'trick_p': 'インスタント強化のP',
      'trick_t': 'インスタント強化のT', 'team_pump': '全体一時強化(P+T)', 'anthem': '常在の全体強化(P+T)',
      'aura_equip_p': '装備/オーラのP', 'aura_equip_t': '装備/オーラのT', 'protect': '自軍を守る(呪禁・破壊不能等)',
      'counterspell': '打ち消し', 'lifegain_n': 'ライフ獲得量', 'drain_n': '相手のライフ喪失量', 'face_dmg': 'プレイヤーへのダメージ',
      'ramp': 'マナ加速(マナ能力)', 'land_search': '土地サーチ', 'recur_hand': '墓地→手札', 'recur_bf': '墓地→戦場',
      'discard_opp': '相手の手札破壊枚数', 'mill_opp': '相手の切削枚数', 'mill_self': '自分の切削枚数', 'evasion_grant': '回避能力の付与',
      'n_activated': '起動型能力の数', 'mana_sink': 'マナの使い道あり', 'n_triggers': '誘発型能力の数', 'etb': 'ETB効果',
      'dies_trigger': '死亡時誘発', 'attack_trigger': '攻撃/戦闘ダメージ誘発', 'repeatable_value': '繰り返し得られる価値の数',
      'enters_tapped': 'タップ状態で戦場に出る', 'self_sacrifice': '自身を生贄にするデメリット', 'symmetric': '対称効果', 'cost_reduction': 'コスト軽減',
      'modal': 'モード選択・両面'}


def main():
    p = pd.read_csv(HERE / 'profiles.csv.gz', keep_default_na=False)
    p = p[[c for c in p.columns if c not in PERF]]
    f = pd.DataFrame([perf_profile(b, t) for b, t in zip(p['btext'], p['type_line'])])
    p = pd.concat([p.reset_index(drop=True), f], axis=1)
    p.to_csv(HERE / 'profiles.csv.gz', index=False, compression='gzip')
    cov = {JA[k]: {'cards': int((f[k] > 0).sum()), 'share': round(float((f[k] > 0).mean()), 3)} for k in PERF}
    json.dump(cov, open(HERE / 'perf_coverage.json', 'w'), indent=1, ensure_ascii=False)
    # review file: previous review columns + perf summary
    r = pd.read_csv(HERE / 'review_profiles.csv', encoding='utf-8-sig')
    r = r[[c for c in r.columns if c != 'その他の性能']]
    def summ(row):
        return ' / '.join(f'{JA[k]}={row[k]}' if not isinstance(row[k], (int,)) or row[k] not in (0, 1) else JA[k]
                          for k in PERF if row[k])
    r.insert(r.columns.get_loc('本文'), 'その他の性能', f.apply(summ, axis=1).to_numpy())
    r.to_csv(HERE / 'review_profiles.csv', index=False, encoding='utf-8-sig')
    for k, v in cov.items():
        print(f'{k:24s} {v["cards"]:5d} ({v["share"]:.1%})')


if __name__ == '__main__':
    main()
