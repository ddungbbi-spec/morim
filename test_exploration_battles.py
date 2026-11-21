"""도주·재진입·저장 복원 시 탐험 전투의 진행 기록을 검증한다."""

import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import data
import save
from map import GameMap, Location, explore
from models import Party
from web_app import DEFAULT_PARTY_SETUP, WebGame
from world import build_world, is_tower_floor_cleared, tower_floor_id


class ExplorationBattleTests(unittest.TestCase):
    def ready_game(self, save_dir=None):
        game = WebGame(save_dir=save_dir)
        game.configure_party(DEFAULT_PARTY_SETUP)
        game.advance_dialogue(1)
        game.advance_dialogue()
        return game

    def test_web_tower_flee_returns_to_village_without_progress_or_rewards(self):
        game = self.ready_game()
        game.move("도전의 탑으로 향한다")
        before = (game.party.gold, list(game.inventory), list(game.equipment_inventory),
                  [member.exp for member in game.party.members])
        with patch("web_app.random.random", return_value=0.0):
            result = game.act({"type": "flee"})
        self.assertTrue(result["ok"])
        self.assertEqual(game.game_map.current_id, "village")
        self.assertEqual(game.phase, "explore")
        self.assertEqual(game.battle_context, "")
        self.assertFalse(is_tower_floor_cleared(game.flags, 1))
        self.assertEqual(before, (game.party.gold, game.inventory, game.equipment_inventory,
                                  [member.exp for member in game.party.members]))
        game.move("도전의 탑으로 향한다")
        self.assertEqual(game.phase, "battle")
        self.assertEqual(game.battle_context, "tower_floor")

    def test_web_failed_tower_flee_stays_in_battle_without_progress(self):
        game = self.ready_game()
        game.move("도전의 탑으로 향한다")
        with patch("web_app.random.random", return_value=0.999999):
            self.assertFalse(game._attempt_flee())
        self.assertEqual(game.phase, "battle")
        self.assertEqual(game.game_map.current_id, tower_floor_id(1))
        self.assertFalse(is_tower_floor_cleared(game.flags, 1))

    def test_web_load_restarts_only_uncleared_tower_floor(self):
        with tempfile.TemporaryDirectory() as directory:
            for cleared in (False, True):
                with self.subTest(cleared=cleared):
                    source = self.ready_game()
                    source.game_map.move_to(tower_floor_id(2))
                    if cleared:
                        source.flags["tower_cleared_floors"] = [2]
                    save.save_game(
                        source.party, source.inventory, source.game_map, source.flags,
                        source.equipment_inventory, path=save.slot_path(1, directory),
                        quest_log=source.quest_log,
                    )
                    game = WebGame(save_dir=Path(directory))
                    result = game.save_action("load", 1)
                    self.assertTrue(result["ok"])
                    self.assertEqual(game.phase, "explore" if cleared else "battle")
                    self.assertEqual(game.battle_context, "" if cleared else "tower_floor")

    @staticmethod
    def flee(battle):
        battle.fled = True
        return True

    def test_console_tower_flee_never_records_clear_or_kills(self):
        world = build_world()
        for location in world.locations.values():
            location.dialogue_played = True
        world.move_to(tower_floor_id(1))
        flags = {}
        party = Party([data.create_warrior("도전자")], gold=123)
        with patch("map.Battle.run", autospec=True, side_effect=self.flee), \
                patch("map.record_defeats") as record, \
                patch("map.prompt_index", side_effect=lambda prompt, count: count - 1), \
                patch("map.prompt_yes_no", return_value=True), redirect_stdout(io.StringIO()):
            self.assertFalse(explore(world, party, [], flags, []))
        record.assert_not_called()
        self.assertEqual(world.current_id, "village")
        self.assertFalse(is_tower_floor_cleared(flags, 1))
        self.assertNotIn("tower_highest_floor", flags)
        self.assertEqual(party.gold, 123)

    def test_console_normal_encounter_flee_never_records_kills(self):
        start = Location("start", "출발", "", exits={"이동": "field"})
        field = Location("field", "들판", "", encounter_chance=1.0,
                         encounter_pool=[lambda: [data.create_slime()]])
        world = GameMap([start, field], "start")
        choices = iter([0, -1])
        with patch("map.Battle.run", autospec=True, side_effect=self.flee), \
                patch("map.record_defeats") as record, \
                patch("map.prompt_index", side_effect=lambda prompt, count: next(choices) % count), \
                patch("map.prompt_yes_no", return_value=True), redirect_stdout(io.StringIO()):
            self.assertFalse(explore(world, Party([data.create_warrior("모험가")]), []))
        record.assert_not_called()
        self.assertEqual(world.current_id, "field")

    def test_console_tower_victory_records_once_after_resuming_on_floor(self):
        world = build_world()
        world.move_to(tower_floor_id(2))
        flags = {}
        with patch("map.Battle.run", return_value=True) as battle, \
                patch("map.record_defeats", return_value=[]) as record, \
                patch("map.prompt_index", side_effect=lambda prompt, count: count - 1), \
                patch("map.prompt_yes_no", return_value=True), redirect_stdout(io.StringIO()):
            self.assertFalse(explore(world, Party([data.create_warrior("도전자")]), [], flags))
        battle.assert_called_once()
        record.assert_called_once()
        self.assertTrue(is_tower_floor_cleared(flags, 2))


if __name__ == "__main__":
    unittest.main()
