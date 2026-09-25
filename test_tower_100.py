"""100층 도전의 탑 규칙과 보상 회귀 테스트."""

import unittest
from unittest.mock import patch

import data
from models import Party
from web_app import DEFAULT_PARTY_SETUP, WebGame
from world import (
    MAP_REGIONS, TOWER_BOSS_INTERVAL, TOWER_MAX_FLOOR,
    build_world, create_scaled_tower_boss, grant_tower_boss_reward,
    is_tower_boss_floor, reset_tower_challenge, tower_floor_id,
    tower_floor_number,
)


class HundredFloorTowerTests(unittest.TestCase):
    def test_tower_has_one_hundred_connected_floors_and_twenty_bosses(self):
        world = build_world()
        tower_region = next(region for region in MAP_REGIONS if region["id"] == "tower")
        self.assertEqual(len(tower_region["locations"]), TOWER_MAX_FLOOR)
        self.assertEqual(tower_floor_number("tower_summit"), 100)

        boss_floors = []
        for floor in range(1, TOWER_MAX_FLOOR + 1):
            location = world.locations[tower_floor_id(floor)]
            self.assertEqual(location.name.endswith(f"{floor}층"), True)
            if floor < TOWER_MAX_FLOOR:
                self.assertIn(tower_floor_id(floor + 1), location.exits.values())
            if floor > 1:
                self.assertIn(tower_floor_id(floor - 1), location.exits.values())
            if location.boss:
                boss_floors.append(floor)

        self.assertEqual(
            boss_floors,
            list(range(TOWER_BOSS_INTERVAL, TOWER_MAX_FLOOR + 1, TOWER_BOSS_INTERVAL)),
        )
        self.assertEqual(len(boss_floors), 20)

    def test_boss_strength_rises_with_floor_and_repeat_tier(self):
        floor_five = create_scaled_tower_boss(5, {})
        floor_fifty = create_scaled_tower_boss(50, {})
        repeated = create_scaled_tower_boss(50, {"tower_clear_count": 1})
        self.assertLess(floor_five.max_hp, floor_fifty.max_hp)
        self.assertLess(floor_five.attack, floor_fifty.attack)
        self.assertGreater(repeated.max_hp, floor_fifty.max_hp)
        self.assertGreater(repeated.attack, floor_fifty.attack)
        self.assertTrue(is_tower_boss_floor(100))
        self.assertFalse(is_tower_boss_floor(99))

    def test_boss_rewards_are_once_per_run_and_equipment_arrives_every_ten_floors(self):
        flags = {}
        party = Party([data.create_warrior("도전자")], gold=0)
        equipment = []

        gold_five, item_five = grant_tower_boss_reward(flags, 5, party, equipment)
        self.assertGreater(gold_five, 0)
        self.assertIsNone(item_five)
        with patch("world.data.generate_random_equipment", return_value=data.IRON_SWORD):
            gold_ten, item_ten = grant_tower_boss_reward(flags, 10, party, equipment)
        self.assertGreater(gold_ten, gold_five)
        self.assertIs(item_ten, data.IRON_SWORD)
        self.assertEqual(equipment, [data.IRON_SWORD])
        self.assertEqual(flags["tower_highest_floor"], 10)

        before_gold = party.gold
        duplicate = grant_tower_boss_reward(flags, 10, party, equipment)
        self.assertEqual(duplicate, (0, None))
        self.assertEqual(party.gold, before_gold)
        self.assertEqual(equipment, [data.IRON_SWORD])

    def test_new_challenge_resets_all_boss_gates_and_run_rewards(self):
        world = build_world()
        for floor in range(5, 101, 5):
            world.locations[tower_floor_id(floor)].boss_defeated = True
        flags = {
            "tower_clear_count": 1,
            "tower_rewarded_floors": list(range(5, 101, 5)),
            "tower_highest_floor": 100,
        }

        self.assertTrue(reset_tower_challenge(world, flags))
        self.assertTrue(flags["tower_challenge_active"])
        self.assertEqual(flags["tower_rewarded_floors"], [])
        self.assertEqual(flags["tower_highest_floor"], 0)
        for floor in range(5, 101, 5):
            self.assertFalse(world.locations[tower_floor_id(floor)].boss_defeated)

    def test_web_boss_victory_records_floor_reward_and_blocks_direct_retry(self):
        game = WebGame()
        self.assertTrue(game.configure_party(DEFAULT_PARTY_SETUP)["ok"])
        game.advance_dialogue(1)
        game.advance_dialogue()
        game.game_map.current_id = tower_floor_id(5)
        game._enter_current_location()

        self.assertEqual(game.phase, "battle")
        self.assertIn("5층 관문 수호자", game.enemies[0].name)
        with patch("web_app.random.random", return_value=0.99):
            game._victory()

        state = game.state()
        self.assertEqual(game.flags["tower_highest_floor"], 5)
        self.assertEqual(game.flags["tower_rewarded_floors"], [5])
        self.assertEqual(state["tower"]["current_floor"], 5)
        self.assertEqual(state["tower"]["max_floor"], 100)
        self.assertEqual(state["tower"]["next_boss_floor"], 10)
        self.assertFalse(state["boss_retry"]["available"])


if __name__ == "__main__":
    unittest.main()
