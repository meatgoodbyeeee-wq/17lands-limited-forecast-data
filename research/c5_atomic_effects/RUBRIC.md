# Extraction rubric (C5: atomic effect tags)

Read the whole card (all faces / halves). Break it into the atomic effects it contains and tag them. Judge only what the text does, in two-player Limited. Do not judge overall strength. Use only the shown text, mana value, colours, type and P/T. "~" is the card itself.

Output one line per card: `<id> <RATE> <CLK> <BLK> | <tags>`
Example: `417 2 1 1 | KD2 ET1 DR1` ; a card with no tags: `418 2 2 1 |`
Ids are the numbers after `#`. Every card must get a line, in input order.

## Three small scales (single digits)
- RATE: efficiency of what the card does for its mana value, compared with typical Limited rates. 0 clearly below rate · 1 slightly below · 2 about at rate · 3 above rate · 4 far above rate (e.g. a 2-mana 3/3, or a 3-mana kill spell with no drawback).
- CLK: pressure on the opponent's life. 0 none · 1 slow · 2 solid · 3 fast / evasive / hasty.
- BLK: defensive value. 0 none · 1 usable blocker · 2 good blocker or lifegain/prevention · 3 very strong defence (stops attackers, repeatable).

## Tags (each appears at most once; level 1 = minor or secondary part of the card, 2 = a main or strong part). Write `<TAG><level>`, e.g. `DR1`.
Removal and interaction:
- KD destroy/exile a creature (unconditional or nearly) · KX kill with a real condition (tapped/attacking/small/needs setup) · DM damage to a creature · DA damage to any target or the opponent's face · MS −X/−X shrink · BN bounce · TP tap/freeze/stun · FT fight or bite · ED edict (opponent chooses) · CS counterspell · PA pacifism-style aura or "can't attack or block" · SW mass removal of creatures
Card flow:
- DR draw · SC scry / loot / selection · RC recursion from graveyard to hand or play · TU tutor / search library · IM impulse (exile and may play) · TK creates creature tokens · CL creates Clue/Treasure/Food or similar tokens
Stats and growth:
- PC +1/+1 counters put on creatures · PT temporary pump · PP permanent pump · AN anthem / lord effect on your creatures · CP copy / clone · EQ equipment, aura or vehicle bonus (stat or ability grant)
Combat keywords and abilities (tag when the card has or grants them): 
- FL flying · MN menace/trample/skulk-type soft evasion · FS first or double strike · DT deathtouch · LL lifelink · HS haste · VG vigilance · RH reach · IN indestructible / regeneration / hexproof / ward / protection · FH flash
Opponent-facing:
- DS discard · ST steal / gain control · MI mill or exile from library · DL drain / life loss for the opponent · TX tax or restriction on the opponent
Mana and economy:
- RM repeatable ramp (mana abilities) · FX fixing / land search · CR cost reduction · SK late-game mana sink (X, repeatable activated ability) · CY cycling / landcycling / channel
Triggers and shape:
- ET enters-the-battlefield effect · AT attack trigger · DY dies / leaves trigger · UP each-turn engine (upkeep/end step) · SP triggers on casting spells · LD landfall · SA sacrifice outlet or sacrifice fodder payoff · CH modal (choose one/two, split, adventure) · KC kicker / optional extra cost / escalate · RE flashback / escape / rebound / reuse from graveyard
Risk and conditions:
- SE symmetric effect (also helps the opponent) · DW real drawback (enters tapped, discard, sacrifice, damage to you, upkeep cost) · CD condition or setup needed for the main effect · RN randomness (coin flip, random choice) · SD pays life or damages you

Rules: tag only what the text actually says; do not infer from the card's name or from what you remember about it. When unsure between 1 and 2 choose 1. Keyword abilities count as tags (e.g. flying → FL2 if it is the card's key feature, FL1 if incidental). A vanilla creature gets no tags.
