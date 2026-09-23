"""Weapon combo boundaries and actual attack damage."""

import unittest
import io
from contextlib import redirect_stdout
from unittest.mock import patch

import data
from combo import ComboChain
from combat import Battle
from models import Party
from web_app import WebGame


class ComboTests(unittest.TestCase):
    def test_distinct_armed_members_chain_same_target_only(self):
        first = data.create_warrior("검객")
        second = data.create_lancer("창객")
        first.equip(data.IRON_SWORD)
        second.equip(data.GUARD_SPEAR)
        enemy = data.create_dark_knight()
        other = data.create_dark_knight()
        chain = ComboChain()

        self.assertEqual(chain.bonus(first, enemy), 0)
        chain.record(first, enemy, True)
        self.assertEqual(chain.bonus(first, enemy), 0)
        self.assertEqual(chain.bonus(second, other), 0)
        self.assertEqual(chain.bonus(second, enemy), 3)
        chain.record(second, enemy, True)
        self.assertEqual(chain.bonus(first, enemy), 4)
        chain.record(first, enemy, False)
        self.assertEqual(chain.bonus(second, enemy), 0)
        chain.record(first, enemy, True)
        self.assertEqual(chain.bonus(second, enemy, data.CURE), 0)
        self.assertEqual(chain.bonus(second, enemy, data.SPINNING_SLASH), 0)
        chain.reset()
        self.assertEqual(chain.bonus(second, enemy), 0)

    def test_web_physical_skill_uses_chain_power_without_changing_skill(self):
        game = WebGame()
        self.assertTrue(game.configure_party([
            {"name": "검객", "job": "warrior"},
            {"name": "창객", "job": "lancer"},
            {"name": "궁수", "job": "archer"},
        ])["ok"])
        first, second, _ = game.party.members
        first.equip(data.IRON_SWORD)
        second.equip(data.GUARD_SPEAR)
        enemy = data.create_dark_knight()
        enemy.hp = enemy.max_hp = 500
        game._begin_battle([enemy], "training", "연계 검증")
        game.current_actor = first
        game.combo.record(first, enemy, True)
        original_power = second.skills[0].power
        with patch("models.random.random", return_value=1):
            before = enemy.hp
            game._use_skill(second, {"skill": 0, "target": 0})
        expected = max(1, second.effective_attack + original_power + 3 - enemy.effective_defense // 2)
        self.assertEqual(before - enemy.hp, expected)
        self.assertEqual(second.skills[0].power, original_power)

    def test_console_attack_applies_chain_and_shows_bonus(self):
        first = data.create_warrior("검객")
        second = data.create_lancer("창객")
        first.equip(data.IRON_SWORD)
        second.equip(data.GUARD_SPEAR)
        enemy = data.create_dark_knight()
        enemy.hp = enemy.max_hp = 500
        battle = Battle(Party([first, second]), [enemy], [])
        battle.combo.record(first, enemy, True)
        before = enemy.hp
        output = io.StringIO()
        with patch("combat.prompt_index", side_effect=[0, 0]), \
                patch("models.random.randint", return_value=0), \
                patch("models.random.random", return_value=1), \
                redirect_stdout(output):
            battle._player_turn(second)
        expected = max(1, second.effective_attack + 3 - enemy.effective_defense // 2)
        self.assertEqual(before - enemy.hp, expected)
        self.assertIn("연계 공격! 추가 위력 +3", output.getvalue())

    def test_web_combo_increases_damage_and_resets_on_defend(self):
        game = WebGame()
        self.assertTrue(game.configure_party([
            {"name": "검객", "job": "warrior"},
            {"name": "창객", "job": "lancer"},
            {"name": "궁수", "job": "archer"},
        ])["ok"])
        first, second, _ = game.party.members
        first.equip(data.IRON_SWORD)
        second.equip(data.GUARD_SPEAR)
        enemy = data.create_dark_knight()
        enemy.hp = enemy.max_hp = 500
        game._begin_battle([enemy], "training", "연계 검증")
        game.current_actor = first
        with patch("models.random.randint", return_value=0), patch("models.random.random", return_value=1):
            before = enemy.hp
            self.assertTrue(game.act({"type": "attack", "target": 0})["ok"])
            first_damage = before - enemy.hp
            game.current_actor = second
            self.assertEqual(game.state()["combo"]["next_bonus"], 3)
            before = enemy.hp
            self.assertTrue(game.act({"type": "attack", "target": 0})["ok"])
            second_damage = before - enemy.hp
        self.assertGreater(second_damage, first_damage)
        self.assertIn("연계 공격! 추가 위력 +3", game.logs)
        game.current_actor = first
        self.assertTrue(game.act({"type": "defend"})["ok"])
        self.assertEqual(game.combo.streak, 0)


if __name__ == "__main__":
    unittest.main()
