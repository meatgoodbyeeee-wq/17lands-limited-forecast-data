# Rubric (C10: reasoned re-judgement against a reference ladder)

You judge Magic: The Gathering cards for two-player Limited (draft, 40-card decks, 17 lands, typical draft opponents). The cards in your input were hard to judge in an earlier pass (all rares and mythics, plus commons and uncommons on which earlier judges disagreed). Use only the shown text, mana value, colours, type and P/T. "~" is the card itself. Do not rely on what you may remember about a card, its set or how it performed; judge the text as if you saw it for the first time.

Your input starts with `CLASS C` (commons and uncommons) or `CLASS R` (rares and mythics). Use the ladder of the same class below.

## Task
For each card: (1) think about how the card plays in a real game: what must be true for it to be good, what happens when that is not true, what the best and the typical deck gets from it, how it compares in raw strength with the ladder levels; (2) write a short reason; (3) give three numbers.

Output exactly one line per card, in input order:
`<id> | <reason, at most 25 words> | <PCT> <GRADE> <SPEC>`
Example: `417 | Cheap removal that also draws; always playable, slightly below level 6 since it only hits small creatures. | 70 7 0`
Ids are the numbers after `#`. Every card must get a line. No other text in the file. The reason must not contain the character `|`.

- PCT (0–100, multiples of 5): where the card stands among all cards of its class in a typical set, by win rate of the decks that drew it. Place it against the ladder: level 1 ≈ 5, level 2 ≈ 20, level 3 ≈ 35, level 4 ≈ 50, level 5 ≈ 65, level 6 ≈ 80, level 7 ≈ 95; values between levels are allowed. Use the whole range; about half of the cards in a class are above 50 by definition.
- GRADE (0–10): overall Limited grade (0 unplayable · 2 sideboard · 4 filler · 5 average playable · 6 good · 7 strong · 8 very strong · 9 bomb · 10 game-winning bomb).
- SPEC (0–3): how much the card's value depends on a specific deck, board or synergy that the drafter has to build around. 0 good in any deck · 1 slightly deck-dependent · 2 needs support to be good · 3 bad or dead without a specific build-around.

Cautions: text that sounds powerful but is slow, conditional or needs a deck built around it is often weaker in practice; plain, efficient cards (cheap removal, evasive or sticky creatures, cards that give two bodies or a card plus a body) are often stronger than they look. Rare status alone is not strength. Judge each card on its text.

## Ladders
### Ladder C (commons and uncommons)
Seven reference cards from a different set, ordered from weakest to strongest by how they actually performed (level 1 = bottom 5%, level 4 = median, level 7 = top 5% of that class). The cards' names are hidden (~).

**Level 1** (about the 5th percentile)
MV 6 R | Creature — Giant 5/4
Trample, haste
Mountaincycling {2} ({2}, Discard this card: Search your library for a Mountain card, reveal it, put it into your hand, then shuffle.)

**Level 2** (about the 20th percentile)
MV 1 G | Instant
Tiered (Choose one additional cost.)
• Somersault — {0} — Target creature gets +2/+2 until end of turn.
• Meteor Strikes — {2} — Double target creature's power and toughness until end of turn.
• Final Heaven — {6}{G} — Triple target creature's power and toughness until end of turn.

**Level 3** (about the 35th percentile)
MV 5 R | Instant
~ deals 6 damage to target creature. Destroy up to one Equipment attached to that creature.

**Level 4** (about the 50th percentile)
MV 1 B | Creature — Salamander Horror 2/1
This creature enters tapped with a stun counter on it. (If it would become untapped, remove a stun counter from it instead.)
Chef's Knife — During your turn, this creature has first strike and deathtouch.

**Level 5** (about the 65th percentile)
MV 2 B | Creature — Ooze Horror 1/1
When this creature enters, each opponent discards a card.

**Level 6** (about the 80th percentile)
MV 3 B | Sorcery
Target opponent sacrifices a creature of their choice.
Create a 0/1 black Wizard creature token with "Whenever you cast a noncreature spell, this token deals 1 damage to each opponent."

**Level 7** (about the 95th percentile)
MV 3 B | Instant
Target creature gets -0/-9999 until end of turn.

### Ladder R (rares and mythics)
Seven reference cards from a different set, ordered from weakest to strongest by how they actually performed (level 1 = bottom 5%, level 4 = median, level 7 = top 5% of that class). The cards' names are hidden (~).

**Level 1** (about the 5th percentile)
MV 4 G | Legendary Artifact
Green spells you cast cost {1} less to cast.
If one or more +1/+1 counters would be put on a creature you control, twice that many +1/+1 counters are put on that creature instead.
{4}{G}{G}, {T}: Distribute two +1/+1 counters among one or two target creatures you control.

**Level 2** (about the 20th percentile)
MV 4 W | Legendary Artifact
White spells you cast cost {1} less to cast.
If you would gain life, you gain twice that much life instead.
{4}{W}{W}, {T}: Creatures you control gain flying and lifelink until end of turn.

**Level 3** (about the 35th percentile)
MV 5 B | Legendary Creature — God 5/5
Indestructible
When ~ enters, each player sacrifices half the non-God creatures they control of their choice, rounded down.
Whenever a player sacrifices another creature, put a +1/+1 counter on ~.

**Level 4** (about the 50th percentile)
MV 3 WR | Legendary Creature — Human Soldier 3/2
First strike, trample, lifelink
Stagger — Whenever ~ deals combat damage to a player, until your next turn, if a source would deal damage to that player or a permanent that player controls, it deals double that damage instead.

**Level 5** (about the 65th percentile)
MV 2 W | Legendary Creature — Human Soldier Mercenary 2/1
When ~ enters, search your library for an Equipment card, reveal it, put it into your hand, then shuffle.
As long as ~ is equipped, if a triggered ability of ~ or an Equipment attached to it triggers, that ability triggers an additional time.

**Level 6** (about the 80th percentile)
MV 3 UR | Legendary Creature — Wizard 0/3
{0}: Add X mana in any combination of {U} and/or {R}, where X is ~'s power. Activate only during your turn and only once each turn.
Whenever you cast a noncreature spell, put a +1/+1 counter on ~ and it deals 1 damage to each opponent.

**Level 7** (about the 95th percentile)
MV 4 R | Sorcery
Choose target creature you control. It deals damage equal to its power to each other creature. If this spell was cast from a graveyard, discard your hand and draw four cards.
Flashback {5}{R}{R} (You may cast this card from your graveyard for its flashback cost. Then exile it.)

