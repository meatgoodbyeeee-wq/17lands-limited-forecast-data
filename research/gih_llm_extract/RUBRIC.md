# Extraction rubric (C3)

Read the whole card (all faces / halves). Judge only what the text does. Do not judge overall strength.
"Opposing" means the opponent's creatures or permanents. Answer in the context of two-player Limited.

Output one line per card: `<id> <RSBCPMDXTK> <dep>` — ten digits in the order below, then one dependency letter.
Example: `417 2010000000 -`

| pos | field | values |
|---|---|---|
| R | removal | 0 none · 1 limited · 2 solid single-target · 3 removes two or more |
| S | sweeper | 0 none · 1 symmetric mass removal · 2 one-sided mass removal |
| B | bodies | creature bodies entering under your control on resolution, 0–3 (cap 3) |
| C | cards | extra cards gained beyond 1-for-1, 0–3 (cap 3) |
| P | repeat | 0 none · 1 repeatable at a cost/condition · 2 repeatable automatically |
| M | modal | 0 · 1 meaningful choice or second use |
| D | dependency | 0 works alone · 1 mild · 2 significant · 3 build-around |
| X | drawback | 0 none · 1 minor · 2 major |
| T | trick | 0 · 1 combat trick / protection / flash ambush |
| K | sink | 0 · 1 useful outlet for extra mana late |

## R removal
- 1 limited: damage ≤2, −1/−1 or −2/−2, fight/bite (needs your creature), bounce, tap/stun, edict (opponent chooses), counterspell,
  or a kill spell with a real targeting restriction (only tapped / attacking / blocking / flying / power ≥4 / mana value ≤2 …).
- 2 solid: destroy/exile target creature or nonland permanent with at most a trivial restriction; ≥3 damage to a creature;
  −3/−3 or more; "can't attack or block" aura; O-Ring style exile.
- 3 two or more: kills two creatures, repeatable removal, or a one-sided sweeper.
- Removal on a creature's ETB or attack counts. A tiny ping ability that can kill 1-toughness creatures repeatedly is 1.

## S sweeper
Mass removal of creatures: 1 if it also hits your own creatures comparably, 2 if one-sided (e.g. "creatures your opponents control get −2/−2").

## B bodies
Count creatures you get immediately: a creature card counts itself; tokens created on cast/ETB count; vehicles and other noncreature permanents count 0.
Tokens created later by a trigger do not count here (see P).

## C cards
Net extra cards: draw N = N (a loot / rummage = 0; draw 2 discard 1 = 1); return a card from graveyard to hand = 1; tutor = 1;
impulse draw you can use = 1; Clue = 1; Treasure/Food = 0. A removal 2-for-1 belongs in R, not C.

## P repeat
Value that recurs over the game: 1 if each use costs mana, tapping, sacrificing, or needs a condition you must set up;
2 if it triggers from ordinary play (each upkeep, end step, attack, when a creature of yours enters or dies).

## M modal
Choose-one/-two modes, kicker/overload/escalate/offspring-like options, split/adventure/MDFC/room, cycling/landcycling,
flashback/escape/other graveyard reuse, alternative costs that change the use.

## D dependency
How much the main effect needs conditions you must assemble:
1 mild — usually true (control a creature, attack, opponent has a creature);
2 significant — specific card types, a creature type, thresholds, graveyard size, casting spells, lifegain triggers;
3 build-around — does little in an ordinary deck of its colours.

## X drawback
1 minor — enters tapped, small life payment, can't block alone, small upkeep cost, discard.
2 major — sacrifice your own permanents, can't block, a symmetric effect that hurts you as much, opponent gains a real benefit.

## T trick
Instant-speed pump, grants indestructible / hexproof / protection / regeneration, or a flash creature.

## K sink
X costs, repeatable mana abilities (not equip), kicker / multikicker, monstrosity / level up / adapt, flashback / escape, landcycling.

## dep (one letter)
What the card asks you to have: `-` none · `T` creature type · `G` graveyard / self-mill · `A` artifacts · `E` enchantments ·
`S` instants / sorceries / noncreature spells · `K` tokens / go-wide · `C` +1/+1 counters · `L` lifegain · `X` sacrifice / death ·
`H` legendary / historic · `M` multicolour · `O` other.
