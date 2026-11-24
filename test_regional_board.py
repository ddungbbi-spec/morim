"""지역 게시판의 진행·저장·보상 중복 방지와 웹 전투/이동 연동 검증."""

import tempfile
import json
import threading
import unittest
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from http.server import ThreadingHTTPServer
from unittest.mock import patch

import data
from commissions import (
    COMMISSION_TEMPLATES, REGIONAL_BOARD_IDS, accept_commission,
    accept_regional_commission, claim_regional_commission, commission_state,
    offer_commission, record_defeats, record_visit, regional_board_state,
    run_regional_board,
)
from models import Party
from reputation import reputation_state
from web_app import DEFAULT_PARTY_SETUP, GameHandler, WebGame
from world import build_world


class RegionalBoardTests(unittest.TestCase):
    def new_game(self):
        game = WebGame()
        self.assertTrue(game.configure_party(DEFAULT_PARTY_SETUP)["ok"])
        game.advance_dialogue(1)
        game.advance_dialogue()
        return game

    def test_every_village_has_three_completable_one_time_commissions(self):
        world = build_world()
        villages = {loc.id for loc in world.locations.values() if loc.is_village}
        self.assertEqual(set(REGIONAL_BOARD_IDS), villages)
        self.assertEqual(len(regional_board_state({})), 15)
        for village_id, ids in REGIONAL_BOARD_IDS.items():
            self.assertEqual(len(ids), 3)
            for cid in ids:
                with self.subTest(commission=cid):
                    flags, inventory = {}, []
                    party = Party([data.create_warrior("검증")], gold=0)
                    template = COMMISSION_TEMPLATES[cid]
                    if template.target_type == "visit":
                        self.assertIn(template.target_id, world.locations)
                    self.assertIsNone(claim_regional_commission(flags, village_id, cid, party, inventory))
                    self.assertTrue(accept_regional_commission(flags, village_id, cid))
                    self.assertFalse(accept_regional_commission(flags, village_id, cid))
                    if template.target_type == "visit":
                        record_visit(flags, template.target_id)
                    else:
                        record_defeats(flags, [template.target_id] * (template.required + 2))
                    entry = next(e for e in regional_board_state(flags, village_id) if e["id"] == cid)
                    self.assertEqual((entry["status"], entry["progress"]), ("ready", template.required))
                    self.assertIsNotNone(claim_regional_commission(flags, village_id, cid, party, inventory))
                    self.assertIsNone(claim_regional_commission(flags, village_id, cid, party, inventory))
                    self.assertFalse(accept_regional_commission(flags, village_id, cid))
                    self.assertEqual(party.gold, template.gold_reward)
                    self.assertEqual([item.name for item in inventory],
                                     [name for name, count in template.item_rewards for _ in range(count)])
                    self.assertEqual(reputation_state(flags, village_id)["score"], 1)

    def test_only_post_accept_progress_and_multiple_regions(self):
        flags = {}
        record_defeats(flags, ["슬라임"] * 3)
        record_visit(flags, "cave")
        for village_id, cid in [("village", "forest_slime_cleanup"),
                                ("village", "cave_patrol"), ("iron_village", "miner_remains")]:
            self.assertTrue(accept_regional_commission(flags, village_id, cid))
        self.assertTrue(all(e["progress"] == 0 for e in regional_board_state(flags)))
        record_defeats(flags, ["슬라임", "야생 늑대", "스켈레톤 광부"])
        record_visit(flags, "mine_entrance")
        entries = {e["id"]: e for e in regional_board_state(flags)}
        self.assertEqual(entries["forest_slime_cleanup"]["progress"], 1)
        self.assertEqual(entries["miner_remains"]["progress"], 1)
        self.assertEqual(entries["cave_patrol"]["progress"], 0)

    def test_legacy_random_commission_is_preserved(self):
        flags = {}
        with patch("commissions.random.choice", side_effect=lambda choices: choices[0]):
            offer_commission(flags, "village")
        accept_commission(flags, "village")
        accept_regional_commission(flags, "village", "forest_slime_cleanup")
        record_defeats(flags, ["슬라임", "슬라임"])
        self.assertEqual(commission_state(flags, "village")["status"], "ready")
        self.assertEqual(regional_board_state(flags, "village")[0]["status"], "ready")

    def test_web_save_roundtrip_partial_ready_and_claimed(self):
        game = self.new_game()
        cid = "forest_slime_cleanup"
        self.assertTrue(game.regional_commission_action("accept", cid)["ok"])
        game._begin_battle([data.create_slime()], "random", "게시판 검증")
        with patch("web_app.random.random", return_value=0.99):
            game._victory()
            game._victory()  # 한 전투의 처치를 중복 반영하지 않는다.
        self.assertEqual(game.state()["tracked_commissions"][0]["progress"], 1)
        with tempfile.TemporaryDirectory() as directory:
            game.save_dir = directory
            for status, progress in [("active", 1), ("ready", 2), ("completed", 2)]:
                with self.subTest(status=status):
                    self.assertTrue(game.save_action("save", 1)["ok"])
                    game.flags = {}
                    self.assertTrue(game.save_action("load", 1)["ok"])
                    entry = game.state()["regional_commissions"][0]
                    self.assertEqual((entry["status"], entry["progress"]), (status, progress))
                    if status == "active":
                        game._begin_battle([data.create_slime()], "random", "게시판 완료")
                        with patch("web_app.random.random", return_value=0.99):
                            game._victory()
                    elif status == "ready":
                        before_gold = game.party.gold
                        before_items = len(game.inventory)
                        self.assertTrue(game.regional_commission_action("claim", cid)["ok"])
                        self.assertEqual(game.party.gold, before_gold + 28)
                        self.assertEqual(len(game.inventory), before_items + 1)
                    else:
                        before = (game.party.gold, len(game.inventory))
                        self.assertFalse(game.regional_commission_action("claim", cid)["ok"])
                        self.assertEqual((game.party.gold, len(game.inventory)), before)
                        self.assertEqual(game.state()["tracked_commissions"], [])

    def test_web_visit_and_location_phase_and_id_guards(self):
        game = self.new_game()
        for operation, cid in [("accept", "miner_remains"), ("accept", "unknown"),
                               ("accept", []), ("claim", "cave_patrol"), ("reset", "cave_patrol")]:
            self.assertFalse(game.regional_commission_action(operation, cid)["ok"])
        self.assertTrue(game.regional_commission_action("accept", "cave_patrol")["ok"])
        with patch("web_app.random.random", return_value=0.99):
            self.assertTrue(game.move("숲으로 향한다")["ok"])
            self.assertFalse(game.regional_commission_action("accept", "forest_wolf_watch")["ok"])
            self.assertTrue(game.move("동굴 쪽으로 향한다")["ok"])
        self.assertEqual(game.state()["tracked_commissions"][0]["status"], "ready")
        self.assertFalse(game.regional_commission_action("claim", "cave_patrol")["ok"])
        game.game_map.move_to("iron_village")
        self.assertFalse(game.regional_commission_action("claim", "cave_patrol")["ok"])
        game.game_map.move_to("village")
        game.phase = "battle"
        self.assertFalse(game.regional_commission_action("claim", "cave_patrol")["ok"])
        game.phase = "explore"
        self.assertTrue(game.regional_commission_action("claim", "cave_patrol")["ok"])

    def test_console_accept_and_claim(self):
        flags, inventory = {}, []
        party = Party([data.create_warrior("검증")], gold=0)
        with patch("builtins.input", side_effect=["3", "y", "4"]):
            run_regional_board(flags, "village", party, inventory)
        record_visit(flags, "cave")
        with patch("builtins.input", side_effect=["3", "y", "4"]):
            run_regional_board(flags, "village", party, inventory)
        self.assertEqual(party.gold, 25)
        self.assertEqual(regional_board_state(flags, "village")[2]["status"], "completed")

    def test_http_simultaneous_claims_pay_only_once(self):
        game = self.new_game()
        cid = "cave_patrol"
        with patch("web_app.GAME", game), patch("web_app.GAME_LOCK", threading.Lock()), \
             patch.object(GameHandler, "multi_session_enabled", False):
            server = ThreadingHTTPServer(("127.0.0.1", 0), GameHandler)
            worker = threading.Thread(target=server.serve_forever, daemon=True)
            worker.start()
            def post(operation):
                request = urllib.request.Request(
                    f"http://127.0.0.1:{server.server_port}/api/regional-commission",
                    data=json.dumps({"operation": operation, "commission": cid}).encode(),
                    headers={"Content-Type": "application/json"},
                )
                try:
                    with urllib.request.urlopen(request, timeout=2) as response:
                        return json.load(response)
                except urllib.error.HTTPError as response:
                    return json.load(response)
            try:
                self.assertTrue(post("accept")["ok"])
                record_visit(game.flags, "cave")
                before_gold, before_items = game.party.gold, len(game.inventory)
                with ThreadPoolExecutor(max_workers=2) as pool:
                    results = list(pool.map(post, ["claim", "claim"]))
                self.assertEqual(sum(result["ok"] for result in results), 1)
                self.assertEqual(game.party.gold, before_gold + 25)
                self.assertEqual(len(game.inventory), before_items + 1)
            finally:
                server.shutdown()
                server.server_close()
                worker.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
