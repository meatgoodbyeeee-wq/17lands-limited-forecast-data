package forge.ai;

import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

import forge.game.card.Card;
import forge.game.phase.PhaseHandler;
import forge.game.phase.PhaseType;
import forge.game.player.Player;

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
}
