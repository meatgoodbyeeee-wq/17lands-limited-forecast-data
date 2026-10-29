#!/usr/bin/env python3
"""One-line prediction reason per card from the B11g contributions (TRK plan, user decision 2026-10-28/29).

The detail screen of the Pages site shows, instead of the numeric breakdown, one or two plain sentences "〇〇だから、〇〇。"
(qualitative, no numbers). Material = the largest raising / lowering factors of THIS card's B11g prediction only:
  structured part: SHAP value per feature, summed per feature group below; text part: Ridge coefficient x TF-IDF per n-gram;
  each centred on the set (contribution minus the set mean of that contribution), so factors explain "higher / lower than this set's average card".
A Sonnet subagent per batch writes the sentences from the material only (prompt_reasons.txt); `check` rejects numbers, missing
"から", wrong length, and missing / extra ids. Output gih-reasons.json is local (TRK predictions are not pushed to public repositories).

  python3 reasons_b11g.py prepare --explain export_tmp/trk_b11g_explain.json.gz --cards <pages>/data/trk/target.json.gz   # reasons/input/bNN.txt
  (one Sonnet subagent per batch: prompt_reasons.txt with {DIR} and {BATCH} -> reasons/raw/bNN.json)
  python3 reasons_b11g.py check
  python3 reasons_b11g.py merge --out <pages>/data/trk/gih-reasons.json
"""
import argparse, gzip, json, re
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
OUT = HERE / 'reasons'
BATCH = 40
TOP = 3            # factors per direction given to the writer
MIN_PP = 0.25      # a factor smaller than this (final pp, centred) is not material

C5 = 'c5_'
GROUPS = {  # label (ja, en) : features. Every B11g feature must be in exactly one group (checked).
    ('AIの総合評価（専門家の評価を手本にしたG3）', 'AI overall grade (G3, modelled on expert reviews)'): ['g3', 'g3_z'],
    ('除去・妨害の性能', 'removal and interaction'): [
        'interaction', 'interaction_per_mv', 'cheap_interaction', 'interaction_condition_count', 'clean_interaction',
        'quality_immediate_removal', 'quality_broad_removal', 'kw_destroy', 'kw_exile', 'kw_damage', 'kw_counter', 'targets_creature',
        'llm_removal', 'llm_sweeper', 'c4_DMG', 'c4_TGT', 'c4_SPD', 'c4_role_R'] + [C5 + x for x in 'KD KX DM DA MS BN TP FT ED CS PA SW'.split()],
    ('カードを増やす・選ぶ力', 'card advantage and selection'): [
        'kw_draw', 'kw_search', 'kw_return', 'kw_surveil', 'kw_scry', 'card_advantage', 'card_advantage_per_mv', 'quality_etb_card_value',
        'quality_repeatable_card_value', 'llm_cards', 'c4_role_V'] + [C5 + x for x in 'DR SC RC TU IM CL'.split()],
    ('繰り返し使える・長期戦で伸びる', 'repeatable value and late-game scaling'): [
        'llm_repeat', 'llm_sink', 'c4_SCALE', 'has_eot', 'has_x_cost'] + [C5 + x for x in 'UP SK'.split()],
    ('サイズとマナ効率', 'size and mana efficiency'): [
        'power', 'toughness', 'power_per_mv', 'toughness_per_mv', 'stats_per_mv', 'c4_SWG', 'llm_bodies', 'kw_token', 'c5_RATE', 'c5_TK'],
    ('攻撃力・回避能力', 'offence and evasion'): [
        'evasion', 'evasion_power_efficiency', 'kw_flying', 'kw_menace', 'kw_trample', 'kw_haste', 'kw_first_strike', 'kw_double_strike',
        'c4_EVA', 'c4_role_A', 'c4_role_F'] + [C5 + x for x in 'FL MN HS FS AT CLK'.split()],
    ('守りとライフ', 'defence and life'): [
        'kw_reach', 'kw_vigilance', 'kw_deathtouch', 'kw_lifelink', 'kw_gain', 'c4_DRAIN', 'c4_role_D'] + [C5 + x for x in 'DT LL VG RH DL BLK'.split()],
    ('除去への強さ・損の少なさ', 'resilience and card-disadvantage risk'): [
        'kw_hexproof', 'kw_ward', 'is_aura', 'is_equipment', 'is_vehicle', 'c4_VULN'] + [C5 + x for x in 'IN EQ'.split()],
    ('マナ総量', 'mana value'): ['mv', 'c4_TURN'],
    ('レアリティ', 'rarity'): ['rarity_ord'],
    ('色・色拘束', 'colours and colour requirements'): ['n_colors', 'mana_symbols', 'is_multicolor', 'is_colorless'],
    ('条件・欠点', 'conditions and drawbacks'): [
        'llm_dependency', 'llm_drawback', 'llm_friction', 'c4_DEAD', 'semantic_tribal_dependency', 'kw_sacrifice', 'kw_discard']
        + [f'llm_dep_{k}' for k in 'TGAESKCLXHMO'] + [C5 + x for x in 'CD DW SE SD RN SA'.split()],
    ('効果の多さ・柔軟さ', 'amount and flexibility of effects'): [
        'llm_impact', 'llm_net', 'llm_impact_per_mv', 'llm_modal', 'c4_STACK', 'keyword_count', 'ability_sentences', 'oracle_len', 'oracle_lines',
        'quality_self_contained_value', 'semantic_flexible_target', 'c5_ntags', 'c5_nlvl2', 'c5_ngroups'] + [C5 + x for x in 'CH KC RE CY'.split()],
    ('テンポ・コンバットトリック', 'tempo and combat tricks'): ['c4_TEMPO', 'llm_trick', 'c4_role_T', 'semantic_cast_trigger'] + [C5 + x for x in 'FH PT SP'.split()],
    ('ほかのクリーチャーの強化・シナジー', 'boosting other creatures and synergy'): ['c4_SYNO', 'c4_role_S'] + [C5 + x for x in 'PC PP AN CP'.split()],
    ('マナ加速・色の補助', 'ramp and fixing'): ['c4_MANA', 'c4_role_N', 'type_land'] + [C5 + x for x in 'RM FX CR LD'.split()],
    ('相手への干渉', 'disrupting the opponent'): ['kw_mill'] + [C5 + x for x in 'DS ST MI TX'.split()],
    ('誘発能力', 'triggered abilities'): ['has_etb', 'kw_graveyard'] + [C5 + x for x in 'ET DY'.split()],
    ('カードの種類', 'card type'): ['type_creature', 'type_instant', 'type_sorcery', 'type_artifact', 'type_enchantment', 'type_planeswalker', 'c4_role_O'],
    ('セットの種類', 'kind of set'): ['is_supplemental_power_set', 'is_premier_set'],
}
TEXT = ('ルールテキストの語句', 'rules-text wording')


def group_of(features):
    g = {}
    for k, fs in GROUPS.items():
        for x in fs:
            if x in g:
                raise SystemExit(f'{x} is in two groups')
            g[x] = k
    miss = [x for x in features if x not in g]
    extra = [x for x in g if x not in features]
    if miss or extra:
        raise SystemExit(f'feature groups do not match the model: missing {miss}, not in model {extra}')
    return g


def level(v):
    a = abs(v)
    return '強く' if a >= 1.0 else 'やや' if a < 0.5 else ''


def overall(d):
    return ('この環境の平均よりかなり高い' if d >= 2 else '平均よりやや高い' if d >= .5 else '平均並み' if d > -.5
            else '平均よりやや低い' if d > -2 else 'この環境の平均よりかなり低い')


def material(ex, cards):
    feats = ex['features']
    gmap = group_of(feats)
    S = np.array([c['structured'] for c in ex['cards']])
    S = S - S.mean(0)                                  # centred on the set
    words = sorted({w for c in ex['cards'] for w in c['text']})
    W = np.array([[c['text'].get(w, 0.) for w in words] for c in ex['cards']])
    Wc = W - W.mean(0)
    gih = np.array([c['gih'] for c in ex['cards']]); dev = gih - gih.mean()
    byid = {c['id']: c for c in cards}
    out = []
    for i, c in enumerate(ex['cards']):
        g = {}
        for j, x in enumerate(feats):
            g.setdefault(gmap[x], []).append((S[i, j], x))
        fac = [(sum(v for v, _ in l), k, [x for v, x in sorted(l, key=lambda z: -abs(z[0]))[:3]]) for k, l in g.items()]
        tsum = float(Wc[i].sum())
        tw = sorted(((Wc[i, j], w) for j, w in enumerate(words) if c['text'].get(w)), key=lambda z: -abs(z[0]))
        fac.append((tsum, TEXT, [w for v, w in tw if np.sign(v) == np.sign(tsum)][:4]))
        up = [f for f in sorted(fac, key=lambda z: -z[0]) if f[0] >= MIN_PP][:TOP]
        down = [f for f in sorted(fac, key=lambda z: z[0]) if f[0] <= -MIN_PP][:TOP]
        card = byid[c['id']]
        out.append({'id': c['id'], 'name': c['name'], 'overall': overall(dev[i]), 'card': card,
                    'up': [(k, level(v), ev) for v, k, ev in up], 'down': [(k, level(v), ev) for v, k, ev in down]})
    return out


def fmt(i, m):
    c = m['card']
    pt = f" {c['power']}/{c['toughness']}" if c.get('power') not in (None, '') else ''
    lines = [f"#{i} | {c['name']} | {c.get('mana_cost') or ''} | {c.get('type_line') or ''}{pt}", (c.get('oracle_text') or '').strip(),
             f"予測: {m['overall']}"]
    for tag, fs in (('押し上げ', m['up']), ('押し下げ', m['down'])):
        for (ja, _), lv, ev in fs:
            lines.append(f"{tag}（{lv or '中程度'}）: {ja}" + (f" ［語句: {' / '.join(ev)}］" if ja == TEXT[0] and ev else ''))
    if not m['up'] and not m['down']:
        lines.append('押し上げ・押し下げ: 目立つ要因なし')
    return '\n'.join(lines)


def cmd_prepare(a):
    ex = json.loads(gzip.open(a.explain, 'rt', encoding='utf-8').read())
    cards = json.loads(gzip.open(a.cards, 'rt', encoding='utf-8').read())['cards']
    ms = material(ex, cards)
    (OUT / 'input').mkdir(parents=True, exist_ok=True); (OUT / 'raw').mkdir(exist_ok=True)
    ids = []
    for b in range(0, len(ms), BATCH):
        part = ms[b:b + BATCH]; name = f'b{b // BATCH + 1:02d}'
        (OUT / 'input' / f'{name}.txt').write_text('\n\n'.join(fmt(b + k + 1, m) for k, m in enumerate(part)) + '\n')
        ids += [{'n': b + k + 1, 'id': m['id'], 'name': m['name'], 'batch': name} for k, m in enumerate(part)]
    json.dump({'version': ex['version'], 'set': ex['set'], 'cards': ids}, open(OUT / 'ids.json', 'w'), ensure_ascii=False, indent=1)
    print(json.dumps({'cards': len(ms), 'batches': (len(ms) + BATCH - 1) // BATCH, 'version': ex['version']}))


DIGIT = re.compile(r'[0-9０-９]|[一二三四五六七八九十百]+(?:枚|点|ターン|マナ|回)|パーセント|％|%')


def problems(n, r):
    out = []
    ja, en = (r or {}).get('ja', ''), (r or {}).get('en', '')
    if not ja or not en:
        return [f'#{n}: ja/en missing']
    if 'から' not in ja or not ja.endswith('。'):
        out.append(f'#{n}: ja is not "〇〇だから、〇〇。"')
    if not 1 <= ja.count('。') <= 2 or len(ja) > 90:
        out.append(f'#{n}: ja must be 1-2 sentences, at most 90 characters')
    if DIGIT.search(ja) or re.search(r'[0-9]|percent|%', en):
        out.append(f'#{n}: numbers are not allowed')
    if len(en) > 220:
        out.append(f'#{n}: en too long')
    return out


def load_raw():
    ids = json.load(open(OUT / 'ids.json'))
    got, bad = {}, []
    for b in sorted({c['batch'] for c in ids['cards']}):
        p = OUT / 'raw' / f'{b}.json'
        want = {str(c['n']) for c in ids['cards'] if c['batch'] == b}
        if not p.exists():
            bad.append(f'{b}: missing'); continue
        d = json.load(open(p))
        if set(d) != want:
            bad.append(f'{b}: ids differ (missing {sorted(want - set(d))[:5]}, extra {sorted(set(d) - want)[:5]})')
        for n in want & set(d):
            bad += problems(n, d[n]); got[n] = d[n]
    return ids, got, bad


def cmd_check(_a):
    ids, got, bad = load_raw()
    print('\n'.join(bad) or f"ok: {len(got)} cards")
    if bad:
        raise SystemExit(1)


def cmd_merge(a):
    ids, got, bad = load_raw()
    if bad:
        raise SystemExit('run check first:\n' + '\n'.join(bad))
    out = {'version': ids['version'], 'set': ids['set'], 'method': 'B11g SHAP (structured, per feature group) + Ridge x TF-IDF (text), '
           'centred on the set; top raising/lowering factors written as 1-2 sentences by Sonnet (research/trk_preview/reasons_b11g.py)',
           'cards': [{'id': c['id'], 'name': c['name'], 'ja': got[str(c['n'])]['ja'], 'en': got[str(c['n'])]['en']} for c in ids['cards']]}
    a.out.write_text(json.dumps(out, ensure_ascii=False, indent=1) + '\n')
    print(json.dumps({'cards': len(out['cards']), 'out': str(a.out)}))


def main():
    ap = argparse.ArgumentParser(); sp = ap.add_subparsers(dest='cmd', required=True)
    p = sp.add_parser('prepare'); p.add_argument('--explain', type=Path, required=True); p.add_argument('--cards', type=Path, required=True)
    sp.add_parser('check')
    p = sp.add_parser('merge'); p.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    {'prepare': cmd_prepare, 'check': cmd_check, 'merge': cmd_merge}[a.cmd](a)


if __name__ == '__main__':
    main()
