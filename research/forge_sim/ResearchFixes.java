package forge.ai;

import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

import forge.game.ability.ApiType;
import forge.game.card.Card;
import forge.game.card.CardCollection;
import forge.game.card.CardLists;
import forge.game.zone.ZoneType;
import forge.game.phase.PhaseHandler;
import forge.game.phase.PhaseType;
import forge.game.player.Player;
import forge.game.spellability.SpellAbility;

/**
 * Research fixes for self-play (17lands-limited-forecast-data, research/forge_sim), enabled only with env S2_PATCH=1.
 * Shared helper: hold a card for a better moment for at most one opponent turn.
 */
public final class ResearchFixes {
    private ResearchFixes() { }

    public static boolean enabled() {
        return "1".equals(System.getenv("S2_PATCH"));
    }

    private static final Map<String, Integer> HELD = new ConcurrentHashMap<>();

    /**
     * True once the card has been held through one full opponent turn: from the AI's next own turn (after the draw step)
     * it should be used as a normal sorcery-speed play instead of waiting for a better window.
     */
    public static boolean holdExpired(final String what, final Card card, final Player ai) {
        final PhaseHandler ph = ai.getGame().getPhaseHandler();
        final String key = what + ":" + System.identityHashCode(ai.getGame()) + ":" + card.getId();
        final Integer held = HELD.putIfAbsent(key, ph.getTurn());
        return held != null && ph.getTurn() >= held + 2 && ph.isPlayerTurn(ai) && ph.getPhase().isAfter(PhaseType.DRAW);
    }

    /** End step of the opponent's turn, right before the AI's own turn. */
    public static boolean isOppEndStep(final Player ai) {
        final PhaseHandler ph = ai.getGame().getPhaseHandler();
        return ph.is(PhaseType.END_OF_TURN) && ph.getNextTurn().equals(ai);
    }

    /** Instant research fixes (PLAN_instants1.md), enabled only with env INS1_PATCH=1. */
    public static boolean instantsEnabled() {
        return "1".equals(System.getenv("INS1_PATCH"));
    }

    /** Diagnostic output (INS_DIAG=1): one tab-separated line per decision. */
    public static void diag(final String what, final Card card, final String result) {
        if ("1".equals(System.getenv("INS_DIAG"))) {
            System.out.println("InsDiag:\t" + what + "\t" + (card == null ? "" : card.getName()) + "\t" + result);
        }
    }

    /**
     * P1: instant removal that should wait for the opponent's turn (L5B), widened: target restrictions on creatures,
     * planeswalkers or nonland permanents (not own ones), bounce and tuck from the battlefield, and edicts.
     */
    public static boolean isInstantRemoval(final SpellAbility sa, final ApiType api) {
        final String valid = sa.getParamOrDefault("ValidTgts", "");
        if (api == ApiType.Sacrifice) {
            return valid.startsWith("Opponent") && sa.getParamOrDefault("SacValid", "").startsWith("Creature");
        }
        if (valid.isEmpty() || valid.contains("YouCtrl")) {
            return false;
        }
        for (final String t : valid.split(",")) {
            final String k = t.trim();
            if (!k.startsWith("Creature") && !k.startsWith("Planeswalker") && !k.startsWith("Permanent.nonLand")) {
                return false;
            }
        }
        if (api == ApiType.Destroy || api == ApiType.DealDamage) {
            return true;
        }
        if (api == ApiType.ChangeZone) {
            final String dest = sa.getParamOrDefault("Destination", "");
            return "Battlefield".equals(sa.getParam("Origin")) && ("Exile".equals(dest) || "Hand".equals(dest) || "Library".equals(dest));
        }
        if (api == ApiType.Pump) {
            return sa.isCurse() && sa.getParamOrDefault("NumDef", "").startsWith("-");
        }
        return false;
    }

    /** P2: a curse whose sub ability makes one of the AI's creatures deal damage equal to its power (Flourishing Grapple). */
    public static boolean isPowerDamageCurse(final SpellAbility sa) {
        final SpellAbility sub = sa.getSubAbility();
        return sa.getApi() == ApiType.Animate && sa.isCurse() && sa.usesTargeting() && sub != null && sub.getApi() == ApiType.Pump
                && "PowerDmg".equals(sub.getParam("AILogic")) && sub.usesTargeting();
    }

    /** P2: target the most valuable opposing permanent one of the AI's creatures can kill with its power; that creature deals the damage. */
    public static boolean choosePowerDamageCurse(final Player ai, final SpellAbility sa) {
        final SpellAbility sub = sa.getSubAbility();
        sub.resetTargets();
        final CardCollection mine = CardLists.getTargetableCards(ai.getCreaturesInPlay(), sub);
        final CardCollection theirs = CardLists.getTargetableCards(ai.getOpponents().getCardsIn(ZoneType.Battlefield), sa);
        Card bestTgt = null, bestSrc = null;
        int bestValue = -1;
        for (final Card t : theirs) {
            final int need = t.isCreature() ? t.getNetToughness() - t.getDamage() : t.isPlaneswalker() ? t.getCurrentLoyalty() : Integer.MAX_VALUE;
            final int value = t.isCreature() ? ComputerUtilCard.evaluateCreature(t) : 150 + 20 * t.getCurrentLoyalty();
            if (value <= bestValue) {
                continue;
            }
            Card src = null;
            for (final Card m : mine) {
                if (m.getNetPower() >= need && (src == null || ComputerUtilCard.evaluateCreature(m) < ComputerUtilCard.evaluateCreature(src))) {
                    src = m;
                }
            }
            if (src != null) {
                bestTgt = t; bestSrc = src; bestValue = value;
            }
        }
        if (bestTgt == null) {
            diag("PowerDmgCurse", sa.getHostCard(), "no-target");
            return false;
        }
        sa.getTargets().add(bestTgt);
        sub.getTargets().add(bestSrc);
        diag("PowerDmgCurse", sa.getHostCard(), "cast");
        return true;
    }
}
