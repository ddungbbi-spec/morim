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
    tower_checkpoint_floor, tower_floor_number,
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

    def test_boss_archetypes_have_distinct_tactics_and_repeat_every_twenty_five_floors(self):
        first_cycle = [create_scaled_tower_boss(floor, {}) for floor in range(5, 30, 5)]
        second_cycle = [create_scaled_tower_boss(floor, {}) for floor in range(30, 55, 5)]

        self.assertEqual(
            [boss.name for boss in first_cycle],
            [
                "5층 철벽의 문지기", "10층 저주의 감시자", "15층 뇌광의 추적자",
                "20층 홍련의 집행자", "25층 천광의 심판자",
            ],
        )
        self.assertEqual(
            [boss.name.split("층 ", 1)[1] for boss in first_cycle],
            [boss.name.split("층 ", 1)[1] for boss in second_cycle],
        )
        self.assertEqual(len({tuple(skill.name for skill in boss.skills) for boss in first_cycle}), 5)
        self.assertEqual(len({tuple(skill.name if skill else None for skill in boss.action_pattern)
                              for boss in first_cycle}), 5)
        self.assertTrue(all(len(boss.boss_phases) == 1 for boss in first_cycle))

    def test_hundredth_floor_guardian_has_unique_two_phase_finale(self):
        guardian = create_scaled_tower_boss(100, {})

        self.assertEqual(guardian.name, "백층의 탑 수호자")
        self.assertEqual([phase.threshold for phase in guardian.boss_phases], [0.6, 0.3])
        self.assertEqual(
            [phase.skill.name for phase in guardian.boss_phases],
            ["안개 장막", "종말의 일격"],
        )
        self.assertIn("심판의 빛", [skill.name for skill in guardian.skills])
        self.assertIn("종말의 일격", [skill.name for skill in guardian.skills])

    def test_checkpoint_uses_highest_completed_ten_floor_boundary(self):
        self.assertEqual(tower_checkpoint_floor({}), 0)
        self.assertEqual(tower_checkpoint_floor({"tower_highest_floor": 9}), 0)
        self.assertEqual(tower_checkpoint_floor({"tower_highest_floor": 10}), 10)
        self.assertEqual(tower_checkpoint_floor({"tower_highest_floor": 27}), 20)
        self.assertEqual(tower_checkpoint_floor({"tower_highest_floor": 100}), 90)

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
        self.assertEqual(game.enemies[0].name, "5층 철벽의 문지기")
        with patch("web_app.random.random", return_value=0.99):
            game._victory()

        state = game.state()
        self.assertEqual(game.flags["tower_highest_floor"], 5)
        self.assertEqual(game.flags["tower_rewarded_floors"], [5])
        self.assertEqual(state["tower"]["current_floor"], 5)
        self.assertEqual(state["tower"]["max_floor"], 100)
        self.assertEqual(state["tower"]["next_boss_floor"], 10)
        self.assertFalse(state["boss_retry"]["available"])

    def test_web_can_resume_from_village_at_highest_checkpoint(self):
        game = WebGame()
        self.assertTrue(game.configure_party(DEFAULT_PARTY_SETUP)["ok"])
        game.advance_dialogue(1)
        game.advance_dialogue()
        game.flags["tower_highest_floor"] = 37
        game.game_map.locations[tower_floor_id(30)].boss_defeated = True

        village_state = game.state()
        self.assertTrue(village_state["tower"]["can_resume"])
        self.assertEqual(village_state["tower"]["checkpoint_floor"], 30)
        result = game.tower_action("resume")

        self.assertTrue(result["ok"])
        self.assertEqual(game.game_map.current_id, tower_floor_id(30))
        self.assertEqual(game.phase, "explore")
        self.assertEqual(result["state"]["tower"]["current_floor"], 30)


if __name__ == "__main__":
    unittest.main()
