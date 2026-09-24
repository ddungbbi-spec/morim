"""적 도감 발견·처치·저장 호환 테스트."""

import tempfile
import unittest
from pathlib import Path

import data
import save as game_save
from bestiary import MASTERED_DEFEATS, bestiary_state, discover_enemies
from web_app import DEFAULT_PARTY_SETUP, WEB_ROOT, WebGame


class BestiaryTests(unittest.TestCase):
    def setUp(self):
        self.game = WebGame()
        self.assertTrue(self.game.configure_party(DEFAULT_PARTY_SETUP)["ok"])

    def test_battle_discovers_enemies_and_victory_records_defeats_once(self):
        enemies = [data.create_slime(), data.create_wild_wolf()]
        self.game._begin_battle(enemies, "training", "도감 시험")

        state = self.game.state()["bestiary"]
        self.assertEqual(state["discovered"], 2)
        self.assertEqual(state["total_defeats"], 0)
        self.assertTrue(any("적 도감 신규 등록" in line for line in self.game.logs))

        self.game._victory()
        self.game._victory()
        state = self.game.state()["bestiary"]
        self.assertEqual(state["total_defeats"], 2)
        self.assertEqual({entry["defeats"] for entry in state["entries"]}, {1})

    def test_fifth_defeat_marks_enemy_as_mastered(self):
        for _ in range(MASTERED_DEFEATS):
            self.game._begin_battle([data.create_slime()], "training", "숙련 시험")
            self.game._victory()

        state = self.game.state()["bestiary"]
        self.assertEqual(state["mastered"], 1)
        self.assertTrue(state["entries"][0]["mastered"])
        self.assertTrue(any("도감 숙련 달성" in line for line in self.game.logs))

    def test_bestiary_survives_save_and_load(self):
        self.game._begin_battle([data.create_goblin()], "training", "저장 시험")
        self.game._victory()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "slot.json"
            game_save.save_game(
                self.game.party, self.game.inventory, self.game.game_map,
                self.game.flags, self.game.equipment_inventory, str(path),
                self.game.quest_log,
            )
            _, _, _, flags, _, _ = game_save.load_game(str(path))

        state = bestiary_state(flags)
        self.assertEqual(state["discovered"], 1)
        self.assertEqual(state["entries"][0]["name"], "고블린")
        self.assertEqual(state["entries"][0]["defeats"], 1)

    def test_malformed_legacy_bestiary_is_ignored_in_state(self):
        state = bestiary_state({"enemy_bestiary": {"깨진 항목": "invalid"}})
        self.assertEqual(state["discovered"], 0)

    def test_corrupt_counts_are_repaired_on_next_encounter(self):
        flags = {"enemy_bestiary": {"슬라임": {"encounters": "?", "defeats": None}}}
        discover_enemies(flags, [data.create_slime()])
        state = bestiary_state(flags)
        self.assertEqual(state["entries"][0]["encounters"], 1)
        self.assertEqual(state["entries"][0]["defeats"], 0)

    def test_web_assets_expose_bestiary_panel(self):
        script = Path(WEB_ROOT, "app.js").read_text(encoding="utf-8")
        styles = Path(WEB_ROOT, "styles.css").read_text(encoding="utf-8")
        self.assertIn("openUtility('bestiary')", script)
        self.assertIn('utilityMode === "bestiary"', script)
        self.assertIn(".bestiary-card.mastered", styles)


if __name__ == "__main__":
    unittest.main()
