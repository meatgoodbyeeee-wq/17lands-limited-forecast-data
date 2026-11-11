import json, tempfile, unittest, urllib.error
from pathlib import Path
import top_site_fetch as t


def fake_json(scale):
    return json.dumps([{"name": "A", "game_count": 100 * scale, "win_rate": 0.55, "ever_drawn_game_count": 40 * scale, "ever_drawn_win_rate": 0.6, "color": "W"},
                       {"name": "B", "game_count": 50 * scale, "win_rate": 0.5, "ever_drawn_game_count": 20 * scale, "ever_drawn_win_rate": None, "color": "U"}])


class T(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        (Path(self.d) / "XXX_case6_manifest.json").write_text(json.dumps({"set": "XXX", "window_start": "2026-06-23T15:51:03+00:00", "window_end": "2026-07-21T15:51:03+00:00", "has_user_wr_bucket": True}))

    def test_urls_and_merge(self):
        seen = []
        def getter(url):
            seen.append(url)
            return 200, fake_json(1 if "user_group=top" in url else 4)
        log, rows = t.run(["XXX"], self.d, getter=getter, pause=0)
        self.assertEqual(len(seen), 2)
        self.assertIn("expansion=XXX", seen[0]); self.assertIn("start_date=2026-06-23", seen[0]); self.assertIn("end_date=2026-07-21", seen[0])
        self.assertNotIn("user_group", seen[0]); self.assertIn("user_group=top", seen[1])
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["all_gih_n"], 160); self.assertEqual(rows[0]["top_gih_n"], 40)
        self.assertFalse(log[-1]["user_group_ignored"])
        self.assertIn("color", log[0]["keys"])

    def test_ignored_param_detected(self):
        log, rows = t.run(["XXX"], self.d, getter=lambda url: (200, fake_json(1)), pause=0)
        self.assertTrue(log[-1]["user_group_ignored"])

    def test_failure_is_logged_not_raised(self):
        def getter(url):
            raise urllib.error.HTTPError(url, 403, "Forbidden", None, None)
        log, rows = t.run(["XXX"], self.d, getter=getter, pause=0, retry_wait=0)
        self.assertEqual(log[0]["error"], "HTTP 403"); self.assertEqual(rows, [])

    def test_refused(self):
        with self.assertRaises(SystemExit):
            t.run(["FRA"], self.d, getter=lambda u: (200, "[]"), pause=0)


if __name__ == "__main__":
    unittest.main()
