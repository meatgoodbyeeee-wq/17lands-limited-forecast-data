# Outcome lessons: where the pre-release model misses (GIH WR, pp vs set mean)

Source: ~450 largest-miss cards across 11 past sets. "Miss" = actual - model. Because the sample was picked for large misses, these sizes are the typical size when the pattern fires, not average corrections; shrink them by roughly half before using them as priors. "Expert" = pre-release human grade. Lessons where the expert was also wrong are marked **[expert also wrong]**.

---

## A. Calibration / scale

### 1. The model compresses the top tail: bombs land higher than predicted
- **Pattern:** cards the model already ranks in roughly the top 5% of the set, especially when the card makes an immediate impact (ETB removal, ETB card advantage plus a big evasive body, a flexible "do several things" spell, an engine that also makes bodies every turn).
- **Direction / size:** UNDERrated, typically +3 to +8 pp, even though they are already near the top.
- **Confidence:** high. About 30 examples, very consistent. Counter-examples are covered in lesson 2: top-ranked cards whose value is delayed or conditional.
- **Use:** stretch the top of the distribution (for example multiply positive predictions above the ~95th percentile by 1.4–1.7) rather than shrinking toward the mean.

### 2. Expensive "bombs" whose value is delayed, conditional or random get overrated
- **Pattern:** 6–7+ MV creatures whose payoff is an attack trigger (they must survive a turn cycle first); high-crew or high-threshold vehicles/artifacts; "cast random cards from the top on attack"; double-cast or "prepared" style creatures that look like two-for-ones but come as two below-rate halves; ETB tokens on a below-rate body at 3–4 MV.
- **Direction / size:** OVERrated, -5 to -7 pp, even when the model ranks them top 20.
- **Confidence:** medium-high. About 10 examples. Experts were split, often grading these 3–3.5. **[expert also wrong in about half]**

### 3. The bottom tail is also compressed: unplayable build-arounds score far worse than predicted
- **Pattern:** cards the model already places in the bottom ~5%: non-creature enchantments or artifacts that only double or copy things, alt-win counters, global type-changing effects, copy-every-spell engines.
- **Direction / size:** OVERrated, -5 to -11 pp, even though the model already ranks them last. Real values reach -13 to -20.
- **Confidence:** high. About 12 examples. The ranking is right but the magnitude is about 2x too small. Experts agreed these are bad.

---

## B. Card advantage, interaction and "boring" cards

### 4. Plain unconditional card draw and selection is underrated
- **Pattern:** draw 2–3 or look-at-N-take-2 sorceries and instants, flashback cantrips, cantrip-plus-small-effect instants, ETB loot or draw enchantments, 1-MV artifacts that "sac: pick 1 of top 2".
- **Direction / size:** UNDERrated, +3 to +6 pp. A huge "draw 2^X" style scaling spell came in at +8.
- **Confidence:** high. About 15 examples. **[expert also wrong]**: these were graded 2.0–2.5.
- **Counter:** "discard your hand, then draw N" wheels, draw that scales with a hard-to-meet board condition, and cards that need speed or threshold to pay off are OVERrated (-5 to -7).

### 5. Hand disruption (targeted or forced discard) is underrated
- **Pattern:** "opponent reveals, you choose a nonland card", "target opponent discards 2" (alone or as a mode), converge discard, ETB-discard creatures, flashback discard.
- **Direction / size:** UNDERrated, +3 to +9 pp.
- **Confidence:** medium-high. About 8 examples, no counter-examples in the sample. **[expert also wrong]**: graded 1.0–2.5.

### 6. Counterspells are underrated
- **Pattern:** hard or soft counters at 1–3 MV: creature-only counters, counter plus loot, "counter unless pay X" with cost reduction, counter riders on pump spells.
- **Direction / size:** UNDERrated, +4 to +5 pp.
- **Confidence:** medium. About 5 examples, consistent. **[expert also wrong]**: graded about 2.5.

### 7. Real sweepers are underrated, weak or symmetric "mini-sweepers" are overrated
- **Pattern, underrated:** unconditional "destroy all creatures", edict-everything effects, expensive one-sided or card-advantage wraths, sagas or enchantments that wrath and then leave a threat.
  - **Size:** UNDERrated, +4 to +8 pp.
- **Pattern, overrated:** 1 damage or -2/-2 to every creature, "each player keeps total power ≤ N", "exile all MV ≤2 permanents", or "2 damage to each creature of type X".
  - **Size:** OVERrated, -5 to -7 pp.
- **Confidence:** high. About 6 examples each way. **[expert also wrong]** on the true wraths, which were graded 3.5. Experts were right on the mini-sweepers.

### 8. Removal that compensates the opponent is overrated
- **Pattern:** cheap destroy or exile that gives the victim tokens, a clue, a face-down 2/2, or a free cast or discover; "shuffle it in and they cast something else"; transform-into-land or turn-into-1/1 auras that leave a usable permanent.
- **Direction / size:** OVERrated, -5 to -11 pp.
- **Confidence:** medium-high. About 7 examples. Experts were mostly lukewarm (1.5–2.5), so this is partly known.
- **Counter:** tap-down "doesn't untap" auras with a late-game shuffle-away option are UNDERrated (+4). They give the opponent nothing.

### 9. Damage-for-X and fight removal: the conversion rate matters more than the model thinks
- **Overrated:** X-damage burn at a 1:1 rate where the rider depends on excess damage (-5); fight spells where your creature must survive and the rider is minor (-7); "bite" spells mostly buffing toughness (-7).
- **Underrated:** "deals twice X", fight or bite spells that also permanently grow your creature, damage equal to mana spent plus an untap or flashback rider, and auras or enchantments whose ETB bites (+3 to +4).
- **Confidence:** medium. About 10 examples, mixed. Experts were near the actual values on several, so the model alone is misreading the rates.

### 10. Narrow sideboard-style removal is unpredictable; flexible versions win
- **Pattern:** artifact/enchantment removal that also hits fliers or creatures, or comes with a bonus land/token, is UNDERrated (+4 to +6). Pure two-target artifact/enchantment removal with a card-gift drawback is OVERrated (-5).
- **Confidence:** low-medium. 3–4 examples.

---

## C. Mana and lands

### 11. Fixing is underrated in sets that support three or more colors
- **Pattern:** mana rocks or dorks that make any color, fetch-a-basic artifacts with a late sac payoff, "tap a creature for any color", fixing creatures and lands, any-color mana on a body, crew-heavy vehicles that also fetch a land, and on-color dual or tri lands.
- **Direction / size:** UNDERrated, +4 to +7 pp. Larger in sets with wedge or 3-color archetypes, converge, or many gold cards.
- **Confidence:** high. About 15 examples. **[expert also wrong]**: graded 2.0–2.5.
- **Counter:** fixing restricted to one creature type, and slow ramp enchantments in fast "go-fast" formats, are OVERrated (-5 to -6).

### 12. Utility lands are nearly free value and score well above prediction
- **Pattern:** a land that taps for mana and also has a mana-sink ability (unblockable-maker, team pump, token maker, card filtering or impulse draw, becomes a creature, regrowth). Also untapped duals with a mild condition.
- **Direction / size:** UNDERrated, +3.5 to +5 pp. The model puts them near the bottom.
- **Confidence:** high. About 10 examples, no clear counter-example except type-restricted mana. **[expert also wrong]**: graded 2.0–3.0.

### 13. Three-color cards with self-contained value are underrated; three-color build-arounds are overrated
- **Pattern, underrated:** in a set with 3-color support, gold 3-color commons or uncommons that are simply efficient or card-advantage: dig spells, ETB-loot bodies, big evasive dragons, multi-effect modal spells. Also converge cards ("X = number of colors spent").
  - **Size:** UNDERrated, +3 to +6 pp. Converge reached +6 to +10.
  - **Note:** the model over-penalizes the color requirement. **[expert also wrong]**: graded 2.5.
- **Pattern, overrated:** 3-color legendary rares whose text needs a sub-theme (cast from exile, sac a permanent on ETB, tap tokens, legendary-matters, symmetric draw).
  - **Size:** OVERrated, -5 to -10 pp.
- **Confidence:** high. About 10 examples each way.

---

## D. Build-arounds and synergy text

### 14. Synergy-dependent legendary rares and mythics are overrated
- **Pattern:** a mid-cost legend or engine whose text is all upside from a sub-theme: noncombat-damage draw, spell copying, casting from the top or from exile, "whenever you cast a spell with property X", affinity granting, mass-tapping ten creatures. Typical sign: an average or small body and no immediate effect.
- **Direction / size:** OVERrated, -5 to -11 pp.
- **Confidence:** high. About 20 examples. **[expert also wrong]** in roughly half: graded 3.0–4.0.
- **Rule of thumb:** if the card does nothing the turn it lands unless the deck is built for it, subtract 4–6 pp.

### 15. Spell-copy and storm-style engines flop in Limited
- **Pattern:** "copy that spell", "copy for each other spell cast this turn", copy-a-token-of-this on spell cast, coin-flip copies.
- **Direction / size:** OVERrated, -5 to -11 pp.
- **Confidence:** high. About 7 examples. Experts were mixed: low on some, 3.5 on others.

### 16. Doublers and copy-enhancers without their own board presence are overrated
- **Pattern:** counter or token doublers, "double the counters on target creature", "copy target token X times", "tokens become copies of this permanent".
- **Direction / size:** OVERrated, -5 to -11 pp, even from an already low prediction.
- **Confidence:** high. About 6 examples.
- **Counter:** a doubler attached to a card with an immediate standalone mode, such as a level-1 counter every turn or a planeswalker that also makes tokens, is UNDERrated.

### 17. Self-harming or symmetric downside effects are badly overrated
- **Pattern:** everyone draws or everyone discards; exile most of every library; "you lose 2 life unless..."; "players can't gain life" plus damage to each player; donate-yourself modes; symmetric mass sacrifice with a life tax; enchant-player effects that are only good once the opponent is low.
- **Direction / size:** OVERrated, -5 to -15 pp. The worst case was -15, a strong-statted flyer with a symmetric deck-destroying ETB.
- **Confidence:** high. About 8 examples. The model seems to read the stats and miss the drawback. Experts mostly caught it with grades of 0.5–2.

### 18. Payoffs for a strong, densely supported set mechanic are underrated; payoffs for a weak or hard-to-trigger mechanic are overrated
- **Pattern, underrated:** "whenever [common mechanic event] happens, small value" creatures at 1–3 MV, where the event happens many times per game in a typical deck. Examples of such events: an enchantment entering in an enchantment-dense set, casting a spell that targets a creature in a spells set, cards leaving the graveyard in a graveyard set, the power-4-plus check in a big-creatures set.
  - **Size:** UNDERrated, +3 to +7 pp. Up to +10 for a cheap engine that also drains.
  - **Note:** experts were lukewarm at 2.0–3.5. **[expert also wrong]**
- **Pattern, overrated:** payoffs for events that are rarely achieved or need extra setup, such as "a permanent card went to the graveyard this turn" end-step checks, max speed, finality reanimation of one type, or turning things face up on a narrow condition.
  - **Size:** OVERrated, -5 to -8 pp.
- **Confidence:** high, about 25 examples. Applying it needs a set-level estimate: count the commons and uncommons that create the triggering event. Roughly 25 or more enablers points to underrated payoffs; few enablers or an event that costs card disadvantage points to overrated payoffs.

### 19. Tribal lords, anthems and go-wide payoffs are underrated in creature-type or go-wide sets
- **Pattern:** "other [types] you control get +1/+1", type-choice anthem artifacts, global +1/+1 enchantments with a drain, "power equals number of creatures", grow-when-ally-enters, attack-with-three payoffs.
- **Direction / size:** UNDERrated, +3.5 to +7.5 pp.
- **Confidence:** high. About 15 examples. Experts were partly right at 3.0–4.0 but still low.
- **Counter:** tribal enchantments that only make tokens on a narrow trigger (-4.6), and legend-matters anthems (-8).

### 20. Sacrifice outlets attached to small value are overrated; sacrifice as a cost on strong effects is underrated
- **Overrated:** creatures with a "sac another creature: drain 1 / gain indestructible" ability, or "sac a nonland permanent on ETB/attack for counters" (-4.5 to -6).
- **Underrated:** 1-MV removal or exile with "sacrifice a creature or artifact" as an additional cost, "sac another permanent: draw 2", and "sac on attack: draw plus evasion" (+3 to +5).
- **Confidence:** medium. About 8 examples. **[expert also wrong]** on the underrated side, graded 1.5–2.5.

### 21. Flicker-your-own-creature effects are overrated unless cheap and cantripping
- **Pattern:** ETB "exile your creature, return at end step" creatures, mass blink sorceries, attack-trigger blinks on a class or enchantment, "turn face up: bounce your own permanent". These rely on a density of ETB creatures that Limited decks lack.
- **Direction / size:** OVERrated, -5 to -9 pp.
- **Confidence:** medium. About 5 examples. Counter: a 1-MV blink that conditionally draws was UNDERrated (+3.7).

### 22. Graveyard spell recursion in spells-heavy sets is underrated; conditional mass reanimation is overrated
- **Underrated:** "return X instants/sorceries to hand", "spells in graveyard have flashback", repeatable free-casting of spells from the graveyard, and "regrow all spells" bombs (+4 to +8). **[expert also wrong]**: graded 2–2.5.
- **Overrated:** "return all cards with MV exactly X", temporary copies of graveyard creatures, "cast a card that went to a graveyard this turn", tutor-to-graveyard, and two-plus-two land and permanent regrowth at 5 MV (-5 to -8).
- **Confidence:** medium-high. About 12 examples.

### 23. Self-contained mill-the-opponent cards are underrated
- **Pattern:** repeatable or large opponent-mill effects: an exhaust-to-mill-graveyard-size artifact, "mill 3 per spell cast", "mill equal to your life total".
- **Direction / size:** UNDERrated, +5 to +10 pp, from a very low prediction. The model treats mill as a non-effect, but 17Lands drafters who pick these build to make them work.
- **Confidence:** low-medium. 4 examples. **[expert also wrong]**: graded 1–3.
- **Counter:** self-mill alt-win bodies are OVERrated (-6).

---

## E. Bodies, keywords and drawbacks

### 24. Oversized bodies with a text drawback are underrated
- **Pattern:** stats far above rate for their MV with a drawback: a 6/6 for 3 that stuns itself when alone, a big indestructible body that can't attack on odd counters, a 3/3 for 1 with a delirium attack restriction, a 4/2 haste that must be blocked, vanilla 9/7s, a 7/7 reach with ward that can also cycle for land. Also menace or ward on an aggressive X/1.
- **Direction / size:** UNDERrated, +3.5 to +7.5 pp. The model over-penalizes drawback text.
- **Confidence:** medium-high. About 10 examples. **[expert also wrong]** on about half, graded 2.0–2.5.
- **Counter:** a small "can't block" body with only recursion text is OVERrated (-6.7).

### 25. Cheap evasive bodies with a second keyword or value text are underrated; low-stat fliers with a conditional rider are overrated
- **Underrated:** 1–2 MV fliers with lifelink, vigilance or a death or ETB value trigger; 2/3–3/x fliers for 2–3 that are self-copying or have ETB "gain 1 per creature"; 1/1 lifelinkers that scry; flying "return a permanent" 2/3s (+3.5 to +6).
- **Overrated:** 1/2 or 2/2 fliers whose rider needs a counter or condition, offspring fliers at 3 MV, and 4-MV fliers whose extra value is a temporary token (-4.5 to -6).
- **Confidence:** high. About 15 examples. **[expert also wrong]** on the underrated side, graded 2.0–2.5.

### 26. Temporary tokens and "attacks with a token that's sacrificed" are overrated
- **Pattern:** creatures that create attacking tokens sacrificed at end of turn (mobilize-style), "endure"-style small choices on a below-rate body, end-step-sacrificed copies, and "put a creature from hand onto the battlefield, sac at end".
- **Direction / size:** OVERrated, -4.5 to -6 pp.
- **Confidence:** medium-high. About 8 examples. Experts were near the actual values at 2.0–2.5.
- **Counter:** a 1-MV "copy X creatures with haste" sorcery was UNDERrated (+4).

### 27. Tap-to-power mechanics (crew, saddle, station) depend on threshold
- **Pattern, underrated:** low thresholds (crew 1–2, saddle 2–3, station ≤7) on efficient bodies, or vehicles with an ETB or landfall payoff.
  - **Size:** UNDERrated, +3 to +10 pp. A land-scaling, land-fetching vehicle came in at +9.7.
  - **Note:** **[expert also wrong]** on commons and uncommons, graded 2.0–3.0.
- **Pattern, overrated:** thresholds of 8, 10 or 20+, cards that only enable crewing or saddling, and "make vehicles creatures" support artifacts.
  - **Size:** OVERrated, -5 to -7 pp.
- **Confidence:** high. About 20 examples.

### 28. Equipment: stats and keywords are underrated, utility without stats is overrated
- **Pattern, underrated:** cheap equipment giving +1/+1 or more with a meaningful rider (attack loot, treasure, artifact kill); equipment granting double strike, flying or unblockable; equipment that brings its own body on ETB.
  - **Size:** UNDERrated, +3.5 to +6.5 pp.
- **Pattern, overrated:** equipment with no P/T boost and only an activated utility (tap, bait, hexproof+haste, reach and can't-be-blocked-by-more-than-one); expensive "ETB destroy" equipment at 7 MV; equipment attached to a poor manifest body.
  - **Size:** OVERrated, -4.5 to -6.5 pp.
- **Confidence:** medium-high. About 18 examples. Experts were mostly correct on the overrated group with low grades.

### 29. Cheap protective or value-adding combat tricks are underrated; counter-only or conditional pumps are overrated
- **Underrated:** 1–2 MV tricks granting hexproof, indestructible or first strike plus a bonus (treasure, untap, artifact kill, lifelink), flash +1/+1 hexproof auras, and permanent-pump auras that draw when they leave (+3.3 to +6).
- **Overrated:** pure "+1/+1 counters" tricks whose rider needs a condition, temporary animate-a-land tricks, and "tap and stun" sorceries (-5 to -5.7).
- **Confidence:** medium. About 10 examples. **[expert also wrong]** on the underrated group, graded 1.5–2.0.

---

## F. Engines and permanents

### 30. Impulse-draw and top-of-library engines that do nothing to the board are overrated
- **Pattern:** 3-MV enchantments that exile the top card each upkeep, "you may cast creatures of power ≤2 from the top", "the top card has plot", and "cast artifacts from the top" on a 5-MV body. They cost tempo and generate marginal value.
- **Direction / size:** OVERrated, -5 to -7 pp.
- **Confidence:** medium-high. About 8 examples. **[expert also wrong]**: graded 3.0–3.5.
- **Counter:** the same effect stapled to a land, or to a sac-artifact outlet in an artifact set, is UNDERrated (+4).

### 31. "Second spell each turn" and spell-cost-reduction payoffs are underrated when standalone; "if you didn't cast a spell" payoffs are overrated
- **Underrated:** a 2/4 body that makes the second spell cheaper, creatures that cost much less after a first spell, and a mid-cost creature that makes tokens or counters on the second spell (+3.5 to +6). **[expert also wrong]**: graded 1.5–3.5.
- **Overrated:** "at end step, if you haven't cast a spell from hand, draw or make a token" on 4–5 MV gold bodies (-4.7 to -5.4), and enchantments that animate only after two spells (-4.7).
- **Confidence:** medium. About 8 examples.

### 32. Cheap engine creatures that grow or draw over time are underrated
- **Pattern:** 1–2 MV creatures that get counters when a common event happens (increment-style, ally or kin enters, tap-three-to-grow with flying at 3 counters), and 2-MV creatures that draw whenever counters are placed. Weak on turn 1 but scaling.
- **Direction / size:** UNDERrated, +3.5 to +6 pp.
- **Confidence:** medium. About 8 examples. **[expert also wrong]** in about half, graded 2.0–3.5.

### 33. Planeswalkers and sagas: value depends on immediate board effect
- **Pattern:** walkers or sagas whose first activation or chapter removes, wraths, draws or makes tokens are UNDERrated (+3 to +6.5). Walkers whose plus ability is selection-only (surveil) and whose minus abilities are small are OVERrated (-5).
- **Confidence:** medium. About 6 examples. **[expert also wrong]** on the overrated case, graded 4.0.

### 34. Lifegain-matters and life-total-threshold cards are polarized
- **Pattern:** a large lifelinker that gets huge above starting life, or a deathtouch flier that gains on opponent life loss, is UNDERrated (+5). A cheap creature needing many lifegain triggers to grow toward a "power exactly N" wincon is OVERrated (-5).
- **Confidence:** low. Few examples. Rule: lifegain payoffs on a body that is already above rate are good. Payoffs that need many triggers before doing anything are bad.

### 35. Rooms, cases and multi-stage permanents: judge by the first stage
- **Pattern:** two-door enchantments or "solve"-style cases are UNDERrated (+3 to +7) when the cheap half or initial ETB already does something real: draw each turn, ETB damage to a creature, attack-trigger tokens, or an additional land per turn. They are OVERrated (-5 to -11) when the first stage is a passive static that does nothing alone, such as convoke-granting, conditional removal of damaged creatures only, or impulse-play.
- **Confidence:** medium. About 10 examples. Experts were mixed.

---

## Applying these to a new set (summary heuristics)
1. Stretch both tails. Push predicted bombs up and predicted unplayables further down (lessons 1 and 3), unless the bomb's value is delayed (lesson 2).
2. Add +3 to +5 for plain card draw, discard, counterspells, real wraths, utility lands and fixing (lessons 4–7, 11–12). Raise the fixing bonus further when the set has 3-color archetypes or converge.
3. Subtract 4–8 from synergy legends, spell-copy engines, doublers, symmetric drawbacks, compensating removal, temporary tokens, blink and impulse engines (lessons 8, 14–17, 21, 26, 30).
4. Estimate enabler density for each set mechanic before rating its payoffs (lesson 18). Cheap payoffs for dense events run hot, and payoffs for hard-to-trigger events run cold.
5. For crew, saddle, station and equipment, low thresholds and real stats are good, while high thresholds and stat-less utility are bad (lessons 27–28).
