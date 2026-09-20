"""웹 전투 시제품의 상태 전환과 기존 게임 규칙 연동 테스트."""

import unittest
import tempfile
import json
import threading
import http.cookiejar
import urllib.request
from pathlib import Path
from unittest.mock import patch

import data
from http.server import ThreadingHTTPServer
from models import StatusEffect
from web_app import DEFAULT_PARTY_SETUP, GameHandler, SessionStore, WEB_ROOT, WebGame


class WebGameTests(unittest.TestCase):
    def test_web_star_forge_gate_choice_and_atomic_failure(self):
        self.finish_intro()
        self.game.party.gold = 9999
        self.game.equipment_inventory = [data.IRON_SWORD, data.IRON_SWORD]
        self.game.inventory = [data.STAR_ORE] * 3
        self.assertFalse(self.forge(0, "star_ore")["ok"])
        self.assertEqual(len(self.game.inventory), 3)
        self.game.flags["star_rift_closed"] = True
        state = self.game.state()["blacksmith"]
        self.assertTrue(state["star_unlocked"])
        self.assertEqual(state["star_ore_count"], 3)
        self.assertTrue(state["equipment"][0]["can_star_upgrade"])
        self.assertTrue(self.forge(0, "star_ore")["ok"])
        self.assertEqual(len(self.game.equipment_inventory), 2)
        self.assertEqual(len(self.game.inventory), 2)
        self.assertTrue(self.forge(0)["ok"])
        self.assertEqual(len(self.game.equipment_inventory), 1)
        self.assertEqual(len(self.game.inventory), 2)
        before = self.game.party.gold
        self.assertFalse(self.forge(0, "star_ore")["ok"])
        self.assertEqual(self.game.party.gold, before)
        self.assertFalse(self.forge(0, ["star_ore"])["ok"])
        self.game.game_map.move_to("star_rift")
        self.assertFalse(self.forge(0, "star_ore")["ok"])

    def test_web_star_boss_material_reward_once_per_victory(self):
        self.finish_intro()
        self.game.inventory = []
        self.game.game_map.move_to("star_rift")
        self.game.game_map.current.dialogue_played = True
        self.game._begin_battle([data.create_slime()], "boss", "검증")
        with patch("web_app.random.random", return_value=0.99):
            self.game._victory()
            self.game._victory()
        self.assertEqual(sum(i.name == "성운석" for i in self.game.inventory), 3)
        self.assertTrue(self.game.boss_action("retry")["ok"])
        with patch("web_app.random.random", return_value=0.99):
            self.game._victory()
        self.assertEqual(sum(i.name == "성운석" for i in self.game.inventory), 6)
        self.assertEqual(sum(i.name == "별의 수호 부적" for i in self.game.equipment_inventory), 1)

    def test_web_post_boss_chapter_gate_choice_boss_and_reward(self):
        self.finish_intro()
        label = "북쪽 관측소로 향한다"
        self.assertFalse(self.game.move(label)["ok"])
        self.assertFalse(self.game.quest_action("accept", "fallen_star")["ok"])
        self.assertEqual(next(quest for quest in self.game.state()["quests"]
                              if quest["id"] == "fallen_star")["status"], "locked")
        self.assertTrue(next(exit for exit in self.game.state()["location"]["exits"]
                             if exit["label"] == label)["locked"])
        self.game.game_map.locations["final_chamber"].boss_defeated = True
        self.game.flags["demon_lord_defeated"] = True
        self.assertTrue(self.game.move(label)["ok"])
        self.assertEqual(self.game.phase, "dialogue")
        self.game.advance_dialogue(0)
        self.game.advance_dialogue()
        self.assertTrue(self.game.flags["star_signal_reported"])
        self.assertEqual(self.game.quest_log.status("fallen_star"), "active")
        self.assertTrue(self.game.move("낙하지로 내려간다")["ok"])
        if self.game.phase == "battle":
            with patch("web_app.random.random", return_value=0.99):
                self.game._victory()
        self.assertEqual(self.game.phase, "dialogue")
        self.game.advance_dialogue()
        self.assertTrue(self.game.move("별의 균열로 들어간다")["ok"])
        self.game.advance_dialogue()
        self.assertEqual(self.game.phase, "battle")
        self.assertEqual(self.game.enemies[0].name, "검은 별의 잔재")
        with patch("web_app.random.random", return_value=0.99):
            self.game._victory()
        self.assertTrue(self.game.flags["star_rift_closed"])
        self.assertEqual(self.game.quest_log.status("fallen_star"), "ready")
        self.assertEqual(sum(item.name == "별의 수호 부적" for item in self.game.equipment_inventory), 1)
        self.assertTrue(self.game.move("유성 낙하지로 돌아간다")["ok"])
        self.assertTrue(self.game.move("관측소로 돌아간다")["ok"])
        self.assertTrue(self.game.move("마을로 돌아간다")["ok"])
        before = self.game.party.gold
        self.assertTrue(self.game.quest_action("claim", "fallen_star")["ok"])
        self.assertEqual(self.game.party.gold, before + 110)
        self.assertFalse(self.game.quest_action("claim", "fallen_star")["ok"])

    def forge(self, index, material="duplicate"):
        return self.game.blacksmith_action(index, material,
                                          self.game._forge_quote(index, material))

    def test_forge_quote_rejects_replay_shifted_target_and_changed_resources(self):
        self.finish_intro()
        self.game.party.gold = 9999
        self.game.flags["star_rift_closed"] = True
        self.game.inventory = [data.STAR_ORE] * 10
        self.game.equipment_inventory = [data.IRON_SWORD, data.IRON_SWORD,
                                         data.LEATHER_ARMOR, data.LEATHER_ARMOR]
        quote = self.game.state()["blacksmith"]["equipment"][1]["quote"]
        self.assertTrue(self.game.blacksmith_action(1, quote=quote)["ok"])
        before = (self.game.party.gold, list(self.game.equipment_inventory))
        self.assertFalse(self.game.blacksmith_action(1, quote=quote)["ok"])
        self.assertEqual(before, (self.game.party.gold, self.game.equipment_inventory))
        quote = self.game.state()["blacksmith"]["equipment"][0]["star_quote"]
        self.assertTrue(self.game.blacksmith_action(0, "star_ore", quote)["ok"])
        before = (self.game.party.gold, list(self.game.inventory))
        self.assertFalse(self.game.blacksmith_action(0, "star_ore", quote)["ok"])
        self.assertEqual(before, (self.game.party.gold, self.game.inventory))
        quote = self.game._forge_quote(0, "star_ore")
        self.game.party.gold += 1
        self.assertFalse(self.game.blacksmith_action(0, "star_ore", quote)["ok"])
        self.assertFalse(self.game.blacksmith_action(0, "star_ore")["ok"])
        self.assertFalse(self.game.blacksmith_action(0, "star_ore", {})["ok"])
        quote = self.game._forge_quote(0, "star_ore")
        self.assertFalse(self.game.blacksmith_action(1, "star_ore", quote)["ok"])
        self.assertFalse(self.game.blacksmith_action(0, "duplicate", quote)["ok"])

    def test_equipment_state_uses_current_bonus_fields(self):
        from blacksmith import preview_upgrade
        sword = preview_upgrade(preview_upgrade(data.IRON_SWORD))
        state = self.game._equipment_state(sword)
        self.assertIn("공격력 +9", state["description"])
        self.assertNotIn("공격력 +5", state["description"])

    def test_rift_forge_equip_save_reload_and_repeat_reward(self):
        import tempfile
        self.finish_intro()
        with tempfile.TemporaryDirectory() as directory:
            self.game.save_dir = directory
            self.game.party.gold = 9999
            self.game.inventory = []
            self.game.game_map.move_to("star_rift")
            self.game.game_map.current.dialogue_played = True
            self.game._begin_battle([data.create_slime()], "boss", "통합 검증")
            with patch("web_app.random.random", return_value=0.99):
                self.game._victory()
            self.assertEqual(sum(i.name == "성운석" for i in self.game.inventory), 3)
            self.game.game_map.move_to("village")
            index = next(i for i, item in enumerate(self.game.equipment_inventory)
                         if item.name == data.STARWARD_CHARM.name)
            self.assertTrue(self.forge(index, "star_ore")["ok"])
            self.assertTrue(self.game.equipment_action("equip", 0, index)["ok"])
            gold = self.game.party.gold
            self.assertTrue(self.game.save_action("save", 1)["ok"])
            self.assertTrue(self.game.save_action("load", 1)["ok"])
            self.assertEqual(self.game.party.gold, gold)
            self.assertEqual(sum(i.name == "성운석" for i in self.game.inventory), 2)
            self.assertEqual(self.game.party.members[0].equipment["accessory"].enhancement_level, 1)
            self.assertTrue(self.game.flags["star_rift_closed"])
            self.game.game_map.move_to("star_rift")
            self.assertTrue(self.game.boss_action("retry")["ok"])
            with patch("web_app.random.random", return_value=0.99):
                self.game._victory()
                self.game._victory()
            self.assertEqual(sum(i.name == "성운석" for i in self.game.inventory), 5)
            self.assertFalse(any(i.name == data.STARWARD_CHARM.name
                                 for i in self.game.equipment_inventory))

    def setUp(self):
        self.game = WebGame()
        result = self.game.configure_party(DEFAULT_PARTY_SETUP)
        self.assertTrue(result["ok"])

    def finish_intro(self, choice=1):
        self.game.advance_dialogue(choice)
        self.game.advance_dialogue()

    def test_initial_state_and_static_assets(self):
        fresh = WebGame()
        state = fresh.state()
        self.assertEqual(state["phase"], "setup")
        self.assertEqual(state["location"]["name"], "시작 마을")
        self.assertIsNone(state["dialogue"])
        self.assertEqual(len(state["party"]), 0)
        self.assertEqual(len(state["setup"]["jobs"]), 6)
        self.assertEqual(len(state["encounters"]), 3)
        for filename in (
            "index.html", "styles.css", "app.js", "manifest.webmanifest", "sw.js",
            "icon.svg", "icon-192.png", "icon-512.png",
        ):
            self.assertTrue((Path(WEB_ROOT) / filename).is_file())
        with open(Path(WEB_ROOT) / "manifest.webmanifest", encoding="utf-8") as stream:
            manifest = json.load(stream)
        self.assertEqual(manifest["display"], "standalone")
        self.assertEqual(
            {icon["sizes"] for icon in manifest["icons"]},
            {"192x192", "512x512", "any"},
        )

    def test_boss_phase_transition_is_reported_once_per_event(self):
        self.finish_intro()
        self.game._begin_battle([data.create_dark_knight()], "boss", "다크 나이트")
        enemy = self.game.enemies[0]
        before = self.game.state()["phase_transition_id"]

        def transition(_members):
            enemy.last_phase_message = "보스가 새로운 힘을 드러낸다!"
            return None, self.game.party.alive_members[0]

        with patch.object(enemy, "choose_action", side_effect=transition):
            self.game._enemy_action(enemy)
        state = self.game.state()
        self.assertEqual(state["phase_transition_id"], before + 1)
        self.assertEqual(state["phase_transition_message"], "보스가 새로운 힘을 드러낸다!")
        self.assertIn("★ 보스가 새로운 힘을 드러낸다!", state["logs"])
        self.assertEqual(self.game.state()["phase_transition_id"], state["phase_transition_id"])

    def test_web_second_job_rules_and_state(self):
        self.finish_intro()
        member = self.game.party.members[0]
        self.assertFalse(self.game.advancement_action(0, "swordmaster")["ok"])
        member.level = 5
        self.assertEqual(len(self.game.state()["advancement"][0]["options"]), 2)
        self.assertFalse(self.game.advancement_action(0, "pyromancer")["ok"])
        self.assertFalse(self.game.advancement_action(0, {"id": "swordmaster"})["ok"])
        self.assertFalse(self.game.advancement_action(99, "swordmaster")["ok"])
        self.assertTrue(self.game.advancement_action(0, "swordmaster")["ok"])
        self.assertEqual(member.job, "검성")
        self.assertFalse(self.game.advancement_action(0, "guardian")["ok"])
        self.assertEqual(self.game.state()["advancement"][0]["options"], [])
        with patch("web_app.random.random", return_value=0.99):
            self.game.move("숲으로 향한다")
        self.assertFalse(self.game.advancement_action(1, "priest")["ok"])

    def test_health_endpoint_and_security_headers(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), GameHandler)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            with urllib.request.urlopen(
                f"http://127.0.0.1:{server.server_port}/api/health", timeout=2
            ) as response:
                payload = json.load(response)
                self.assertTrue(payload["ok"])
                self.assertEqual(payload["service"], "undefined-legend")
                self.assertEqual(response.headers["Cache-Control"], "no-store")
                self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
                self.assertEqual(response.headers["X-Frame-Options"], "DENY")
                self.assertIn("frame-ancestors 'none'", response.headers["Content-Security-Policy"])
        finally:
            server.shutdown()
            server.server_close()
            worker.join(timeout=2)

    def test_mobile_touch_and_deployment_files(self):
        project_root = Path(WEB_ROOT).parent
        for filename in (
            "Dockerfile", ".dockerignore", ".gitignore", ".python-version",
            "compose.yaml", "render.yaml", "DEPLOYMENT.md",
            ".github/workflows/tests.yml",
        ):
            self.assertTrue((project_root / filename).is_file())
        dockerfile = (project_root / "Dockerfile").read_text(encoding="utf-8")
        styles = (Path(WEB_ROOT) / "styles.css").read_text(encoding="utf-8")
        index = (Path(WEB_ROOT) / "index.html").read_text(encoding="utf-8")
        self.assertIn("USER appuser", dockerfile)
        self.assertIn("/api/health", dockerfile)
        self.assertIn("min-height: 44px", styles)
        self.assertIn("safe-area-inset-bottom", styles)
        self.assertIn("font-size: 16px", styles)
        self.assertIn("viewport-fit=cover", index)

    def test_browser_sessions_and_save_slots_are_isolated(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(
            GameHandler, "multi_session_enabled", True
        ), patch.object(GameHandler, "session_store", SessionStore(Path(directory))):
            server = ThreadingHTTPServer(("127.0.0.1", 0), GameHandler)
            worker = threading.Thread(target=server.serve_forever, daemon=True)
            worker.start()

            def client():
                jar = http.cookiejar.CookieJar()
                return urllib.request.build_opener(
                    urllib.request.HTTPCookieProcessor(jar)
                ), jar

            def api(opener, path, body=None):
                data = None if body is None else json.dumps(body).encode("utf-8")
                request = urllib.request.Request(
                    f"http://127.0.0.1:{server.server_port}{path}", data=data,
                    headers={"Content-Type": "application/json"},
                )
                with opener.open(request, timeout=2) as response:
                    return json.load(response)

            first, first_jar = client()
            second, second_jar = client()
            try:
                secure_request = urllib.request.Request(
                    f"http://127.0.0.1:{server.server_port}/api/state",
                    headers={"X-Forwarded-Proto": "https"},
                )
                with first.open(secure_request, timeout=2) as response:
                    self.assertTrue(json.load(response)["ok"])
                    set_cookie = response.headers["Set-Cookie"]
                    self.assertIn("HttpOnly", set_cookie)
                    self.assertIn("SameSite=Lax", set_cookie)
                    self.assertIn("Secure", set_cookie)
                api(second, "/api/state")
                self.assertNotEqual(
                    next(iter(first_jar)).value, next(iter(second_jar)).value
                )
                first_setup = api(first, "/api/setup", {"members": DEFAULT_PARTY_SETUP})
                second_setup = api(second, "/api/setup", {"members": [
                    {"name": "청명", "job": "rogue"},
                    {"name": "설화", "job": "archer"},
                    {"name": "무진", "job": "summoner"},
                ]})
                self.assertEqual(first_setup["state"]["party"][0]["name"], "레온")
                self.assertEqual(second_setup["state"]["party"][0]["name"], "청명")
                api(first, "/api/dialogue", {"choice": 1})
                api(first, "/api/dialogue", {})
                saved = api(first, "/api/save", {"operation": "save", "slot": 1})
                self.assertTrue(saved["state"]["save_slots"][0]["exists"])
                second_state = api(second, "/api/state")["state"]
                self.assertFalse(second_state["save_slots"][0]["exists"])
            finally:
                server.shutdown()
                server.server_close()
                worker.join(timeout=2)

    def test_custom_party_setup_supports_all_jobs_and_names(self):
        game = WebGame()
        result = game.configure_party([
            {"name": "청명", "job": "rogue"},
            {"name": "설화", "job": "archer"},
            {"name": "무진", "job": "summoner"},
        ])
        self.assertTrue(result["ok"])
        self.assertEqual([member.name for member in game.party.members], ["청명", "설화", "무진"])
        self.assertEqual([member.job for member in game.party.members], ["도적", "궁수", "소환술사"])
        self.assertEqual(game.phase, "dialogue")

    def test_party_setup_rejects_duplicate_or_invalid_data(self):
        game = WebGame()
        duplicate = game.configure_party([
            {"name": "가람", "job": "warrior"},
            {"name": "가람", "job": "mage"},
            {"name": "다온", "job": "healer"},
        ])
        self.assertFalse(duplicate["ok"])
        invalid = game.configure_party([
            {"name": "가람", "job": "unknown"},
            {"name": "나래", "job": "mage"},
            {"name": "다온", "job": "healer"},
        ])
        self.assertFalse(invalid["ok"])
        non_text = game.configure_party([
            {"name": None, "job": "warrior"},
            {"name": "나래", "job": "mage"},
            {"name": "다온", "job": "healer"},
        ])
        self.assertFalse(non_text["ok"])

    def test_dialogue_choice_updates_flags_and_main_quest(self):
        first = self.game.advance_dialogue(0)
        self.assertTrue(first["ok"])
        self.assertTrue(self.game.flags["promised_elder"])
        self.assertEqual(self.game.phase, "dialogue")

        continued = self.game.advance_dialogue()
        self.assertTrue(continued["ok"])
        self.assertEqual(self.game.phase, "explore")
        self.assertEqual(self.game.quest_log.status("ruins_darkness"), "active")

    def test_story_flag_locks_and_unlocks_elder_armory(self):
        label = "장로의 비밀 무기고로 들어간다"
        self.game.advance_dialogue(1)
        self.game.advance_dialogue()
        locked_exit = next(
            exit_data for exit_data in self.game.state()["location"]["exits"]
            if exit_data["label"] == label
        )
        self.assertTrue(locked_exit["locked"])
        self.assertEqual(locked_exit["lock_reason"], "장로의 신뢰 필요")
        blocked = self.game.move(label)
        self.assertFalse(blocked["ok"])
        self.assertEqual(self.game.game_map.current_id, "village")

        accepted = WebGame()
        accepted.configure_party(DEFAULT_PARTY_SETUP)
        accepted.advance_dialogue(0)
        accepted.advance_dialogue()
        moved = accepted.move(label)
        self.assertTrue(moved["ok"])
        self.assertEqual(accepted.game_map.current_id, "elder_armory")
        self.assertEqual(
            accepted.equipment_inventory[-1].name,
            "장로의 수호 인장",
        )

    def test_world_move_updates_location_and_visited_map(self):
        self.game.advance_dialogue(1)
        self.game.advance_dialogue()
        with patch("web_app.random.random", return_value=0.99):
            result = self.game.move("숲으로 향한다")
        self.assertTrue(result["ok"])
        self.assertEqual(self.game.game_map.current_id, "forest_entrance")
        self.assertIn("forest_entrance", self.game.game_map.visited)
        self.assertEqual(self.game.phase, "explore")

    def test_village_inn_fully_restores_party(self):
        self.finish_intro()
        for member in self.game.party.members:
            member.hp = 0
            member.mp = 0
            member.guarding = True
            member.status_effects.append(
                StatusEffect("poison", "중독", 2, power=3)
            )
        result = self.game.inn_action()
        self.assertTrue(result["ok"])
        self.assertTrue(result["state"]["inn"])
        for member in self.game.party.members:
            self.assertEqual(member.hp, member.effective_max_hp)
            self.assertEqual(member.mp, member.effective_max_mp)
            self.assertFalse(member.status_effects)
            self.assertFalse(member.guarding)

    def test_inn_is_unavailable_outside_village(self):
        self.finish_intro()
        self.game.game_map.current_id = "forest_entrance"
        result = self.game.inn_action()
        self.assertFalse(result["ok"])

    def test_village_opens_repeat_tower_and_scales_guardian(self):
        self.finish_intro()
        self.game.game_map.locations["tower_summit"].boss_defeated = True
        self.game.flags["tower_clear_count"] = 1
        result = self.game.tower_action("reset")
        self.assertTrue(result["ok"])
        self.assertEqual(result["state"]["tower"]["next_tier"], 2)
        self.assertTrue(result["state"]["tower"]["active"])
        self.assertFalse(result["state"]["tower"]["can_retry"])

        self.game.game_map.current_id = "tower_summit"
        self.game.game_map.current.dialogue_played = True
        self.game._enter_current_location()
        self.assertEqual(self.game.phase, "battle")
        self.assertIn("2단계", self.game.enemies[0].name)
        self.assertGreater(self.game.enemies[0].max_hp, data.create_tower_guardian().max_hp)

    def test_random_encounter_starts_on_world_move(self):
        self.game.advance_dialogue(1)
        self.game.advance_dialogue()
        with patch("web_app.random.random", return_value=0.0), patch(
            "web_app.random.choice", side_effect=lambda values: values[0]
        ):
            self.game.move("숲으로 향한다")
        self.assertEqual(self.game.phase, "battle")
        self.assertEqual(self.game.battle_context, "random")
        self.assertEqual(self.game.enemies[0].name, "슬라임")

    def test_locked_exit_consumes_key_and_claims_vault_loot(self):
        self.game.game_map.current_id = "cave"
        self.game.phase = "explore"
        blocked = self.game.move("굳게 닫힌 문 안으로")
        self.assertFalse(blocked["ok"])
        self.game.inventory.append(data.RUSTY_KEY)
        moved = self.game.move("굳게 닫힌 문 안으로")
        self.assertTrue(moved["ok"])
        self.assertEqual(self.game.game_map.current_id, "cave_vault")
        self.assertTrue(self.game.game_map.current.loot_claimed)
        self.assertTrue(any(item.name == "행운의 반지" for item in self.game.equipment_inventory))

    def test_world_boss_starts_after_location_dialogue(self):
        self.game.game_map.current_id = "ruins"
        self.game.phase = "explore"
        self.game._enter_current_location()
        self.assertEqual(self.game.phase, "dialogue")
        self.game.advance_dialogue()
        self.assertEqual(self.game.phase, "battle")
        self.assertEqual(self.game.battle_context, "boss")
        self.assertEqual(self.game.enemies[0].name, "다크 나이트")

    def test_world_boss_victory_unlocks_location_progress(self):
        self.game.game_map.current_id = "ruins"
        self.game.game_map.current.dialogue_played = True
        self.game.phase = "explore"
        self.game._enter_current_location()
        self.game.enemies[0].hp = 1
        with patch("models.random.randint", return_value=0), patch(
            "web_app.random.random", return_value=0.99
        ):
            while self.game.phase == "battle":
                self.game.act({"type": "attack", "target": 0})
        self.assertTrue(self.game.game_map.current.boss_defeated)
        self.assertEqual(self.game.phase, "explore")

    def test_final_boss_web_returns_to_village_with_one_time_loot_and_ending(self):
        self.game.game_map.current_id = "final_chamber"
        chamber = self.game.game_map.current
        chamber.dialogue_played = True
        self.game.game_map.locations["village"].dialogue_played = True
        self.game._begin_battle([data.create_sealed_demon_lord()], "boss", "최종 보스")
        with patch("web_app.random.random", return_value=0.99):
            self.game._victory()
        self.assertEqual(self.game.game_map.current_id, "village")
        self.assertEqual(self.game.phase, "explore")
        self.assertTrue(chamber.boss_defeated)
        self.assertTrue(chamber.loot_claimed)
        self.assertTrue(self.game.game_map.locations["ending"].dialogue_played)
        self.assertEqual(sum(item.name == data.SEALBREAKER_BLADE.name
                             for item in self.game.equipment_inventory), 1)
        self.assertIn("빛의 마법진", " ".join(self.game.logs))

        # 재도전에서도 마을로 돌아오되 엔딩과 보물은 다시 지급하지 않는다.
        self.game.game_map.current_id = "final_chamber"
        self.game._begin_battle([data.create_sealed_demon_lord()], "boss_retry", "재도전")
        with patch("web_app.random.random", return_value=0.99):
            self.game._victory()
        self.assertEqual(self.game.game_map.current_id, "village")
        self.assertEqual(sum(item.name == data.SEALBREAKER_BLADE.name
                             for item in self.game.equipment_inventory), 1)

    def test_defeated_world_boss_can_be_rechallenged_without_duplicate_treasure(self):
        self.game.game_map.current_id = "forgotten_shrine"
        location = self.game.game_map.current
        location.dialogue_played = True
        location.boss_defeated = True
        location.loot_claimed = True
        self.game.phase = "explore"
        before_cloaks = sum(
            item.name == data.MIST_CLOAK.name for item in self.game.equipment_inventory
        )

        state = self.game.state()
        self.assertTrue(state["boss_retry"]["available"])
        started = self.game.boss_action("retry")
        self.assertTrue(started["ok"])
        self.assertEqual(self.game.phase, "battle")
        self.assertEqual(self.game.battle_context, "boss_retry")
        self.assertEqual(self.game.enemies[0].name, "안개의 여왕")

        self.game.enemies[0].hp = 1
        with patch("models.random.randint", return_value=0), patch(
            "web_app.random.random", return_value=0.99
        ):
            while self.game.phase == "battle":
                self.game.act({"type": "attack", "target": 0})

        after_cloaks = sum(
            item.name == data.MIST_CLOAK.name for item in self.game.equipment_inventory
        )
        self.assertEqual(after_cloaks, before_cloaks)
        self.assertTrue(self.game.game_map.current.boss_defeated)
        self.assertTrue(self.game.state()["boss_retry"]["available"])
        self.assertIn("언제든 재도전", " ".join(self.game.logs))

    def test_boss_retry_is_rejected_before_first_clear(self):
        self.game.game_map.current_id = "ruins"
        self.game.phase = "explore"
        result = self.game.boss_action("retry")
        self.assertFalse(result["ok"])

    def test_web_shop_buy_sell_and_key_item_protection(self):
        self.finish_intro()
        shops = self.game.state()["shop"]["shops"]
        self.assertEqual(
            [shop["name"] for shop in shops],
            ["여행자 잡화점", "바람칼 무기점", "철벽 방어구점", "세아의 약초점"],
        )
        self.game.party.gold = 100
        before_count = len(self.game.inventory)
        bought = self.game.shop_action("buy_item", 0)
        self.assertTrue(bought["ok"])
        self.assertEqual(len(self.game.inventory), before_count + 1)

        self.game.inventory.append(data.RUSTY_KEY)
        sell_names = [item["name"] for item in self.game.state()["shop"]["sell_items"]]
        self.assertNotIn("녹슨 열쇠", sell_names)
        sold = self.game.shop_action("sell_item", 0)
        self.assertTrue(sold["ok"])
        self.assertIn(data.RUSTY_KEY, self.game.inventory)

        weapon = self.game.shop_action("buy_equipment", 0, shop_index=1)
        self.assertTrue(weapon["ok"])
        self.assertEqual(self.game.equipment_inventory[-1].name, "철검")

        wrong_stock = self.game.shop_action("buy_item", 0, shop_index=1)
        self.assertFalse(wrong_stock["ok"])

    def test_herbalist_shop_unlocks_and_applies_escort_discount(self):
        self.finish_intro()
        herbal_shop = self.game.state()["shop"]["shops"][3]
        self.assertFalse(herbal_shop["available"])
        blocked = self.game.shop_action("buy_item", 1, shop_index=3)
        self.assertFalse(blocked["ok"])

        self.game.flags["found_herbalist"] = True
        self.game.flags["escorted_herbalist"] = True
        self.game.party.gold = 35
        herbal_shop = self.game.state()["shop"]["shops"][3]
        tonic = herbal_shop["items"][1]
        self.assertTrue(herbal_shop["available"])
        self.assertEqual((tonic["base_price"], tonic["price"]), (35, 28))
        bought = self.game.shop_action("buy_item", 1, shop_index=3)
        self.assertTrue(bought["ok"])
        self.assertEqual(self.game.party.gold, 7)
        self.assertEqual(self.game.inventory[-1].name, "달빛 영약")

    def test_web_blacksmith_upgrades_only_in_village(self):
        self.finish_intro()
        self.game.party.gold = 500
        self.game.equipment_inventory.extend([data.IRON_SWORD, data.IRON_SWORD])
        state = self.game.state()
        self.assertTrue(state["blacksmith"]["equipment"][0]["can_upgrade"])
        self.assertIn("공격력", state["blacksmith"]["equipment"][0]["preview"])
        self.assertIn("→", state["blacksmith"]["equipment"][0]["preview"])

        result = self.forge(0)
        self.assertTrue(result["ok"])
        self.assertEqual(len(self.game.equipment_inventory), 1)
        self.assertEqual(self.game.equipment_inventory[0].enhancement_level, 1)
        self.assertIn("+1", result["state"]["equipment_inventory"][0]["display_name"])

        self.game.game_map.current_id = "forest_entrance"
        blocked = self.forge(0)
        self.assertFalse(blocked["ok"])

    def test_web_equipment_equip_swap_and_unequip(self):
        self.finish_intro()
        self.game.equipment_inventory.extend([data.IRON_SWORD, data.OAK_STAFF])
        equipped = self.game.equipment_action("equip", 0, 0)
        self.assertTrue(equipped["ok"])
        self.assertIs(self.game.party.members[0].equipment["weapon"], data.IRON_SWORD)

        swapped = self.game.equipment_action("equip", 0, 0)
        self.assertTrue(swapped["ok"])
        self.assertIs(self.game.party.members[0].equipment["weapon"], data.OAK_STAFF)
        self.assertIn(data.IRON_SWORD, self.game.equipment_inventory)

        removed = self.game.equipment_action("unequip", 0, slot="weapon")
        self.assertTrue(removed["ok"])
        self.assertIsNone(self.game.party.members[0].equipment["weapon"])

    def test_web_quest_accept_and_claim(self):
        self.finish_intro()
        accepted = self.game.quest_action("accept", "miners_rest")
        self.assertTrue(accepted["ok"])
        self.game.game_map.locations["mine_depths"].boss_defeated = True
        before_gold = self.game.party.gold
        claimed = self.game.quest_action("claim", "miners_rest")
        self.assertTrue(claimed["ok"])
        self.assertEqual(self.game.quest_log.status("miners_rest"), "completed")
        self.assertEqual(self.game.party.gold, before_gold + 45)

    def test_web_marsh_quest_grants_escort_bonus(self):
        self.finish_intro()
        accepted = self.game.quest_action("accept", "lost_herbalist")
        self.assertTrue(accepted["ok"])
        self.game.game_map.locations["forgotten_shrine"].boss_defeated = True
        self.game.flags["found_herbalist"] = True
        self.game.flags["escorted_herbalist"] = True
        before_gold = self.game.party.gold

        claimed = self.game.quest_action("claim", "lost_herbalist")

        self.assertTrue(claimed["ok"])
        self.assertEqual(self.game.party.gold, before_gold + 80)
        self.assertEqual(
            [item.name for item in self.game.inventory[-3:]],
            ["해독제", "해독제", "에테르"],
        )

    def test_web_archive_story_route_boss_reward_and_quest(self):
        self.finish_intro()
        self.game.game_map.current_id = "moonlit_spring"
        self.game.phase = "explore"
        self.game.game_map.current.dialogue_played = True
        blocked = self.game.move("세아가 알려준 수로로 들어간다")
        self.assertFalse(blocked["ok"])
        self.assertTrue(self.game.state()["location"]["exits"][1]["locked"])
        self.game.game_map.current.dialogue_played = False
        self.game._enter_current_location()
        self.assertEqual(self.game.phase, "dialogue")
        self.game.advance_dialogue(1)
        self.game.advance_dialogue()
        self.assertTrue(self.game.flags["found_herbalist"])

        opened = self.game.move("세아가 알려준 수로로 들어간다")
        self.assertTrue(opened["ok"])
        self.assertEqual(self.game.phase, "dialogue")
        self.assertEqual(self.game.game_map.current_id, "drowned_archive")
        self.game.advance_dialogue(0)
        self.game.advance_dialogue()
        self.assertTrue(self.game.flags["archive_reported"])
        self.assertEqual(self.game.quest_log.status("seals_echo"), "active")

        entered = self.game.move("메아리가 울리는 아래층으로 내려간다")
        self.assertTrue(entered["ok"])
        self.game.advance_dialogue()
        self.assertEqual(self.game.phase, "battle")
        self.assertEqual(self.game.enemies[0].name, "봉인의 메아리")
        self.game.enemies[0].hp = 1
        with patch("models.random.randint", return_value=0), patch(
            "web_app.random.random", return_value=0.99
        ):
            while self.game.phase == "battle":
                self.game.act({"type": "attack", "target": 0})
        self.assertTrue(self.game.flags["echo_purified"])
        self.assertTrue(self.game.game_map.current.boss_defeated)
        self.assertTrue(self.game.game_map.current.loot_claimed)
        self.assertEqual(self.game.quest_log.status("seals_echo"), "ready")
        self.assertEqual(sum(item.name == "기록실의 등불" for item in self.game.equipment_inventory), 1)

        self.game.move("가라앉은 기록실로 돌아간다")
        self.game.move("달빛 샘으로 돌아간다")
        self.game.game_map.current_id = "village"
        self.game._enter_current_location()
        before_gold = self.game.party.gold
        claimed = self.game.quest_action("claim", "seals_echo")
        self.assertTrue(claimed["ok"])
        self.assertEqual(self.game.party.gold, before_gold + 90)
        self.assertEqual(self.game.inventory[-1].name, "달빛 영약")

    def test_web_save_and_load_roundtrip(self):
        self.finish_intro()
        with tempfile.TemporaryDirectory() as directory, patch("save.SAVE_DIR", directory):
            self.game.party.gold = 73
            saved = self.game.save_action("save", 1)
            self.assertTrue(saved["ok"])
            self.assertTrue(self.game.state()["save_slots"][0]["exists"])
            self.game.party.gold = 1
            self.game.reset()
            self.assertEqual(self.game.phase, "setup")
            loaded = self.game.save_action("load", 1)
            self.assertTrue(loaded["ok"])
            self.assertEqual(self.game.party.gold, 73)
            self.assertEqual(self.game.game_map.current_id, "village")

    def test_browser_backup_restores_after_server_storage_reset(self):
        self.finish_intro()
        with tempfile.TemporaryDirectory() as first_dir, tempfile.TemporaryDirectory() as second_dir:
            self.game.save_dir = first_dir
            saved = self.game.save_action("save", 1)
            self.assertTrue(saved["ok"])
            self.assertEqual(saved["slot"], 1)
            self.assertEqual(saved["backup"]["party"][0]["name"], "레온")

            restarted = WebGame(Path(second_dir))
            restored = restarted.save_action("restore", 1, saved["backup"])
            self.assertTrue(restored["ok"])
            self.assertTrue(restored["state"]["save_slots"][0]["exists"])
            loaded = restarted.save_action("load", 1)
            self.assertTrue(loaded["ok"])
            self.assertEqual(restarted.party.members[0].name, "레온")

    def test_invalid_browser_backup_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            fresh = WebGame(Path(directory))
            result = fresh.save_action("restore", 1, {"save_version": 7})
            self.assertFalse(result["ok"])
            self.assertFalse(Path(directory, "slot1.json").exists())

    def test_start_battle_advances_to_player_turn(self):
        with patch("models.random.randint", return_value=0):
            result = self.game.start_battle("forest")
        self.assertTrue(result["ok"])
        self.assertEqual(self.game.phase, "battle")
        self.assertIsNotNone(self.game.current_actor)
        self.assertEqual(len(self.game.enemies), 2)

    def test_attack_uses_shared_character_rules(self):
        with patch("models.random.randint", return_value=0):
            self.game.start_battle("forest")
            before = self.game.enemies[0].hp
            result = self.game.act({"type": "attack", "target": 0})
        self.assertTrue(result["ok"])
        self.assertLess(self.game.enemies[0].hp, before)

    def test_invalid_action_does_not_consume_turn(self):
        self.game.start_battle("forest")
        actor = self.game.current_actor
        result = self.game.act({"type": "attack", "target": 99})
        self.assertFalse(result["ok"])
        self.assertIs(self.game.current_actor, actor)

    def test_boss_flee_is_blocked_and_consumes_action(self):
        self.game.start_battle("dark_knight")
        actor = self.game.current_actor
        result = self.game.act({"type": "flee"})
        self.assertTrue(result["ok"])
        self.assertEqual(self.game.phase, "battle")
        self.assertIn("보스 전투에서는 도망칠 수 없습니다.", self.game.logs)
        self.assertIsNot(self.game.current_actor, actor)

    def test_web_boss_phase_message_is_logged(self):
        self.finish_intro()
        self.game._begin_battle(
            [data.create_sealed_demon_lord()], "boss", "페이즈 연출 시험"
        )
        boss = self.game.enemies[0]
        boss.hp = int(boss.effective_max_hp * 0.3)
        self.game._enemy_action(boss)
        self.assertTrue(any("★" in message and "사슬" in message for message in self.game.logs))
        self.game._enemy_action(boss)
        self.assertTrue(any("★" in message and "붕괴" in message for message in self.game.logs))

    def test_victory_awards_gold_and_opens_encounter_selection(self):
        self.game.start_battle("forest")
        for enemy in self.game.enemies:
            enemy.hp = 1
        starting_gold = self.game.party.gold
        with patch("models.random.randint", return_value=0), patch("web_app.random.random", return_value=0.99):
            while self.game.phase == "battle":
                self.game.act({"type": "attack", "target": 0})
        self.assertEqual(self.game.phase, "victory")
        self.assertGreater(self.game.party.gold, starting_gold)
        self.assertTrue(self.game.state()["encounters"])


if __name__ == "__main__":
    unittest.main()
