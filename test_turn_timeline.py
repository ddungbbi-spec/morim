"""Current-round and next-round speed timeline behavior."""

import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

import data
from combat import Battle
from models import Party, StatusEffect
from web_app import DEFAULT_PARTY_SETUP, WebGame


class TurnTimelineTests(unittest.TestCase):
    def build_web_battle(self):
        game = WebGame()
        self.assertTrue(game.configure_party(DEFAULT_PARTY_SETUP)["ok"])
        for member, speed in zip(game.party.members, (10, 8, 6)):
            member.speed = speed
        fast_enemy = data.create_slime()
        slow_enemy = data.create_wild_wolf()
        fast_enemy.speed = 9
        slow_enemy.speed = 7
        game._begin_battle([fast_enemy, slow_enemy], "training", "순서 검증")
        return game, fast_enemy, slow_enemy

    def test_current_round_tracks_only_remaining_actors(self):
        game, fast_enemy, slow_enemy = self.build_web_battle()
        state = game.state()["turn_timeline"]
        self.assertEqual(
            [entry["name"] for entry in state["current_round"]],
            ["레온", fast_enemy.name, "리제", slow_enemy.name, "셀린"],
        )
        self.assertTrue(state["current_round"][0]["current"])
        self.assertEqual([entry["speed"] for entry in state["current_round"]], [10, 9, 8, 7, 6])
        self.assertEqual(state["current_round"][1]["side"], "enemy")
        self.assertEqual(state["current_round"][1]["intent"], "불규칙 행동")

        with patch("models.random.random", return_value=1), patch("models.random.randint", return_value=0):
            self.assertTrue(game.act({"type": "defend"})["ok"])
        remaining = game.state()["turn_timeline"]["current_round"]
        self.assertEqual([entry["name"] for entry in remaining], ["리제", slow_enemy.name, "셀린"])
        self.assertNotIn(fast_enemy.name, [entry["name"] for entry in remaining])

    def test_next_round_forecast_uses_live_speed_but_does_not_reorder_current_round(self):
        game, fast_enemy, _ = self.build_web_battle()
        current = game.current_actor
        current.apply_status(StatusEffect(
            kind="debuff_speed", name="둔화", remaining_turns=3, speed_mod=-6,
        ))
        timeline = game.state()["turn_timeline"]
        self.assertEqual(timeline["current_round"][0]["name"], current.name)
        self.assertEqual(timeline["next_round"][-1]["name"], current.name)
        self.assertEqual(timeline["next_round"][-1]["speed"], 4)

        fast_enemy.hp = 0
        timeline = game.state()["turn_timeline"]
        self.assertNotIn(fast_enemy.name, [entry["name"] for entry in timeline["current_round"]])
        self.assertNotIn(fast_enemy.name, [entry["name"] for entry in timeline["next_round"]])

    def test_non_battle_timeline_is_empty(self):
        game = WebGame()
        self.assertTrue(game.configure_party(DEFAULT_PARTY_SETUP)["ok"])
        self.assertEqual(game.state()["turn_timeline"], {"current_round": [], "next_round": []})

    def test_console_prints_speed_order(self):
        fast = data.create_archer("빠름")
        slow = data.create_warrior("느림")
        enemy = data.create_slime()
        fast.speed, enemy.speed, slow.speed = 10, 7, 4
        battle = Battle(Party([slow, fast]), [enemy], [])
        output = io.StringIO()
        with redirect_stdout(output):
            battle._print_turn_order(battle._turn_order())
        text = output.getvalue()
        self.assertLess(text.index("빠름"), text.index(enemy.name))
        self.assertLess(text.index(enemy.name), text.index("느림"))
        self.assertIn("속도 10", text)


if __name__ == "__main__":
    unittest.main()
