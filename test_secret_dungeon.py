"""시크릿 던전 해금, 전용 콘텐츠, 보상과 저장 연동 테스트."""

import tempfile
import unittest
from unittest.mock import patch

import data
from web_app import DEFAULT_PARTY_SETUP, WebGame
from world import build_world, secret_dungeon_unlocked


class SecretDungeonTests(unittest.TestCase):
    def setUp(self):
        self.game = WebGame()
        self.assertTrue(self.game.configure_party(DEFAULT_PARTY_SETUP)["ok"])
        self.game.advance_dialogue(1)
        self.game.advance_dialogue()

    def secret_region(self):
        return next(
            region for region in self.game.state()["maps"]["world"]
            if region["id"] == "secret_grave"
        )

    def test_unlock_requires_void_victory_and_abyss_clear(self):
        label = "검은 비석의 숨은 문을 연다"
        requirement = self.game.game_map.locations["village"].flag_requirements[label]

        self.assertFalse(secret_dungeon_unlocked({}))
        self.assertFalse(requirement.is_met({"void_observer_defeated": True}))
        self.assertFalse(requirement.is_met({"dungeon_clear_count": 3}))
        self.assertTrue(requirement.is_met({
            "void_observer_defeated": True,
            "dungeon_clear_count": 1,
        }))
        self.assertTrue(secret_dungeon_unlocked({
            "void_observer_defeated": True,
            "dungeon_clear_count": 4,
        }))
        self.assertTrue(self.secret_region()["locked"])
        blocked = self.game.move(label)
        self.assertFalse(blocked["ok"])
        self.assertIn("심연 변이 던전", blocked["error"])

        self.game.flags["void_observer_defeated"] = True
        self.assertTrue(self.secret_region()["locked"])
        self.game.flags["dungeon_clear_count"] = 1
        self.assertFalse(self.secret_region()["locked"])
        with patch("web_app.random.random", return_value=0.99):
            self.assertTrue(self.game.move(label)["ok"])
        self.assertEqual(self.game.game_map.current_id, "forgotten_sword_grave")

    def test_world_contains_three_room_route_and_unique_content(self):
        world = build_world()
        self.assertEqual(len(world.locations), 44)
        self.assertEqual(
            world.locations["forgotten_sword_grave"].exits["검무덤 깊은 곳으로 내려간다"],
            "grave_depths",
        )
        self.assertEqual(
            world.locations["grave_depths"].exits["무명의 제단으로 들어간다"],
            "nameless_sanctum",
        )
        boss = world.locations["nameless_sanctum"].boss()[0]
        self.assertEqual(boss.name, "무명검귀")
        self.assertTrue(boss.smart_ai)
        self.assertEqual(boss.action_pattern[1].name, "장송검우")
        self.assertEqual(
            world.locations["nameless_sanctum"].loot_equipment,
            data.NAMELESS_SOUL_CHARM,
        )
        self.assertIn(data.NAMELESS_SOUL_CHARM.name, data.PROTECTED_EQUIPMENT_NAMES)
        self.assertIs(data.EQUIPMENT_BY_NAME[data.NAMELESS_SOUL_CHARM.name],
                      data.NAMELESS_SOUL_CHARM)

    def test_web_boss_first_clear_reward_and_save_roundtrip(self):
        self.game.flags.update({
            "void_observer_defeated": True,
            "dungeon_clear_count": 1,
        })
        with patch("web_app.random.random", return_value=0.99):
            self.assertTrue(self.game.move("검은 비석의 숨은 문을 연다")["ok"])
            self.assertTrue(self.game.move("검무덤 깊은 곳으로 내려간다")["ok"])
            self.assertTrue(self.game.move("무명의 제단으로 들어간다")["ok"])

        self.assertEqual(self.game.phase, "battle")
        self.assertEqual(self.game.enemies[0].name, "무명검귀")
        with patch("web_app.random.random", return_value=0.99):
            self.game._victory()
        self.assertTrue(self.game.flags["nameless_swordmaster_defeated"])
        self.assertTrue(self.game.game_map.current.boss_defeated)
        self.assertTrue(self.game.game_map.current.loot_claimed)
        self.assertEqual(
            sum(item.name == data.NAMELESS_SOUL_CHARM.name
                for item in self.game.equipment_inventory),
            1,
        )

        with tempfile.TemporaryDirectory() as directory:
            self.game.save_dir = directory
            self.assertTrue(self.game.save_action("save", 1)["ok"])
            self.game.flags.clear()
            self.game.game_map.current.boss_defeated = False
            self.assertTrue(self.game.save_action("load", 1)["ok"])
            self.assertTrue(self.game.flags["nameless_swordmaster_defeated"])
            self.assertTrue(self.game.game_map.locations["nameless_sanctum"].boss_defeated)
            self.assertEqual(
                sum(item.name == data.NAMELESS_SOUL_CHARM.name
                    for item in self.game.equipment_inventory),
                1,
            )


if __name__ == "__main__":
    unittest.main()
