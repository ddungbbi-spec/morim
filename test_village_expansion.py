"""마을 공통 시설, 특화 이벤트, 황혼장터 권역 통합 테스트."""

import unittest

import data
from commissions import accept_commission, commission_state, offer_commission, record_defeats
from web_app import DEFAULT_PARTY_SETUP, WebGame
from world import MAP_REGIONS, build_world


class FixedChoice:
    def __init__(self, commission_id):
        self.commission_id = commission_id

    def choice(self, choices):
        return next(choice for choice in choices if choice.commission_id == self.commission_id)


class VillageExpansionTests(unittest.TestCase):
    def test_each_village_has_full_hub_services_and_unique_event_map(self):
        world = build_world()
        services = {"quest_board", "advancement", "blacksmith", "crafting"}
        event_links = {
            "iron_village": "iron_forge_yard",
            "mist_village": "mist_herb_garden",
            "star_village": "star_beacon",
            "twilight_village": "twilight_caravan_square",
        }
        for village in world.visited_villages + [
            world.locations[village_id] for village_id in event_links
        ]:
            self.assertTrue(village.has_inn)
            self.assertTrue(village.has_shop)
            self.assertTrue(village.quest_npc)
            self.assertEqual(village.services, services)
        for village_id, event_id in event_links.items():
            self.assertIn(event_id, world.locations[village_id].exits.values())
            self.assertIn(village_id, world.locations[event_id].exits.values())
            self.assertIsNotNone(world.locations[event_id].dialogue)

    def test_twilight_region_connects_to_shadow_valley_and_has_encounters(self):
        world = build_world()
        self.assertEqual(
            world.locations["shadow_valley"].exits["황혼 교역로로 향한다"],
            "twilight_road",
        )
        road = world.locations["twilight_road"]
        self.assertEqual(road.exits["황혼장터로 향한다"], "twilight_village")
        enemies = [enemy.name for factory in road.encounter_pool for enemy in factory()]
        self.assertIn("교역로 산적", enemies)
        self.assertIn("황혼 매", enemies)
        twilight = next(region for region in MAP_REGIONS if region["id"] == "twilight")
        self.assertEqual(len(twilight["locations"]), 3)

    def test_village_event_choice_unlocks_local_shop_discount(self):
        game = WebGame()
        self.assertTrue(game.configure_party(DEFAULT_PARTY_SETUP)["ok"])
        game.game_map.move_to("iron_forge_yard")
        game._enter_current_location()
        self.assertEqual(game.phase, "dialogue")
        self.assertTrue(game.advance_dialogue(0)["ok"])
        self.assertTrue(game.flags["iron_forge_aided"])
        self.assertTrue(game.advance_dialogue()["ok"])

        game.game_map.move_to("iron_village")
        game.phase = "explore"
        shop = game.state()["shop"]["shops"][0]
        self.assertEqual(shop["discount_rate"], 0.15)
        self.assertEqual(shop["items"][0]["price"], 12)

    def test_each_event_uses_an_independent_village_benefit(self):
        game = WebGame()
        self.assertTrue(game.configure_party(DEFAULT_PARTY_SETUP)["ok"])
        cases = [
            ("mist_herb_garden", "mist_garden_aided"),
            ("star_beacon", "star_beacon_aided"),
            ("twilight_caravan_square", "twilight_trade_aided"),
        ]
        for location_id, flag in cases:
            game.game_map.move_to(location_id)
            game.phase = "explore"
            game._enter_current_location()
            self.assertTrue(game.advance_dialogue(0)["ok"])
            self.assertTrue(game.flags[flag])
            self.assertTrue(game.advance_dialogue()["ok"])

    def test_twilight_npc_commission_tracks_new_enemy(self):
        flags = {}
        _, template = offer_commission(
            flags, "twilight_village", FixedChoice("twilight_bandit_patrol")
        )
        self.assertEqual(template.target_id, "교역로 산적")
        self.assertTrue(accept_commission(flags, "twilight_village"))
        self.assertEqual(record_defeats(flags, ["교역로 산적"]), [])
        self.assertEqual(record_defeats(flags, ["교역로 산적"]), ["황혼길 순찰"])
        self.assertEqual(commission_state(flags, "twilight_village")["status"], "ready")

    def test_twilight_village_is_available_to_fast_travel_after_visit(self):
        game = WebGame()
        self.assertTrue(game.configure_party(DEFAULT_PARTY_SETUP)["ok"])
        self.assertTrue(game.advance_dialogue(0)["ok"])
        self.assertTrue(game.advance_dialogue()["ok"])
        game.game_map.move_to("twilight_village")
        travel_ids = {entry["id"] for entry in game.state()["village"]["travel"]}
        self.assertIn("village", travel_ids)
        self.assertTrue(game.travel_action("village")["ok"])
        self.assertTrue(game.travel_action("twilight_village")["ok"])


if __name__ == "__main__":
    unittest.main()
