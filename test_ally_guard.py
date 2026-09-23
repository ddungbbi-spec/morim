"""One-hit ally guard action and enemy attack redirection."""

import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

import data
from combat import Battle
from models import Party
from protection import AllyProtection
from web_app import WebGame


PARTY_SETUP = [
    {"name": "수호", "job": "warrior"},
    {"name": "술사", "job": "mage"},
    {"name": "치유", "job": "healer"},
]


class AllyGuardTests(unittest.TestCase):
    def test_links_reject_self_replace_old_target_and_expire(self):
        protector = data.create_warrior("수호")
        first = data.create_mage("첫 대상")
        second = data.create_healer("둘째 대상")
        links = AllyProtection()
        with self.assertRaises(ValueError):
            links.protect(protector, protector)
        links.protect(protector, first)
        self.assertIs(links.protector_for(first), protector)
        links.protect(protector, second)
        self.assertIsNone(links.protector_for(first))
        self.assertIs(links.protector_for(second), protector)
        links.clear_protector(protector)
        self.assertIsNone(links.protector_for(second))

    def test_only_single_target_attacks_consume_guard(self):
        protector = data.create_warrior("수호")
        target = data.create_mage("대상")
        links = AllyProtection()
        links.protect(protector, target)
        actual, message = links.redirect(target, data.CHAOS_WAVE)
        self.assertIs(actual, target)
        self.assertEqual(message, "")
        self.assertIs(links.protector_for(target), protector)
        actual, message = links.redirect(target, data.WEAKEN)
        self.assertIs(actual, target)
        self.assertEqual(message, "")
        self.assertIs(links.protector_for(target), protector)
        actual, message = links.redirect(target, data.DARK_BOLT)
        self.assertIs(actual, protector)
        self.assertIn("공격을 대신", message)
        self.assertIsNone(links.protector_for(target))

    def build_game(self):
        game = WebGame()
        self.assertTrue(game.configure_party(PARTY_SETUP)["ok"])
        for member, speed in zip(game.party.members, (10, 8, 6)):
            member.speed = speed
        enemy = data.create_dark_knight()
        enemy.speed = 4
        game._begin_battle([enemy], "boss", "엄호 검증")
        return game, enemy

    def test_web_action_rejects_self_without_consuming_turn(self):
        game, _ = self.build_game()
        actor = game.current_actor
        result = game.act({"type": "protect", "target": 0})
        self.assertFalse(result["ok"])
        self.assertIs(game.current_actor, actor)
        self.assertFalse(actor.guarding)

    def test_web_guard_redirects_once_and_halves_damage(self):
        game, enemy = self.build_game()
        protector, target, _ = game.party.members
        self.assertTrue(game.act({"type": "protect", "target": 1})["ok"])
        self.assertTrue(protector.guarding)
        self.assertEqual(game.state()["party"][1]["guarded_by"], protector.name)
        target_before, protector_before = target.hp, protector.hp
        with patch.object(enemy, "choose_action", return_value=(None, target)), \
                patch("models.random.randint", return_value=0), \
                patch("models.random.random", return_value=1):
            game._enemy_action(enemy)
        raw = max(1, enemy.effective_attack - protector.effective_defense // 2)
        self.assertEqual(target.hp, target_before)
        self.assertEqual(protector_before - protector.hp, max(1, (raw + 1) // 2))
        self.assertEqual(game.state()["party"][1]["guarded_by"], "")
        self.assertIn("엄호해 공격을 대신", " ".join(game.logs))

    def test_web_aoe_does_not_consume_guard(self):
        game, enemy = self.build_game()
        protector, target, _ = game.party.members
        game.protection.protect(protector, target)
        protector.guarding = True
        with patch.object(enemy, "choose_action", return_value=(data.CHAOS_WAVE, target)), \
                patch("models.random.random", return_value=1):
            game._enemy_action(enemy)
        self.assertIs(game.protection.protector_for(target), protector)
        self.assertLess(target.hp, target.effective_max_hp)

    def test_web_single_target_attack_skill_is_redirected(self):
        game, enemy = self.build_game()
        protector, target, _ = game.party.members
        game.protection.protect(protector, target)
        protector.guarding = True
        target_before, protector_before = target.hp, protector.hp
        with patch.object(enemy, "choose_action", return_value=(data.DARK_BOLT, target)), \
                patch("models.random.random", return_value=1):
            game._enemy_action(enemy)
        self.assertEqual(target.hp, target_before)
        self.assertLess(protector.hp, protector_before)
        self.assertIsNone(game.protection.protector_for(target))

    def test_console_enemy_attack_uses_guard(self):
        protector = data.create_warrior("수호")
        target = data.create_mage("대상")
        enemy = data.create_dark_knight()
        battle = Battle(Party([protector, target]), [enemy], [])
        battle.protection.protect(protector, target)
        protector.guarding = True
        output = io.StringIO()
        with patch.object(enemy, "choose_action", return_value=(None, target)), \
                patch("models.random.randint", return_value=0), \
                patch("models.random.random", return_value=1), \
                redirect_stdout(output):
            battle._enemy_turn(enemy)
        self.assertEqual(target.hp, target.effective_max_hp)
        self.assertLess(protector.hp, protector.effective_max_hp)
        self.assertIn("엄호해 공격을 대신", output.getvalue())


if __name__ == "__main__":
    unittest.main()
