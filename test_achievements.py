"""업적 소급 판정, 보상, 저장 호환 테스트."""

import tempfile
import unittest
from pathlib import Path

import data
import save as game_save
from achievements import achievement_state
from web_app import DEFAULT_PARTY_SETUP, WEB_ROOT, WebGame


class AchievementTests(unittest.TestCase):
    def setUp(self):
        self.game = WebGame()
        self.assertTrue(self.game.configure_party(DEFAULT_PARTY_SETUP)["ok"])
        self.game.phase = "explore"

    def test_existing_progress_unlocks_achievements_retroactively(self):
        self.game.flags["enemy_bestiary"] = {
            f"적{index}": {"name": f"적{index}", "defeats": 5, "encounters": 5}
            for index in range(5)
        }
        state = achievement_state(self.game.flags, 10, 4)
        ready_ids = {entry["id"] for entry in state["entries"] if entry["status"] == "ready"}
        self.assertTrue({
            "first_victory", "field_researcher", "seasoned_hunter",
            "pathfinder", "village_envoy",
        }.issubset(ready_ids))

    def test_claim_pays_gold_once(self):
        self.game.flags["enemy_bestiary"] = {
            "슬라임": {"name": "슬라임", "defeats": 1, "encounters": 1}
        }
        before = self.game.party.gold
        result = self.game.achievement_action("first_victory")
        self.assertTrue(result["ok"])
        self.assertEqual(self.game.party.gold, before + 30)
        self.assertEqual(
            next(entry for entry in result["state"]["achievements"]["entries"]
                 if entry["id"] == "first_victory")["status"],
            "claimed",
        )
        self.assertFalse(self.game.achievement_action("first_victory")["ok"])
        self.assertEqual(self.game.party.gold, before + 30)

    def test_locked_unknown_and_battle_claims_are_rejected(self):
        self.assertFalse(self.game.achievement_action("seasoned_hunter")["ok"])
        self.assertFalse(self.game.achievement_action("missing")["ok"])
        self.game.phase = "battle"
        self.assertFalse(self.game.achievement_action("first_victory")["ok"])

    def test_claim_record_survives_save_and_load(self):
        self.game.flags["enemy_bestiary"] = {
            "슬라임": {"name": "슬라임", "defeats": 1, "encounters": 1}
        }
        self.assertTrue(self.game.achievement_action("first_victory")["ok"])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "slot.json"
            game_save.save_game(
                self.game.party, self.game.inventory, self.game.game_map,
                self.game.flags, self.game.equipment_inventory, str(path),
                self.game.quest_log,
            )
            party, _, game_map, flags, _, _ = game_save.load_game(str(path))
        state = achievement_state(flags, len(game_map.visited), len(game_map.visited_villages))
        first = next(entry for entry in state["entries"] if entry["id"] == "first_victory")
        self.assertEqual(first["status"], "claimed")
        self.assertEqual(party.gold, self.game.party.gold)

    def test_web_assets_expose_achievement_panel_and_api(self):
        script = Path(WEB_ROOT, "app.js").read_text(encoding="utf-8")
        styles = Path(WEB_ROOT, "styles.css").read_text(encoding="utf-8")
        self.assertIn("openUtility('achievements')", script)
        self.assertIn('utilityMode === "achievements"', script)
        self.assertIn('/api/achievement', script)
        self.assertIn(".utility-card.achievement-claimed", styles)


if __name__ == "__main__":
    unittest.main()
