"""Enemy intent previews must be useful without mutating AI state."""

import io
import unittest
from contextlib import redirect_stdout

import data
from combat import Battle
from models import Party
from web_app import DEFAULT_PARTY_SETUP, WebGame


class EnemyIntentTests(unittest.TestCase):
    def setUp(self):
        self.party = Party([
            data.create_warrior("전사"), data.create_mage("마법사"),
            data.create_healer("힐러"),
        ])

    def test_pattern_preview_does_not_advance_ai(self):
        enemy = data.create_dark_knight()
        before = (enemy.action_count, set(enemy.triggered_phase_indices))
        first = enemy.preview_intent(self.party.members)
        second = enemy.preview_intent(self.party.members)
        self.assertEqual(first, second)
        self.assertEqual(first["action"], "위협의 포효")
        self.assertEqual(first["target"], "공격력이 가장 높은 파티원")
        self.assertEqual((enemy.action_count, enemy.triggered_phase_indices), before)

        skill, _ = enemy.choose_action(self.party.members)
        self.assertEqual(skill.name, "위협의 포효")
        self.assertEqual(enemy.action_count, 1)
        self.assertEqual(enemy.preview_intent(self.party.members)["action"], "다크볼트")

    def test_phase_preview_overrides_pattern_without_triggering_it(self):
        enemy = data.create_dark_knight()
        enemy.hp = enemy.effective_max_hp // 2
        intent = enemy.preview_intent(self.party.members)
        self.assertEqual(intent["action"], "암흑 폭주")
        self.assertEqual(intent["target"], "자신")
        self.assertTrue(intent["phase"])
        self.assertEqual(enemy.triggered_phase_indices, set())
        skill, target = enemy.choose_action(self.party.members)
        self.assertEqual(skill.name, "암흑 폭주")
        self.assertIs(target, enemy)
        self.assertEqual(enemy.triggered_phase_indices, {0})

    def test_mp_shortage_and_random_monster_intents(self):
        enemy = data.create_dark_knight()
        enemy.action_count = 1
        enemy.mp = 0
        intent = enemy.preview_intent(self.party.members)
        self.assertEqual(intent["action"], "기본 공격")
        self.assertEqual(intent["target"], "HP가 가장 낮은 파티원")
        self.assertFalse(intent["phase"])

        random_intent = data.create_slime().preview_intent(self.party.members)
        self.assertFalse(random_intent["known"])
        self.assertEqual(random_intent["action"], "불규칙 행동")

    def test_console_status_prints_intent(self):
        battle = Battle(self.party, [data.create_dark_knight()], [])
        output = io.StringIO()
        with redirect_stdout(output):
            battle._print_battle_status()
        text = output.getvalue()
        self.assertIn("[적 행동 예고]", text)
        self.assertIn("다크 나이트: 위협의 포효", text)

    def test_web_state_exposes_and_advances_boss_intent(self):
        game = WebGame()
        self.assertTrue(game.configure_party(DEFAULT_PARTY_SETUP)["ok"])
        enemy = data.create_dark_knight()
        game._begin_battle([enemy], "boss", "행동 예고 검증")
        state = game.state()
        self.assertEqual(state["enemies"][0]["intent"]["action"], "위협의 포효")
        game._enemy_action(enemy)
        self.assertEqual(game.state()["enemies"][0]["intent"]["action"], "다크볼트")


if __name__ == "__main__":
    unittest.main()
