"""Weapon combo boundaries and actual attack damage."""

import unittest
import io
from contextlib import redirect_stdout
from unittest.mock import patch

import data
from combo import ComboChain, COMBO_FINISHERS
from combat import Battle
from models import Party
from web_app import WebGame


class ComboTests(unittest.TestCase):
    def test_third_hit_finishers_match_weapon_identity(self):
        setup = [
            (data.IRON_SWORD, "debuff_defense", -2, 0),
            (data.IRON_DAGGER, "poison", 0, 3),
            (data.GUARD_SPEAR, "debuff_defense", -4, 0),
            (data.HUNTER_BOW, "debuff_speed", -3, 0),
            (data.BATTLE_AXE, "debuff_attack", -3, 0),
            (data.IRON_GAUNTLET, "paralysis", 0, 0),
        ]
        starter = data.create_warrior("선봉")
        starter.equip(data.IRON_SWORD)
        middle = data.create_archer("중진")
        middle.equip(data.HUNTER_BOW)
        for weapon, kind, modifier, poison_power in setup:
            with self.subTest(family=weapon.weapon_family):
                finisher = data.create_warrior("마무리")
                finisher.equipment["weapon"] = weapon
                enemy = data.create_dark_knight()
                chain = ComboChain()
                chain.record(starter, enemy, True)
                chain.record(middle, enemy, True)
                self.assertEqual(
                    chain.finisher_name(finisher, enemy),
                    COMBO_FINISHERS[weapon.weapon_family][0],
                )
                message = chain.apply_finisher(finisher, enemy, True)
                effect = enemy.status_effects[0]
                self.assertIn(effect.name, message)
                self.assertEqual(effect.kind, kind)
                self.assertEqual(effect.power, poison_power)
                self.assertIn(modifier, (effect.attack_mod, effect.defense_mod, effect.speed_mod))

    def test_finisher_requires_landing_and_living_target(self):
        first = data.create_warrior("첫째")
        second = data.create_archer("둘째")
        third = data.create_lancer("셋째")
        first.equip(data.IRON_SWORD)
        second.equip(data.HUNTER_BOW)
        third.equip(data.GUARD_SPEAR)
        for landed, alive in ((False, True), (True, False)):
            enemy = data.create_dark_knight()
            enemy.hp = 1 if alive else 0
            chain = ComboChain()
            chain.record(first, enemy, True)
            chain.record(second, enemy, True)
            self.assertEqual(chain.apply_finisher(third, enemy, landed), "")
            self.assertEqual(enemy.status_effects, [])

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

    def test_web_third_hit_exposes_and_applies_finisher(self):
        game = WebGame()
        self.assertTrue(game.configure_party([
            {"name": "검객", "job": "warrior"},
            {"name": "궁수", "job": "archer"},
            {"name": "창객", "job": "lancer"},
        ])["ok"])
        first, second, third = game.party.members
        first.equip(data.IRON_SWORD)
        second.equip(data.HUNTER_BOW)
        third.equip(data.GUARD_SPEAR)
        enemy = data.create_dark_knight()
        enemy.hp = enemy.max_hp = 500
        game._begin_battle([enemy], "training", "마무리 검증")
        game.combo.record(first, enemy, True)
        game.combo.record(second, enemy, True)
        game.current_actor = third
        self.assertEqual(game.state()["combo"]["finisher"], "파갑 관통")
        with patch("models.random.randint", return_value=0), patch("models.random.random", return_value=1):
            self.assertTrue(game.act({"type": "attack", "target": 0})["ok"])
        self.assertTrue(enemy.has_status("debuff_defense"))
        self.assertIn("3타 연계 마무리 [파갑 관통]!", " ".join(game.logs))


if __name__ == "__main__":
    unittest.main()
