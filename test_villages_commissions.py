"""다중 마을, 방문 기반 이동, NPC 무작위 의뢰 통합 테스트."""

import tempfile
import unittest
from unittest.mock import patch

import data
from commissions import (
    accept_commission, claim_commission, commission_state, offer_commission,
    record_defeats, record_visit,
)
from models import Party
from web_app import DEFAULT_PARTY_SETUP, WebGame
from world import build_world


class FixedChoice:
    def __init__(self, commission_id):
        self.commission_id = commission_id

    def choice(self, choices):
        return next(choice for choice in choices if choice.commission_id == self.commission_id)


class VillageCommissionTests(unittest.TestCase):
    def test_new_villages_connect_to_existing_regions_and_have_distinct_services(self):
        world = build_world()
        self.assertEqual(len(world.locations), 44)
        villages = {
            location.id: location for location in world.locations.values()
            if location.is_village
        }
        self.assertEqual(
            set(villages), {
                "village", "iron_village", "mist_village", "star_village",
                "twilight_village",
            },
        )
        self.assertEqual(world.locations["mine_entrance"].exits["철광촌으로 향한다"],
                         "iron_village")
        self.assertEqual(world.locations["cave"].exits["광부들의 지름길로 철광촌에 간다"],
                         "iron_village")
        self.assertEqual(
            world.locations["moonlit_spring"].exits["물안개 등불을 따라 안개나루로 간다"],
            "mist_village",
        )
        self.assertEqual(world.locations["star_observatory"].exits["별바람 역참으로 향한다"],
                         "star_village")
        full_services = {"quest_board", "advancement", "blacksmith", "crafting"}
        self.assertTrue(all(village.services == full_services for village in villages.values()))
        self.assertTrue(all(village.has_inn and village.quest_npc
                            for village in villages.values()))

    def test_commission_counts_only_progress_after_accept_and_rotates_after_claim(self):
        flags = {}
        party = Party([data.create_warrior("의뢰인")], gold=10)
        inventory = []
        offer_commission(flags, "village", FixedChoice("forest_slime_cleanup"))
        record_defeats(flags, ["슬라임"])
        self.assertEqual(commission_state(flags, "village")["progress"], 0)
        self.assertTrue(accept_commission(flags, "village"))
        self.assertEqual(record_defeats(flags, ["슬라임"]), [])
        self.assertEqual(record_defeats(flags, ["슬라임"]), ["숲길 점액 청소"])
        ready = commission_state(flags, "village")
        self.assertEqual((ready["status"], ready["progress"]), ("ready", 2))

        completed = claim_commission(flags, "village", party, inventory)
        self.assertEqual(completed.commission_id, "forest_slime_cleanup")
        self.assertEqual(party.gold, 38)
        self.assertEqual([item.name for item in inventory], ["포션"])
        self.assertIsNone(commission_state(flags, "village"))

        _, next_template = offer_commission(flags, "village", FixedChoice("forest_wolf_watch"))
        self.assertEqual(next_template.commission_id, "forest_wolf_watch")

    def test_visit_commission_requires_a_new_visit_after_accept(self):
        flags = {}
        offer_commission(flags, "iron_village", FixedChoice("mine_depth_survey"))
        record_visit(flags, "mine_depths")
        self.assertEqual(commission_state(flags, "iron_village")["progress"], 0)
        self.assertTrue(accept_commission(flags, "iron_village"))
        self.assertEqual(record_visit(flags, "mine_depths"), ["심층 갱도 측량"])
        self.assertEqual(commission_state(flags, "iron_village")["status"], "ready")

    def test_web_fast_travel_unlocks_only_after_physical_visit(self):
        game = WebGame()
        self.assertTrue(game.configure_party(DEFAULT_PARTY_SETUP)["ok"])
        game.advance_dialogue(1)
        game.advance_dialogue()
        self.assertFalse(game.travel_action("iron_village")["ok"])

        with patch("web_app.random.random", return_value=0.99):
            self.assertTrue(game.move("숲으로 향한다")["ok"])
            self.assertTrue(game.move("폐광 쪽으로 향한다")["ok"])
            self.assertTrue(game.move("철광촌으로 향한다")["ok"])
        self.assertEqual(game.game_map.current_id, "iron_village")
        self.assertIn("iron_village", game.game_map.visited)
        travel_ids = {entry["id"] for entry in game.state()["village"]["travel"]}
        self.assertEqual(travel_ids, {"village"})

        with tempfile.TemporaryDirectory() as directory:
            game.save_dir = directory
            self.assertTrue(game.save_action("save", 1)["ok"])
            game.game_map.visited.discard("iron_village")
            self.assertTrue(game.save_action("load", 1)["ok"])
            self.assertIn("iron_village", game.game_map.visited)

        self.assertFalse(game.travel_action("star_village")["ok"])
        self.assertTrue(game.travel_action("village")["ok"])
        self.assertEqual(game.game_map.current_id, "village")

    def test_web_commission_progress_reward_and_save_roundtrip(self):
        game = WebGame()
        self.assertTrue(game.configure_party(DEFAULT_PARTY_SETUP)["ok"])
        game.advance_dialogue(1)
        game.advance_dialogue()
        with patch("commissions.random.choice", side_effect=lambda choices: choices[0]):
            self.assertTrue(game.commission_action("offer")["ok"])
        self.assertEqual(game.state()["village"]["commission"]["id"],
                         "forest_slime_cleanup")
        self.assertTrue(game.commission_action("accept")["ok"])

        game._begin_battle([data.create_slime()], "random", "의뢰 저장 검증")
        with patch("web_app.random.random", return_value=0.99):
            game._victory()
        active = game.state()["village"]["commission"]
        self.assertEqual((active["status"], active["progress"]), ("active", 1))

        with tempfile.TemporaryDirectory() as directory:
            game.save_dir = directory
            self.assertTrue(game.save_action("save", 1)["ok"])
            game.flags.clear()
            self.assertTrue(game.save_action("load", 1)["ok"])
            restored = game.state()["village"]["commission"]
            self.assertEqual((restored["status"], restored["progress"]), ("active", 1))

            game._begin_battle([data.create_slime()], "random", "의뢰 완료 검증")
            with patch("web_app.random.random", return_value=0.99):
                game._victory()
            self.assertEqual(game.state()["village"]["commission"]["status"], "ready")
            before_gold = game.party.gold
            self.assertTrue(game.commission_action("claim")["ok"])
            self.assertEqual(game.party.gold, before_gold + 28)
            self.assertIsNone(game.state()["village"]["commission"])

    def test_village_service_state_matches_each_hub(self):
        game = WebGame()
        self.assertTrue(game.configure_party(DEFAULT_PARTY_SETUP)["ok"])
        game.advance_dialogue(1)
        game.advance_dialogue()

        game.game_map.move_to("iron_village")
        state = game.state()
        self.assertIsNotNone(state["shop"])
        self.assertIsNotNone(state["blacksmith"])
        self.assertIsNotNone(state["crafting"])
        self.assertTrue(state["inn"])
        self.assertTrue(state["advancement_service"])

        game.game_map.move_to("star_village")
        state = game.state()
        self.assertIsNotNone(state["blacksmith"])
        self.assertIsNotNone(state["crafting"])
        self.assertTrue(state["advancement_service"])
        self.assertTrue(state["village"]["npc"])


if __name__ == "__main__":
    unittest.main()
