import gzip, csv, json, tempfile, unittest, urllib.error
from pathlib import Path
import skill_site_fetch as t


def api(url):
    if "scryfall.com/bulk-data" in url:
        return 200, json.dumps({"download_uri": "https://data.scryfall.io/oracle.json"}).encode()
    if "data.scryfall.io" in url:
        return 200, json.dumps([{"name": "A", "cmc": 2.0, "type_line": "Creature — Elf", "colors": ["G"]},
                                {"name": "B // C", "cmc": 3.0, "card_faces": [{"name": "B", "type_line": "Instant", "colors": ["U"]}, {"name": "C"}]}]).encode()
    k = 4 if "user_group" not in url else (1 if "top" in url else 2)
    return 200, json.dumps([{"name": "A", "ever_drawn_game_count": 10 * k, "ever_drawn_win_rate": 0.55, "avg_pick": 3.1, "url": "x", "rarity": "common", "types": ["Creature"]},
                            {"name": "B", "ever_drawn_game_count": 5 * k, "ever_drawn_win_rate": None, "avg_pick": 5.0, "rarity": "uncommon"}]).encode()


class T(unittest.TestCase):
    def test_run(self):
        d = tempfile.mkdtemp()
        log, rows, meta = t.run(["XXX"], d, getter=api, pause=0, retry_wait=0)
        self.assertEqual([r["group"] for r in log], ["all", "top", "middle", "bottom"])
        self.assertEqual(log[1]["share_of_all"], 0.25); self.assertFalse(log[1]["group_ignored"])
        with gzip.open(Path(d) / "site_groups.csv.gz", "rt") as f:
            R = list(csv.DictReader(f))
        self.assertEqual(len(R), 8); self.assertNotIn("url", R[0]); self.assertIn("avg_pick", R[0]); self.assertNotIn("types", R[0])
        with gzip.open(Path(d) / "card_scryfall.csv.gz", "rt") as f:
            S = {r["name"]: r for r in csv.DictReader(f)}
        self.assertEqual(S["A"]["mv"], "2.0"); self.assertEqual(S["B"]["type_line"], "Instant"); self.assertEqual(meta["scryfall"]["matched"], 2)

    def test_ignored_group_and_failure(self):
        d = tempfile.mkdtemp()
        same = lambda url: api(url.replace("user_group", "x")) if "17lands" in url else api(url)
        log, rows, meta = t.run(["XXX"], d, getter=same, pause=0, retry_wait=0)
        self.assertTrue(log[1]["group_ignored"])
        def bad(url):
            raise urllib.error.HTTPError(url, 403, "no", None, None)
        log, rows, meta = t.run(["XXX"], tempfile.mkdtemp(), getter=bad, pause=0, retry_wait=0)
        self.assertEqual(log[0]["error"], "HTTP 403"); self.assertIn("error", meta["scryfall"])

    def test_refused(self):
        with self.assertRaises(SystemExit):
            t.run(["TRK"], tempfile.mkdtemp(), getter=api, pause=0)


if __name__ == "__main__":
    unittest.main()
