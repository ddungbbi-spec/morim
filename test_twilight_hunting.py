"""황혼장터 파생 사냥터, 전용 의뢰, 보스 보상 통합 테스트."""

import tempfile
import unittest
from unittest.mock import patch

import data
from commissions import accept_commission, commission_state, offer_commission, record_defeats
from web_app import DEFAULT_PARTY_SETUP, WebGame
from world import MAP_REGIONS, build_world


class FixedChoice:
    def __init__(self, commission_id):
        self.commission_id = commission_id

    def choice(self, choices):
        return next(choice for choice in choices if choice.commission_id == self.commission_id)


class TwilightHuntingTests(unittest.TestCase):
    def setUp(self):
        self.game = WebGame()
        self.assertTrue(self.game.configure_party(DEFAULT_PARTY_SETUP)["ok"])
        self.game.advance_dialogue(1)
        self.game.advance_dialogue()

    def test_hunting_route_branches_from_village_and_returns_both_ways(self):
        world = build_world()
        route = [
            "twilight_village", "red_reed_field", "twilight_hunter_camp",
            "windscar_ravine", "duskfang_den",
        ]
        for current_id, next_id in zip(route, route[1:]):
            self.assertIn(next_id, world.locations[current_id].exits.values())
            self.assertIn(current_id, world.locations[next_id].exits.values())

        twilight = next(region for region in MAP_REGIONS if region["id"] == "twilight")
        self.assertEqual(len(twilight["locations"]), 7)
        self.assertTrue(set(route).issubset(twilight["locations"]))

    def test_each_hunting_ground_has_distinct_encounters(self):
        world = build_world()
        field_enemies = {
            enemy.name
            for factory in world.locations["red_reed_field"].encounter_pool
            for enemy in factory()
        }
        ravine_enemies = {
            enemy.name
            for factory in world.locations["windscar_ravine"].encounter_pool
            for enemy in factory()
        }
        self.assertIn("붉은갈기 승냥이", field_enemies)
        self.assertIn("협곡 도적술사", ravine_enemies)
        self.assertGreater(
            world.locations["windscar_ravine"].encounter_chance,
            world.locations["red_reed_field"].encounter_chance,
        )

        boss = world.locations["duskfang_den"].boss()[0]
        self.assertEqual(boss.name, "황혼송곳니 우두머리")
        self.assertTrue(boss.smart_ai)
        self.assertTrue(boss.boss_phases)
        self.assertEqual(world.locations["duskfang_den"].loot_equipment,
                         data.DUSKFANG_TALISMAN)
        self.assertIn(data.DUSKFANG_TALISMAN.name, data.PROTECTED_EQUIPMENT_NAMES)
        self.assertIs(data.EQUIPMENT_BY_NAME[data.DUSKFANG_TALISMAN.name],
                      data.DUSKFANG_TALISMAN)

    def test_camp_event_records_choice_and_supplies_once(self):
        self.game.game_map.move_to("twilight_hunter_camp")
        self.game._enter_current_location()
        self.assertEqual(self.game.phase, "dialogue")
        self.assertTrue(self.game.advance_dialogue(0)["ok"])
        self.assertTrue(self.game.flags["twilight_tracks_studied"])
        self.assertTrue(self.game.advance_dialogue()["ok"])
        self.assertTrue(self.game.game_map.current.loot_claimed)
        self.assertEqual(sum(item.name == data.ANTIDOTE.name for item in self.game.inventory), 1)

    def test_new_commission_tracks_hunting_enemy(self):
        flags = {}
        _, template = offer_commission(
            flags, "twilight_village", FixedChoice("twilight_jackal_hunt")
        )
        self.assertEqual(template.required, 3)
        self.assertTrue(accept_commission(flags, "twilight_village"))
        self.assertEqual(record_defeats(flags, ["붉은갈기 승냥이"]), [])
        self.assertEqual(record_defeats(flags, ["붉은갈기 승냥이"]), [])
        self.assertEqual(record_defeats(flags, ["붉은갈기 승냥이"]), ["붉은 갈대의 울음"])
        self.assertEqual(commission_state(flags, "twilight_village")["status"], "ready")

    def test_boss_reward_is_unique_retryable_and_persists(self):
        den = self.game.game_map.locations["duskfang_den"]
        self.game.game_map.move_to("duskfang_den")
        den.dialogue_played = True
        self.game._enter_current_location()
        self.assertEqual(self.game.phase, "battle")
        self.assertEqual(self.game.enemies[0].name, "황혼송곳니 우두머리")
        with patch("web_app.random.random", return_value=0.99):
            self.game._victory()
        self.assertTrue(den.boss_defeated)
        self.assertTrue(den.loot_claimed)
        self.assertEqual(
            sum(item.name == data.DUSKFANG_TALISMAN.name
                for item in self.game.equipment_inventory),
            1,
        )

        self.assertTrue(self.game.boss_action("retry")["ok"])
        with patch("web_app.random.random", return_value=0.99):
            self.game._victory()
        self.assertEqual(
            sum(item.name == data.DUSKFANG_TALISMAN.name
                for item in self.game.equipment_inventory),
            1,
        )

        with tempfile.TemporaryDirectory() as directory:
            self.game.save_dir = directory
            self.assertTrue(self.game.save_action("save", 1)["ok"])
            den.boss_defeated = False
            den.loot_claimed = False
            self.game.equipment_inventory.clear()
            self.assertTrue(self.game.save_action("load", 1)["ok"])
            loaded_den = self.game.game_map.locations["duskfang_den"]
            self.assertTrue(loaded_den.boss_defeated)
            self.assertTrue(loaded_den.loot_claimed)
            self.assertEqual(
                sum(item.name == data.DUSKFANG_TALISMAN.name
                    for item in self.game.equipment_inventory),
                1,
            )


if __name__ == "__main__":
    unittest.main()
