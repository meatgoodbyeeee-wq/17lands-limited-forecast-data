package forge.ai;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;

import forge.game.card.Card;
import forge.game.combat.Combat;
import forge.game.combat.CombatUtil;
import forge.game.player.Player;
import forge.util.AITimeoutTracker;

/**
 * Research attack pass for self-play (17lands-limited-forecast-data, research/forge_sim/PLAN_attack1.md), enabled only with
 * env ATK1_PATCH=1. After Forge's normal attack declaration, adds attackers that are not needed as blockers when, against a
 * predicted single-block response (one blocker per attacker), the attack loses no more creatures than the opponent, deals
 * lethal damage, or turns spare creatures into 5+ more damage.
 */
public final class ResearchAttack {
    private ResearchAttack() { }

    public static boolean enabled() {
        return "1".equals(System.getenv("ATK1_PATCH"));
    }

    /** Predicted result of an attack against the defender's greedy single blocks. */
    static final class Outcome {
        int damage, ourLost, theirLost, ourValue, theirValue;
    }

    /**
     * Defender's greedy response: attackers in order of unblocked damage; for each, a blocker that kills it and survives,
     * else one that survives without killing, else a trade with a blocker of lower value; otherwise unblocked. If the
     * unblocked damage is lethal, the remaining blockers chump the largest unblocked attackers.
     */
    static Outcome predict(final Player ai, final Player defender, final List<Card> attackers, final List<Card> blockers, final Combat combat) {
        final Outcome o = new Outcome();
        final List<Card> free = new ArrayList<>(blockers);
        final List<Card> order = new ArrayList<>(attackers);
        order.sort(Comparator.comparingInt((Card a) -> ComputerUtilCombat.damageIfUnblocked(a, defender, combat, false)).reversed());
        final List<Card> unblocked = new ArrayList<>();
        for (final Card a : order) {
            AITimeoutTracker.check();
            final int atkValue = ComputerUtilCard.evaluateCreature(a);
            Card eat = null, wall = null, trade = null;
            if (CombatUtil.canAttackerBeBlockedWithAmount(a, 1, defender)) {
                for (final Card b : free) {
                    if (!CombatUtil.canBlock(a, b)) {
                        continue;
                    }
                    final boolean kills = ComputerUtilCombat.canDestroyAttacker(ai, a, b, combat, false);
                    final boolean dies = ComputerUtilCombat.canDestroyBlocker(ai, b, a, combat, false);
                    final int v = ComputerUtilCard.evaluateCreature(b);
                    if (kills && !dies) {
                        if (eat == null || v < ComputerUtilCard.evaluateCreature(eat)) {
                            eat = b;
                        }
                    } else if (!dies) {
                        if (wall == null || v < ComputerUtilCard.evaluateCreature(wall)) {
                            wall = b;
                        }
                    } else if (kills && v <= atkValue) {
                        if (trade == null || v < ComputerUtilCard.evaluateCreature(trade)) {
                            trade = b;
                        }
                    }
                }
            }
            final Card b = eat != null ? eat : wall != null ? wall : trade;
            if (b == null) {
                unblocked.add(a);
                o.damage += ComputerUtilCombat.damageIfUnblocked(a, defender, combat, false);
                continue;
            }
            free.remove(b);
            if (b != wall) {
                o.ourLost++;
                o.ourValue += atkValue;
            }
            if (b == trade) {
                o.theirLost++;
                o.theirValue += ComputerUtilCard.evaluateCreature(b);
            }
        }
        // chump blocks when the unblocked damage is lethal
        for (final Card a : unblocked) {
            if (o.damage < defender.getLife() || free.isEmpty()) {
                break;
            }
            if (!CombatUtil.canAttackerBeBlockedWithAmount(a, 1, defender)) {
                continue;
            }
            Card chump = null;
            for (final Card b : free) {
                if (CombatUtil.canBlock(a, b) && (chump == null || ComputerUtilCard.evaluateCreature(b) < ComputerUtilCard.evaluateCreature(chump))) {
                    chump = b;
                }
            }
            if (chump == null) {
                continue;
            }
            free.remove(chump);
            o.damage -= ComputerUtilCombat.damageIfUnblocked(a, defender, combat, false);
            if (ComputerUtilCombat.canDestroyBlocker(ai, chump, a, combat, false)) {
                o.theirLost++;
                o.theirValue += ComputerUtilCard.evaluateCreature(chump);
            }
            if (ComputerUtilCombat.canDestroyAttacker(ai, a, chump, combat, false)) {
                o.ourLost++;
                o.ourValue += ComputerUtilCard.evaluateCreature(a);
            }
        }
        return o;
    }

    /** Spare creatures to add to the attack on the defending player (empty if none is worth it). */
    public static List<Card> extraAttackers(final Player ai, final Player defender, final Combat combat, final List<Card> spare, final List<Card> blockers) {
        final List<Card> chosen = new ArrayList<>();
        if (spare.isEmpty() || !defender.canLoseLife()) {
            return chosen;
        }
        final List<Card> current = new ArrayList<>(combat.getAttackersOf(defender));
        final Outcome base = predict(ai, defender, current, blockers, combat);
        final List<Card> cands = new ArrayList<>(spare);
        cands.sort(Comparator.comparingInt((Card a) -> ComputerUtilCombat.damageIfUnblocked(a, defender, combat, false)).reversed());
        final List<Card> trial = new ArrayList<>(current);
        int bestDamage = base.damage;
        for (int i = 0; i < cands.size(); i++) {
            trial.add(cands.get(i));
            final Outcome o = predict(ai, defender, trial, blockers, combat);
            final int dDamage = o.damage - base.damage;
            final int dOurLost = o.ourLost - base.ourLost, dTheirLost = o.theirLost - base.theirLost;
            final int dOurValue = o.ourValue - base.ourValue, dTheirValue = o.theirValue - base.theirValue;
            final boolean lethal = o.damage >= defender.getLife();
            final boolean even = dDamage > 0 && dOurLost <= dTheirLost && dOurValue <= 1.5 * dTheirValue;
            final boolean spareDamage = dDamage >= 5 && dOurLost - dTheirLost <= 1;
            if ((lethal || even || spareDamage) && o.damage > bestDamage) {
                bestDamage = o.damage;
                chosen.clear();
                chosen.addAll(cands.subList(0, i + 1));
            }
        }
        return chosen;
    }
}
