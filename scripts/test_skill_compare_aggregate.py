"""Mock-data test for skill_compare_aggregate.py: compares the matrix aggregation with a plain per-row count."""
import gzip, json, subprocess, sys, tempfile, unittest
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).resolve().parent


def make_mock(path, n=3000, seed=3):
    r = np.random.default_rng(seed)
    cards = ["Alpha", "Beta Card", "Gamma, the Third", "Island"]
    start = pd.Timestamp("2026-01-01T00:00:00Z")
    d = pd.DataFrame({
        "expansion": "XXX", "event_type": "PremierDraft",
        "draft_id": [f"d{i // 3}" for i in range(n)],
        "draft_time": [(start + pd.Timedelta(hours=float(h))).isoformat() for h in r.uniform(0, 24 * 32, n)],
        "game_time": "", "build_index": 0, "match_number": r.integers(1, 9, n), "game_number": 1,
        "rank": r.choice(["gold", "platinum", "diamond", "mythic", None], n), "opp_rank": r.choice(["gold", "diamond", None], n),
        "main_colors": r.choice(["WU", "BR", "G", "UBG", None], n), "splash_colors": r.choice(["", "R", None], n),
        "on_play": r.choice([True, False], n), "num_mulligans": r.integers(0, 4, n), "opp_num_mulligans": r.integers(0, 2, n),
        "opp_colors": r.choice(["WB", "UR"], n), "num_turns": r.integers(4, 25, n), "won": r.choice([True, False], n),
        "user_n_games_bucket": r.choice([1, 10, 50, 100, 500, 1000], n),
        "user_game_win_rate_bucket": r.choice([0.3, 0.46, 0.5, 0.56, 0.6, 0.62, 0.64, 0.7, np.nan], n)})
    for c in cards:
        dk = r.integers(0, 3, n); d["deck_" + c] = dk; d["sideboard_" + c] = r.integers(0, 2, n)
        d["opening_hand_" + c] = np.minimum(dk, r.integers(0, 2, n)); d["drawn_" + c] = np.minimum(dk, r.integers(0, 2, n))
        d["tutored_" + c] = (r.uniform(size=n) < 0.02).astype(int)
    d.to_csv(path, index=False, compression="gzip")
    return d, cards, start


class T(unittest.TestCase):
    def test_against_naive(self):
        tmp = Path(tempfile.mkdtemp()); f = tmp / "mock.csv.gz"
        d, cards, start = make_mock(f)
        out = tmp / "out"
        subprocess.run([sys.executable, str(HERE / "skill_compare_aggregate.py"), "--set", "XXX", "--local-file", str(f), "--out-dir", str(out), "--chunksize", "700"], check=True)
        C = pd.read_csv(out / "XXX_cards.csv.gz"); G = pd.read_csv(out / "XXX_games.csv.gz"); man = json.loads((out / "XXX_skill_manifest.json").read_text())
        t = pd.to_datetime(d.draft_time, utc=True); w = d[(t >= t.min()) & (t < t.min() + pd.Timedelta(days=28))].copy()
        self.assertEqual(man["games"], len(w))
        wr, ng = w.user_game_win_rate_bucket, w.user_n_games_bucket
        top = (ng >= 50) & (wr >= 0.5999); b5 = (ng >= 50) & (wr >= 0.6399)
        for c in cards:
            gih = (w["opening_hand_" + c] > 0) | (w["drawn_" + c] > 0) | (w["tutored_" + c] > 0)
            got = C[(C.card_name == c) & C.grp.isin(["B4", "B5"])][["gih_g", "gih_w"]].sum()
            self.assertEqual(got.gih_g, int((gih & top).sum())); self.assertEqual(got.gih_w, int((gih & top & w.won).sum()))
            gd = (w["drawn_" + c] > 0) & (w["opening_hand_" + c] == 0)
            self.assertEqual(int(C[(C.card_name == c) & (C.grp == "B5")].gd_w.sum()), int((gd & b5 & w.won).sum()))
            pool = (w["deck_" + c] + w["sideboard_" + c]) > 0
            self.assertEqual(int(C[(C.card_name == c) & C.grp.isin(["B1", "B2", "B3", "B4", "B5", "L"])].pool_g.sum()), int((pool & ~((ng >= 50) & wr.isna())).sum()))
            self.assertEqual(int(C[(C.card_name == c) & (C.grp == "T500")].copies.sum()), int(w.loc[top & (ng >= 500), "deck_" + c].sum()))
            gns = (w["deck_" + c] > 0) & ~gih
            self.assertEqual(int(C[(C.card_name == c) & C.grp.isin(["B4", "B5"])].gns_w.sum()), int((gns & top & w.won).sum()))
        allg = G[(G.dim == "all")]
        self.assertEqual(int(allg.games.sum()), len(w)); self.assertEqual(int(allg.wins.sum()), int(w.won.sum()))
        op = G[(G.dim == "on_play") & (G.val.astype(str) == "1") & G.band.isin(["B4", "B5"])]
        self.assertEqual(int(op.wins.sum()), int((top & w.on_play & w.won).sum()))
        mc = G[(G.dim == "main_colors") & (G.val.astype(str) == "UBG")]
        self.assertEqual(int(mc.games.sum()), int((w.main_colors == "UBG").sum()))
        self.assertEqual(int(G[G.dim == "turns"].games.sum()), len(w))


if __name__ == "__main__":
    unittest.main()
