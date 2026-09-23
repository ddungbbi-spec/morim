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
        self.assertEqual(first["target_name"], "전사")
        self.assertEqual(first["target"], "전사 (공격력 최고)")
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
        weakest = min(self.party.members, key=lambda member: member.hp)
        self.assertEqual(intent["target"], f"{weakest.name} (HP 최저)")
        self.assertEqual(intent["target_names"], [weakest.name])
        self.assertFalse(intent["phase"])

        random_intent = data.create_slime().preview_intent(self.party.members)
        self.assertFalse(random_intent["known"])
        self.assertEqual(random_intent["action"], "불규칙 행동")
        self.assertEqual(random_intent["target_type"], "unknown")
        self.assertEqual(random_intent["target_names"], [])

    def test_preview_exposes_exact_single_and_aoe_targets(self):
        warrior, mage, healer = self.party.members
        warrior.hp, mage.hp, healer.hp = 30, 7, 20
        warrior.attack, mage.attack, healer.attack = 8, 25, 6

        enemy = data.create_dark_knight()
        enemy.action_count = 2
        basic = enemy.preview_intent(self.party.members)
        self.assertEqual(basic["target_type"], "single")
        self.assertEqual(basic["target_name"], mage.name)
        self.assertEqual(basic["target_names"], [mage.name])

        enemy.action_count = 0
        debuff = enemy.preview_intent(self.party.members)
        self.assertEqual(debuff["target_name"], mage.name)
        self.assertIn("공격력 최고", debuff["target"])

        queen = data.create_mist_queen()
        queen.action_count = 1
        aoe = queen.preview_intent(self.party.members)
        self.assertEqual(aoe["target_type"], "all")
        self.assertEqual(aoe["target"], "파티 전체")
        self.assertEqual(aoe["target_names"], [warrior.name, mage.name, healer.name])

    def test_self_buff_does_not_expose_party_target(self):
        enemy = data.create_dark_knight()
        enemy.hp = enemy.effective_max_hp // 2
        intent = enemy.preview_intent(self.party.members)
        self.assertEqual(intent["target_type"], "self")
        self.assertEqual(intent["target_name"], enemy.name)
        self.assertNotIn(intent["target_name"], [member.name for member in self.party.members])

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

    def test_web_state_marks_single_and_aoe_threats_on_party(self):
        game = WebGame()
        self.assertTrue(game.configure_party(DEFAULT_PARTY_SETUP)["ok"])
        for member, hp in zip(game.party.members, (35, 6, 24)):
            member.hp = hp
        enemy = data.create_dark_knight()
        enemy.action_count = 2
        game._begin_battle([enemy], "boss", "표적 표시 검증")

        state = game.state()
        targeted = next(member for member in state["party"] if member["name"] == "리제")
        self.assertEqual(targeted["targeted_by"][0]["enemy"], enemy.name)
        self.assertEqual(targeted["targeted_by"][0]["action"], "기본 공격")
        self.assertFalse(targeted["targeted_by"][0]["aoe"])
        self.assertTrue(all(
            not member["targeted_by"] for member in state["party"] if member["name"] != "리제"
        ))

        queen = data.create_mist_queen()
        queen.action_count = 1
        queen.speed = 0
        game._begin_battle([queen], "boss", "광역 표시 검증")
        state = game.state()
        self.assertTrue(all(member["targeted_by"] for member in state["party"]))
        self.assertTrue(all(member["targeted_by"][0]["aoe"] for member in state["party"]))


if __name__ == "__main__":
    unittest.main()
