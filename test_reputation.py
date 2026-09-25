"""마을별 평판 획득, 등급 할인, 저장 호환 통합 테스트."""

import tempfile
import unittest

import data
from commissions import accept_commission, claim_commission, offer_commission, record_defeats
from models import Party
from quests import QuestLog
from reputation import add_reputation, reputation_state
from web_app import DEFAULT_PARTY_SETUP, WebGame
from world import build_world


class FixedChoice:
    def __init__(self, commission_id):
        self.commission_id = commission_id

    def choice(self, choices):
        return next(choice for choice in choices if choice.commission_id == self.commission_id)


class VillageReputationTests(unittest.TestCase):
    def test_commissions_raise_only_the_origin_village_reputation(self):
        flags = {}
        party = Party([data.create_warrior("평판 시험")], gold=0)
        inventory = []
        offer_commission(flags, "village", FixedChoice("forest_slime_cleanup"))
        self.assertTrue(accept_commission(flags, "village"))
        record_defeats(flags, ["슬라임", "슬라임"])

        self.assertIsNotNone(claim_commission(flags, "village", party, inventory))
        self.assertEqual(reputation_state(flags, "village")["score"], 1)
        self.assertEqual(reputation_state(flags, "iron_village")["score"], 0)

    def test_reputation_tiers_unlock_progressive_shop_discounts(self):
        flags = {}
        shop = build_world().locations["iron_village"].shops[0]
        item = data.POTION

        self.assertEqual(shop.price_for(item, flags), item.price)
        add_reputation(flags, "iron_village", 3)
        reputation = reputation_state(flags, "iron_village")
        self.assertEqual((reputation["tier"], reputation["discount_rate"]),
                         ("마을의 조력자", 0.05))
        self.assertEqual(shop.price_for(item, flags, reputation["discount_rate"]), 14)

        flags["iron_forge_aided"] = True
        self.assertEqual(shop.active_discount(flags, reputation["discount_rate"]), 0.20)
        self.assertEqual(shop.price_for(item, flags, reputation["discount_rate"]), 12)

    def test_story_choice_adds_bonus_reputation(self):
        flags = {"astral_beacon_lit": True}
        world = build_world()
        world.locations["void_throne"].boss_defeated = True
        quests = QuestLog({"beyond_stars": "active"})
        quests.refresh_from_world(world, flags)
        party = Party([data.create_warrior("별길 시험")], gold=0)

        self.assertTrue(quests.claim("beyond_stars", party, [], flags))
        self.assertEqual(reputation_state(flags, "star_village")["score"], 4)

    def test_web_shop_uses_reputation_and_save_restores_it(self):
        game = WebGame()
        self.assertTrue(game.configure_party(DEFAULT_PARTY_SETUP)["ok"])
        game.advance_dialogue(1)
        game.advance_dialogue()
        add_reputation(game.flags, "village", 6)

        state = game.state()
        self.assertEqual(state["village"]["reputation"]["tier"], "신뢰받는 해결사")
        self.assertEqual(state["shop"]["shops"][0]["items"][0]["price"], 13)

        with tempfile.TemporaryDirectory() as directory:
            game.save_dir = directory
            self.assertTrue(game.save_action("save", 1)["ok"])
            game.flags["village_reputation"] = {}
            self.assertTrue(game.save_action("load", 1)["ok"])
            restored = game.state()["village"]["reputation"]
            self.assertEqual((restored["score"], restored["discount_rate"]), (6, 0.10))


if __name__ == "__main__":
    unittest.main()
