"""웹 자동 전투의 상황 판단과 연속 진행 테스트."""

import unittest
from pathlib import Path
from unittest.mock import patch

import data
from models import Party
from web_app import DEFAULT_PARTY_SETUP, WEB_ROOT, WebGame


class AutoBattleTests(unittest.TestCase):
    def setUp(self):
        self.game = WebGame()
        self.assertTrue(self.game.configure_party(DEFAULT_PARTY_SETUP)["ok"])

    def test_auto_action_rejects_non_battle_phase(self):
        self.assertFalse(self.game.auto_action()["ok"])

    def test_web_assets_expose_auto_toggle_and_three_speed_steps(self):
        script = Path(WEB_ROOT, "app.js").read_text(encoding="utf-8")
        styles = Path(WEB_ROOT, "styles.css").read_text(encoding="utf-8")
        self.assertIn('request("/api/auto", {strategy: autoBattleStrategy})', script)
        self.assertIn("const AUTO_BATTLE_DELAYS = {1: 900, 2: 450, 3: 300}", script)
        self.assertIn("undefined-legend-auto-strategy", script)
        self.assertIn("공세", script)
        self.assertIn("안정", script)
        self.assertIn("자동 전투 시작", script)
        self.assertIn(".auto-battle-controls", styles)
        self.assertIn(".strategy-button", styles)

    def test_auto_strategy_rejects_unknown_value_without_spending_turn(self):
        self.game._begin_battle([data.create_slime()], "training", "전술 검증")
        actor = self.game.current_actor

        result = self.game.auto_action("reckless")

        self.assertFalse(result["ok"])
        self.assertIs(self.game.current_actor, actor)
        self.assertIn("지원하지 않는", result["error"])
        self.assertFalse(self.game.auto_action({"mode": "aggressive"})["ok"])

    def test_survival_strategy_defends_earlier_than_balanced(self):
        warrior = data.create_warrior("수호 전사")
        warrior.speed = 99
        warrior.hp = max(1, int(warrior.effective_max_hp * 0.35))
        self.game.party = Party([warrior])
        self.game._begin_battle([data.create_slime()], "training", "안정 전술")

        balanced, _ = self.game._choose_auto_action("balanced")
        survival, description = self.game._choose_auto_action("survival")

        self.assertNotEqual(balanced["type"], "defend")
        self.assertEqual(survival, {"type": "defend"})
        self.assertIn("방어", description)

    def test_aggressive_strategy_delays_healing(self):
        healer = data.create_healer("공세 치유자")
        warrior = data.create_warrior("부상자")
        healer.speed = 99
        warrior.hp = max(1, int(warrior.effective_max_hp * 0.40))
        self.game.party = Party([healer, warrior])
        self.game._begin_battle([data.create_slime()], "training", "공세 전술")

        balanced, balanced_description = self.game._choose_auto_action("balanced")
        aggressive, aggressive_description = self.game._choose_auto_action("aggressive")

        self.assertEqual(balanced["type"], "skill")
        self.assertIn("회복", balanced_description)
        self.assertNotIn("회복", aggressive_description)
        self.assertNotEqual(aggressive, balanced)

    def test_auto_action_log_includes_selected_strategy(self):
        self.game._begin_battle([data.create_slime()], "training", "전술 로그")

        result = self.game.auto_action("aggressive")

        self.assertTrue(result["ok"])
        self.assertTrue(any("자동 전투[공세]" in line for line in self.game.logs))

    def test_auto_action_heals_most_wounded_ally(self):
        healer = data.create_healer("치유자")
        warrior = data.create_warrior("부상자")
        healer.speed = 99
        warrior.hp = 5
        self.game.party = Party([healer, warrior])
        self.game._begin_battle([data.create_slime()], "training", "자동 회복")

        before = warrior.hp
        result = self.game.auto_action()

        self.assertTrue(result["ok"])
        self.assertGreater(warrior.hp, before)
        self.assertTrue(any("큐어" in line and "회복" in line for line in self.game.logs))

    def test_auto_action_uses_aoe_against_multiple_enemies(self):
        mage = data.create_mage("광역술사")
        mage.speed = 99
        mage.skills = [data.BLIZZAGA]
        mage.max_mp = 99
        mage.mp = 99
        enemies = [data.create_slime(), data.create_wild_wolf()]
        for enemy in enemies:
            enemy.weakness = "ice"
        self.game.party = Party([mage])
        self.game._begin_battle(enemies, "training", "자동 광역기")
        before = [enemy.hp for enemy in enemies]

        with patch("models.random.random", return_value=0.99):
            result = self.game.auto_action()

        self.assertTrue(result["ok"])
        self.assertTrue(all(enemy.hp < hp for enemy, hp in zip(enemies, before)))
        self.assertTrue(any("적 전체" in line for line in self.game.logs))

    def test_auto_action_does_not_repeat_an_active_buff(self):
        warrior = data.create_warrior("강화 전사")
        warrior.speed = 99
        warrior.skills = [data.WAR_CRY]
        enemy = data.create_slime()
        enemy.speed = 1
        self.game.party = Party([warrior])
        self.game._begin_battle([enemy], "training", "자동 강화")

        self.assertTrue(self.game.auto_action()["ok"])
        self.assertTrue(warrior.has_status("buff_attack"))
        self.assertTrue(self.game.auto_action()["ok"])
        buff_choices = [
            line for line in self.game.logs
            if "자동 전투" in line and "[전투 함성] 강화" in line
        ]
        self.assertEqual(len(buff_choices), 1)

    def test_auto_battle_can_finish_a_training_encounter(self):
        self.game._begin_battle([data.create_slime()], "training", "자동 완주")
        with (
            patch("models.random.randint", return_value=0),
            patch("models.random.random", return_value=0.99),
            patch("web_app.random.random", return_value=0.99),
        ):
            for _ in range(100):
                if self.game.phase != "battle":
                    break
                result = self.game.auto_action()
                self.assertTrue(result["ok"])

        self.assertEqual(self.game.phase, "victory")
        self.assertTrue(any("자동 전투" in line for line in self.game.logs))


if __name__ == "__main__":
    unittest.main()
