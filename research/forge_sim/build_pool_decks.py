#!/usr/bin/env python3
"""Forge self-play, step 1 (alternative, user request 2026-10-29): one "whole colour pool" deck per colour pair, no card choice.

  python3 research/forge_sim/build_pool_decks.py --forge <forge checkout> --out research/forge_sim/decks_fra_pool_c2u1 --common 2 --uncommon 1

Rule: every common and uncommon non-land card of the set whose mana cost has only the pair's colours (colourless included), with
--common / --uncommon copies each, plus basic lands at the 40-card ratio (17 lands per 23 spells, rounded), split by the coloured
mana symbols of the spells (each colour at least 6/17 of the lands). No prediction model and no deck-size limit.
Rarity and mana cost come from Forge's edition file and card scripts (front face).
"""
import argparse, glob, re
from pathlib import Path

PAIRS = ['WU', 'WB', 'WR', 'WG', 'UB', 'UR', 'UG', 'BR', 'BG', 'RG']
BASIC = {'W': 'Plains', 'U': 'Island', 'B': 'Swamp', 'R': 'Mountain', 'G': 'Forest'}


def set_cards(forge, code):
    for f in glob.glob(str(Path(forge) / 'forge-gui/res/editions/*.txt')):
        t = open(f, encoding='utf-8').read()
        if re.search(rf'^Code={code}$', t, re.M):
            break
    else:
        raise SystemExit(f'no edition {code}')
    size = int(re.search(r'^CardsInSet=(\d+)', t, re.M).group(1)) if re.search(r'^CardsInSet=', t, re.M) else 10 ** 6
    rar = {}
    for line in t.split('[cards]')[1].split('\n[')[0].splitlines():
        m = re.match(r'(\d+)\w* (\w) (.+?)(?: @.*)?$', line.strip())
        if m and int(m.group(1)) <= size:
            rar.setdefault(m.group(3).strip(), m.group(2))
    return rar


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--forge', required=True); ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--common', type=int, default=2); ap.add_argument('--uncommon', type=int, default=1)
    ap.add_argument('--set', default='FRA')
    a = ap.parse_args()
    rar = set_cards(a.forge, a.set)
    info = {}
    for f in glob.glob(str(Path(a.forge) / 'forge-gui/res/cardsfolder/*/*.txt')):
        s = open(f, encoding='utf-8', errors='ignore').read().split('ALTERNATE')[0]
        n = re.search(r'^Name:(.+)$', s, re.M)
        if n and n.group(1).strip() in rar:
            mc = re.search(r'^ManaCost:(.+)$', s, re.M); mc = mc.group(1) if mc else ''
            info[n.group(1).strip()] = (re.findall(r'[WUBRG]', mc), 'Land' in re.search(r'^Types:(.+)$', s, re.M).group(1))
    assert set(info) == set(rar), sorted(set(rar) - set(info))
    a.out.mkdir(parents=True, exist_ok=True)
    for p in PAIRS:
        main_ = []
        for name in sorted(info):
            sym, land = info[name]
            copies = {'C': a.common, 'U': a.uncommon}.get(rar[name], 0)
            if not land and copies and set(sym) <= set(p):
                main_.append((copies, name, sym))
        spells = sum(c for c, _, _ in main_)
        lands = round(spells * 17 / 23)
        cnt = {c: sum(k * s.count(c) for k, _, s in main_) for c in p}
        n0 = max(round(lands * 6 / 17), min(lands - round(lands * 6 / 17), round(lands * cnt[p[0]] / max(1, sum(cnt.values())))))
        basics = {p[0]: n0, p[1]: lands - n0}
        lines = ['[metadata]', f'Name={a.set}_{p}_00', '[main]'] + [f'{c} {n}|{a.set}' for c, n, _ in main_] + \
                [f'{basics[c]} {BASIC[c]}' for c in p]
        (a.out / f'{a.set}_{p}_00.dck').write_text('\n'.join(lines) + '\n')
        print(p, 'spells', spells, 'unique', len(main_), 'lands', basics)


if __name__ == '__main__':
    main()
