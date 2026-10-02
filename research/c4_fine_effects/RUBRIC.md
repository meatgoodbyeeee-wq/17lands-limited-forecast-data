# Extraction rubric (C4: finer card effects)

Read the whole card (all faces / halves). Judge only what the text does, in two-player Limited. Do not judge overall strength or how good the card is, and use only the shown text, mana value, colours, type and P/T. "~" is the card itself; "opposing" means the opponent's permanents.

Output one line per card: `<id> <fourteen digits> <role>` — digits in the order below, then one role letter. Example: `417 30200211030012 R`.
The ids are the numbers after `#`. Every card must get a line.

| pos | field | values |
|---|---|---|
| 1 DMG | removal magnitude (largest effect on a creature in one resolution or activation) | 0 none · 1 toughness/power reduction or damage ≤2 · 2 exactly 3 · 3 4–5 · 4 ≥6, or destroy/exile |
| 2 TGT | what the removal can hit | 0 none · 1 narrow (only tapped/attacking/blocking/small/flying/a type) · 2 any creature · 3 any creature or planeswalker/nonland permanent · 4 any target including players |
| 3 SPD | removal timing | 0 none · 1 sorcery speed, aura, or slow/attached · 2 instant speed or on enter/attack · 3 repeatable on demand |
| 4 SWG | board stats added on resolution (total power+toughness of the card itself if it is a creature, plus tokens created, plus permanent pumps) | 0 ≤2 or none · 1 3–4 · 2 5–7 · 3 8–11 · 4 ≥12 |
| 5 EVA | evasion | 0 none · 1 soft (menace, trample, "can't be blocked by" a narrow class, skulk) · 2 flying or equivalent · 3 effectively unblockable |
| 6 TURN | when it first changes the game, using its mana value and conditions | 0 turns 1–3 · 1 turns 4–5 · 2 turn 6 or later · 3 only once conditions are met (does nothing alone) |
| 7 DEAD | how often the main effect does nothing in a normal game | 0 never · 1 rarely · 2 sometimes (about a third of games) · 3 often (half or more) |
| 8 SCALE | grows with game length or resources | 0 no · 1 mild (some growth or X) · 2 strong (grows each turn or every spell/mana) |
| 9 TEMPO | tempo as the main job (bounce, tap/stun, haste, free or cheap spells, effects stronger than their cost in turns) | 0 none · 1 some · 2 main purpose |
| 10 VULN | card disadvantage when answered in response or after (auras, equipment attach, pump on a target, "when this enters" absent) | 0 none · 1 moderate · 2 high (two-for-one risk) |
| 11 STACK | number of distinct independent useful effects or abilities on the card (a vanilla body = 1; cap 5) | 1–5 (write 0 if the card does nothing, e.g. blank text) |
| 12 SYNO | how much it helps your other cards (lord, anthem, cost reduction for others, enables others) | 0 none · 1 minor / one type · 2 team-wide |
| 13 DRAIN | life swing per resolution (gain, loss to opponent, or damage to face) in a normal use | 0 none · 1 1–3 · 2 4–6 · 3 ≥7 |
| 14 MANA | mana help | 0 none · 1 fixing or one-shot · 2 repeatable ramp / extra land drops |

Role (one letter, the card's main job): `A` attacker / aggressive body · `D` defender / blocker · `V` value engine / card advantage · `F` finisher / top-end threat · `R` removal / interaction · `T` trick / protection · `S` support / synergy piece · `N` ramp / fixing / land · `O` other.

Notes: a creature card counts itself for SWG (power+toughness). Scale SWG by the stats shown, not by the cost. For a modal card use the strongest mode for DMG/TGT/SPD but reflect flexibility in STACK. For TURN, use the card's mana value (cheap tricks and removal count as turns 1–3 unless they need a condition). Be consistent: when two values fit, choose the lower one.
