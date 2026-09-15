"""핵심 게임 규칙과 저장 기능의 회귀 테스트."""

import builtins
import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

import data
from advancement import ADVANCED_JOBS, advance, options_for
import dialogues
import save
import balance_simulator
import equipment_simulator
from blacksmith import MAX_ENHANCEMENT, enhance_equipment, upgrade_cost
from quests import QuestLog
from combat import Battle
from input_utils import prompt_index
from map import explore
from models import Party, StatusEffect
from shop import _sell_menu
from shop import Shop
from world import (
    build_world, complete_tower_challenge, create_scaled_tower_guardian,
    reset_tower_challenge,
)


class GameTests(unittest.TestCase):
    def test_all_second_jobs_unlock_at_level_five_and_preserve_growth(self):
        self.assertEqual(len(ADVANCED_JOBS), 12)
        for creator in data.JOB_CREATORS.values():
            for choice in options_for(creator("검증")):
                member = creator("검증")
                with self.assertRaises(ValueError):
                    advance(member, choice.id)
                member.level = 5
                member.sync_skills_for_level()
                original_skills = {skill.name for skill in member.skills}
                original_attack = member.attack
                selected = advance(member, choice.id)
                self.assertEqual(member.job, selected.name)
                self.assertEqual(member.base_job, selected.base_job)
                self.assertEqual(member.attack, original_attack + selected.attack)
                self.assertIn(selected.skill.name, [skill.name for skill in member.skills])
                self.assertTrue(original_skills.issubset({skill.name for skill in member.skills}))
                self.assertIs(data.SKILLS_BY_NAME[selected.skill.name], selected.skill)
                with self.assertRaises(ValueError):
                    advance(member, choice.id)
                member.gain_exp(100)
                self.assertIn(selected.skill.name, [skill.name for skill in member.skills])

    def test_second_job_save_roundtrip_and_old_save_compatibility(self):
        member = data.create_warrior("전직 기록")
        member.level = 5
        member.sync_skills_for_level()
        advance(member, "guardian")
        party = Party([member])
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "slot1.json")
            save.save_game(party, [], build_world(), {}, [], path)
            loaded_party, *_ = save.load_game(path)
            loaded = loaded_party.members[0]
            self.assertEqual(loaded.job, "수호기사")
            self.assertEqual(loaded.base_job, "전사")
            self.assertEqual(loaded.advanced_job_id, "guardian")
            self.assertEqual(loaded.max_hp, member.max_hp)
            self.assertEqual([s.name for s in loaded.skills], [s.name for s in member.skills])
            with self.assertRaises(ValueError):
                advance(loaded, "swordmaster")

            with open(path, encoding="utf-8") as stream:
                payload = json.load(stream)
            payload["party"][0].pop("base_job")
            payload["party"][0].pop("advanced_job_id")
            payload["party"][0]["job"] = "전사"
            payload["party"][0]["skills"].remove("철벽의 맹세")
            with open(path, "w", encoding="utf-8") as stream:
                json.dump(payload, stream)
            old_party, *_ = save.load_game(path)
            self.assertEqual(old_party.members[0].base_job, "전사")
            self.assertEqual(old_party.members[0].advanced_job_id, "")

    def test_balance_simulator_smoke(self):
        battle_rows = balance_simulator.run_analysis(trials=1, seed=7)
        route_rows = balance_simulator.run_route_analysis(trials=1, seed=7)
        self.assertEqual(len(battle_rows), 56 * len(balance_simulator.SCENARIOS))
        self.assertEqual(len(route_rows), 56 * len(balance_simulator.ROUTES))

    def test_equipment_simulator_smoke(self):
        rows, rarity_counts, _ = equipment_simulator.run_analysis(samples_per_level=2, seed=7)
        self.assertEqual(len(rows), 8 * 4)
        self.assertEqual(sum(rarity_counts.values()), 8 * 2)

    def test_healer_has_free_attack_skill(self):
        healer = data.create_healer("치유사")
        light_arrow = next(skill for skill in healer.skills if skill.name == "빛의 화살")
        self.assertEqual(light_arrow.mp_cost, 0)
        self.assertEqual(light_arrow.kind, "attack")

    def test_rogue_critical_and_evasion(self):
        rogue = data.create_rogue("그림자")
        enemy = data.create_slime()
        with patch("models.random.random", return_value=0.0), patch("models.random.randint", return_value=0):
            damage = rogue.basic_attack(enemy)
        self.assertTrue(rogue.last_attack_was_critical)
        self.assertEqual(damage, 12)

        enemy = data.create_slime()
        with patch("models.random.random", return_value=0.0), patch("models.random.randint", return_value=0):
            damage = enemy.basic_attack(rogue)
        self.assertEqual(damage, 0)
        self.assertTrue(rogue.last_damage_evaded)

    def test_rogue_traits_survive_save_roundtrip(self):
        rogue = data.create_rogue("저장 도적")
        party = Party([rogue])
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "slot1.json")
            save.save_game(party, [], build_world(), {}, [], path)
            loaded_party, *_ = save.load_game(path)
        loaded = loaded_party.members[0]
        self.assertEqual(loaded.critical_rate, 0.20)
        self.assertEqual(loaded.evasion_rate, 0.15)

    def test_legacy_rogue_save_receives_new_traits(self):
        legacy = save._character_to_dict(data.create_rogue("옛 도적"))
        legacy.pop("critical_rate")
        legacy.pop("evasion_rate")
        loaded = save._character_from_dict(legacy)
        self.assertEqual(loaded.critical_rate, 0.20)
        self.assertEqual(loaded.evasion_rate, 0.15)

    def test_boss_pattern_and_golem_phase(self):
        hero = data.create_warrior("대상")
        boss = data.create_dark_knight()
        first_skill, _ = boss.choose_action([hero])
        second_skill, _ = boss.choose_action([hero])
        self.assertEqual(first_skill.name, "위협의 포효")
        self.assertEqual(second_skill.name, "다크볼트")

        golem = data.create_cave_golem()
        golem.hp = golem.effective_max_hp // 2
        phase_skill, phase_target = golem.choose_action([hero])
        self.assertEqual(phase_skill.name, "암석 반격")
        self.assertTrue(phase_skill.aoe)
        self.assertIs(phase_target, hero)
        self.assertTrue(golem.phase_triggered)

    def test_multi_phase_boss_triggers_in_order_with_messages(self):
        hero = data.create_warrior("페이즈 대상")
        boss = data.create_sealed_demon_lord()
        boss.hp = int(boss.effective_max_hp * 0.3)

        first_skill, first_target = boss.choose_action([hero])
        self.assertEqual(first_skill.name, "심연의 결계")
        self.assertIs(first_target, boss)
        self.assertIn("사슬", boss.last_phase_message)

        second_skill, second_target = boss.choose_action([hero])
        self.assertEqual(second_skill.name, "최후의 심판")
        self.assertIs(second_target, hero)
        self.assertTrue(second_skill.aoe)
        self.assertIn("붕괴", boss.last_phase_message)

        third_skill, _ = boss.choose_action([hero])
        self.assertEqual(third_skill.name, "혼돈의 파동")
        self.assertEqual(boss.last_phase_message, "")

    def test_main_quest_progress_and_single_claim(self):
        quest_log = QuestLog()
        quest_log.sync_story_flags({"promised_elder": True})
        self.assertEqual(quest_log.status("ruins_darkness"), "active")

        game_map = build_world()
        game_map.locations["ruins"].boss_defeated = True
        quest_log.refresh_from_world(game_map)
        self.assertEqual(quest_log.status("ruins_darkness"), "ready")

        party = Party([data.create_warrior("의뢰인")])
        inventory = []
        self.assertTrue(quest_log.claim("ruins_darkness", party, inventory))
        self.assertEqual(party.gold, 50)
        self.assertEqual([item.name for item in inventory], ["포션", "포션"])
        self.assertFalse(quest_log.claim("ruins_darkness", party, inventory))
        self.assertEqual(party.gold, 50)

    def test_quest_accepts_completed_objective_and_saves(self):
        quest_log = QuestLog()
        game_map = build_world()
        game_map.locations["mine_depths"].boss_defeated = True
        self.assertTrue(quest_log.accept("miners_rest"))
        quest_log.refresh_from_world(game_map)
        self.assertEqual(quest_log.status("miners_rest"), "ready")

        party = Party([data.create_archer("기록자")])
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "slot1.json")
            save.save_game(party, [], game_map, {}, [], path, quest_log=quest_log)
            *_, loaded_log = save.load_game(path)
        self.assertEqual(loaded_log.status("miners_rest"), "ready")

    def test_marsh_quest_npc_choice_and_bonus_reward(self):
        quest_log = QuestLog()
        game_map = build_world()
        self.assertTrue(quest_log.accept("lost_herbalist"))
        game_map.locations["forgotten_shrine"].boss_defeated = True
        quest_log.refresh_from_world(game_map)
        self.assertEqual(quest_log.status("lost_herbalist"), "active")
        self.assertIsNotNone(game_map.locations["moonlit_spring"].dialogue)

        flags = {}
        with patch.object(builtins, "input", return_value="1"), redirect_stdout(io.StringIO()):
            dialogues.moonlit_spring_dialogue().run(flags)
        self.assertTrue(flags["found_herbalist"])
        self.assertTrue(flags["escorted_herbalist"])
        quest_log.refresh_from_world(game_map, flags)
        self.assertEqual(quest_log.status("lost_herbalist"), "ready")

        party = Party([data.create_healer("구조대")], gold=0)
        inventory = []
        self.assertTrue(
            quest_log.claim("lost_herbalist", party, inventory, flags)
        )
        self.assertEqual(party.gold, 80)
        self.assertEqual(
            [item.name for item in inventory], ["해독제", "해독제", "에테르"]
        )

    def test_menu_rejects_zero_negative_and_text(self):
        with patch.object(builtins, "input", side_effect=["0", "-1", "문자", "2"]):
            self.assertEqual(prompt_index("> ", 3), 1)

    def test_guard_reduces_direct_damage(self):
        hero = data.create_warrior("방어자")
        battle = Battle(Party([hero]), [data.create_slime()], [])
        with patch.object(builtins, "input", return_value="4"):
            battle._player_turn(hero)
        self.assertTrue(hero.guarding)
        self.assertEqual(hero.receive_damage(9), 5)

    def test_key_item_cannot_be_used_or_sold(self):
        hero = data.create_warrior("열쇠지킴이")
        inventory = [data.RUSTY_KEY]
        battle = Battle(Party([hero]), [data.create_slime()], inventory)
        with patch.object(builtins, "input", side_effect=["3", "4"]):
            battle._player_turn(hero)
        self.assertEqual(inventory, [data.RUSTY_KEY])
        _sell_menu(battle.party, inventory, [])
        self.assertEqual(inventory, [data.RUSTY_KEY])

    def test_action_cancel_returns_to_main_menu_without_cost(self):
        hero = data.create_warrior("취소 확인")
        starting_mp = hero.mp
        battle = Battle(Party([hero]), [data.create_slime()], [])
        cancel_option = str(len(hero.skills) + 1)
        with patch.object(builtins, "input", side_effect=["2", cancel_option, "4"]):
            battle._player_turn(hero)
        self.assertEqual(hero.mp, starting_mp)
        self.assertTrue(hero.guarding)

    def test_target_cancel_returns_to_main_menu(self):
        hero = data.create_warrior("대상 취소")
        enemy = data.create_slime()
        battle = Battle(Party([hero]), [enemy], [])
        with patch.object(builtins, "input", side_effect=["1", "2", "4"]):
            battle._player_turn(hero)
        self.assertEqual(enemy.hp, enemy.effective_max_hp)
        self.assertTrue(hero.guarding)

    def test_flee_succeeds_from_normal_battle_without_rewards(self):
        hero = data.create_rogue("도주자")
        party = Party([hero])
        enemy = data.create_slime()
        starting_gold = party.gold
        battle = Battle(party, [enemy], [])
        with patch.object(builtins, "input", return_value="6"), patch(
            "combat.random.random", return_value=0.0
        ), redirect_stdout(io.StringIO()):
            result = battle.run()
        self.assertTrue(result)
        self.assertTrue(battle.fled)
        self.assertTrue(enemy.is_alive)
        self.assertEqual(party.gold, starting_gold)

    def test_flee_is_blocked_in_boss_battle(self):
        battle = Battle(Party([data.create_warrior("도전자")]), [data.create_dark_knight()], [])
        with redirect_stdout(io.StringIO()):
            result = battle._attempt_flee()
        self.assertFalse(result)
        self.assertFalse(battle.fled)

    def test_enemy_info_shows_elements_and_status_duration(self):
        enemy = data.create_mine_drake()
        enemy.status_effects.append(
            StatusEffect(kind="poison", name="중독", remaining_turns=3, power=1)
        )
        battle = Battle(Party([data.create_mage("관찰자")]), [enemy], [])
        output = io.StringIO()
        with redirect_stdout(output):
            battle._print_enemy_info()
        rendered = output.getvalue()
        self.assertIn("약점 냉", rendered)
        self.assertIn("저항 화", rendered)
        self.assertIn("중독 3턴", rendered)

    def test_steal_is_bonus_and_only_once_per_enemy(self):
        rogue = data.create_rogue("도적")
        enemy = data.create_goblin()
        original_reward = enemy.gold_reward
        first, _, _ = rogue.use_skill(data.STEAL, enemy)
        rogue.mp = rogue.max_mp
        second, _, _ = rogue.use_skill(data.STEAL, enemy)
        self.assertEqual(first, min(original_reward, data.STEAL.power))
        self.assertEqual(second, 0)
        self.assertEqual(enemy.gold_reward, original_reward)

    def test_level_up_fills_equipment_adjusted_maximum(self):
        hero = data.create_warrior("성장자")
        hero.equip(data.LEATHER_ARMOR)
        hero.gain_exp(20)
        self.assertEqual(hero.hp, hero.effective_max_hp)

    def test_skill_growth_unlocks_and_upgrades(self):
        warrior = data.create_warrior("성장 전사")
        warrior.gain_exp(20)
        self.assertEqual(warrior.level, 2)
        self.assertIn("수호 태세", [skill.name for skill in warrior.skills])
        self.assertTrue(any("습득" in message for message in warrior.last_growth_messages))

        warrior.gain_exp(40)
        skill_names = [skill.name for skill in warrior.skills]
        self.assertEqual(warrior.level, 3)
        self.assertNotIn("파워 슬래시", skill_names)
        self.assertIn("브레이버 슬래시", skill_names)
        self.assertTrue(any("강화" in message for message in warrior.last_growth_messages))

    def test_each_job_has_level_two_growth(self):
        for creator in data.JOB_CREATORS.values():
            member = creator("성장 확인")
            before = {skill.name for skill in member.skills}
            member.gain_exp(20)
            after = {skill.name for skill in member.skills}
            self.assertGreater(len(after - before), 0, member.job)

    def test_loaded_character_keeps_future_progression(self):
        archer = data.create_archer("저장 궁수")
        party = Party([archer])
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "slot1.json")
            save.save_game(party, [], build_world(), {}, [], path)
            loaded_party, *_ = save.load_game(path)
        loaded = loaded_party.members[0]
        loaded.gain_exp(20)
        self.assertIn("다중 사격", [skill.name for skill in loaded.skills])

    def test_boss_equipment_special_effects(self):
        rogue = data.create_rogue("장비 도적")
        rogue.equip(data.MITHRIL_DAGGER)
        self.assertAlmostEqual(rogue.effective_critical_rate, 0.30)

        warrior = data.create_warrior("장비 전사")
        warrior.equip(data.LEGENDARY_ARMOR)
        self.assertEqual(warrior.receive_damage(10), 9)

    def test_random_equipment_rarity_and_affixes(self):
        affixes = data.RANDOM_AFFIXES[:3]
        with patch.object(data.random, "choices", return_value=["legendary"]), \
             patch.object(data.random, "choice", return_value=("강철검", "weapon")), \
             patch.object(data.random, "sample", return_value=affixes):
            equipment = data.generate_random_equipment(3)
        self.assertEqual(equipment.rarity, "legendary")
        self.assertTrue(equipment.generated)
        self.assertEqual(equipment.attack_bonus, 7)
        self.assertEqual(equipment.defense_bonus, 2)
        self.assertEqual(equipment.max_hp_bonus, 8)

    def test_enemy_can_drop_random_equipment(self):
        party = Party([data.create_warrior("수집가")])
        enemy = data.create_slime()
        enemy.equipment_drop_chance = 1.0
        equipment_inventory = []
        dropped = data.generate_random_equipment(1)
        battle = Battle(party, [enemy], [], equipment_inventory)
        with patch("combat.random.random", return_value=0.0), \
             patch("data.generate_random_equipment", return_value=dropped):
            battle._victory()
        self.assertEqual(equipment_inventory, [dropped])

    def test_generated_equipment_save_roundtrip_and_legacy_name(self):
        generated = data.generate_random_equipment(4)
        hero = data.create_archer("장비 기록자")
        hero.equip(generated)
        reserve = data.generate_random_equipment(2)
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "slot1.json")
            save.save_game(Party([hero]), [], build_world(), {}, [reserve], path)
            loaded_party, _, _, _, loaded_equipment, _ = save.load_game(path)
        restored = loaded_party.members[0].equipment[generated.slot]
        self.assertEqual(save._equipment_to_dict(restored), save._equipment_to_dict(generated))
        self.assertEqual(save._equipment_to_dict(loaded_equipment[0]), save._equipment_to_dict(reserve))
        self.assertIs(save._equipment_from_data("철검"), data.IRON_SWORD)

    def test_legacy_high_level_save_syncs_growth_skills(self):
        legacy = save._character_to_dict(data.create_mage("옛 마법사"))
        legacy["level"] = 3
        loaded = save._character_from_dict(legacy)
        names = [skill.name for skill in loaded.skills]
        self.assertNotIn("파이라", names)
        self.assertIn("에어로라", names)
        self.assertIn("파이가", names)

    def test_blacksmith_enhances_clone_and_preserves_original(self):
        party = Party([data.create_warrior("대장장이 손님")], gold=500)
        equipment_inventory = [data.IRON_SWORD, data.IRON_SWORD]
        original_attack = data.IRON_SWORD.attack_bonus
        cost = upgrade_cost(data.IRON_SWORD)

        upgraded, paid = enhance_equipment(party, equipment_inventory, 0)

        self.assertEqual(paid, cost)
        self.assertEqual(party.gold, 500 - cost)
        self.assertEqual(len(equipment_inventory), 1)
        self.assertEqual(upgraded.enhancement_level, 1)
        self.assertEqual(upgraded.attack_bonus, original_attack + 2)
        self.assertIn("+1", upgraded.display_name)
        self.assertEqual(data.IRON_SWORD.enhancement_level, 0)
        self.assertEqual(data.IRON_SWORD.attack_bonus, original_attack)

    def test_blacksmith_max_level_and_save_round_trip(self):
        party = Party([data.create_warrior("강화 장인")], gold=9999)
        equipment = data.IRON_SWORD
        for level in range(1, MAX_ENHANCEMENT + 1):
            equipment_inventory = [equipment, data.IRON_SWORD]
            equipment, _ = enhance_equipment(party, equipment_inventory, 0)
            self.assertEqual(equipment.enhancement_level, level)

        with self.assertRaisesRegex(ValueError, "최대 강화"):
            enhance_equipment(party, [equipment, data.IRON_SWORD], 0)

        restored = save._equipment_from_data(save._equipment_to_dict(equipment))
        self.assertEqual(restored.enhancement_level, MAX_ENHANCEMENT)
        self.assertEqual(restored.attack_bonus, equipment.attack_bonus)

    def test_world_links_are_valid(self):
        game_map = build_world()
        for location in game_map.locations.values():
            for target in location.exits.values():
                self.assertIn(target, game_map.locations)

    def test_console_defeated_boss_can_be_rechallenged(self):
        game_map = build_world()
        game_map.current_id = "ruins"
        game_map.current.dialogue_played = True
        game_map.current.boss_defeated = True
        party = Party([data.create_warrior("재도전자")])

        with patch("map.Battle") as battle_type, patch.object(
            builtins, "input", side_effect=["6", "9", "y"]
        ), redirect_stdout(io.StringIO()):
            battle_type.return_value.run.return_value = True
            result = explore(game_map, party, [], {}, [])

        self.assertFalse(result)
        battle_type.assert_called_once()
        self.assertEqual(battle_type.call_args.args[1][0].name, "다크 나이트")
        self.assertTrue(game_map.current.boss_defeated)

    def test_mist_marsh_expansion_is_connected_and_reward_registered(self):
        game_map = build_world()
        self.assertEqual(len(game_map.locations), 25)
        self.assertEqual(
            game_map.locations["deep_forest"].exits["안개 습지로 들어간다"],
            "mist_marsh",
        )
        self.assertEqual(
            game_map.locations["forgotten_shrine"].exits["달빛 샘으로 들어간다"],
            "moonlit_spring",
        )
        boss = game_map.locations["forgotten_shrine"].boss()[0]
        self.assertEqual(boss.name, "안개의 여왕")
        self.assertEqual(boss.weakness, "thunder")
        self.assertIs(data.EQUIPMENT_BY_NAME["안개의 망토"], data.MIST_CLOAK)

    def test_archive_episode_choice_quest_ending_and_save(self):
        game_map = build_world()
        label = "세아가 알려준 수로로 들어간다"
        spring = game_map.locations["moonlit_spring"]
        self.assertEqual(spring.exits[label], "drowned_archive")
        self.assertFalse(spring.flag_requirements[label].is_met({}))
        self.assertTrue(spring.flag_requirements[label].is_met({"found_herbalist": True}))
        self.assertEqual(game_map.locations["drowned_archive"].exits[
            "메아리가 울리는 아래층으로 내려간다"
        ], "echo_vault")
        self.assertEqual(game_map.locations["echo_vault"].boss()[0].name, "봉인의 메아리")
        self.assertIs(data.EQUIPMENT_BY_NAME["기록실의 등불"], data.ARCHIVE_LANTERN)

        for choice, reported, reward in (("1", True, 90), ("2", False, 65)):
            with self.subTest(choice=choice):
                flags = {"found_herbalist": True, "echo_purified": True}
                with patch.object(builtins, "input", return_value=choice), redirect_stdout(io.StringIO()):
                    dialogues.drowned_archive_dialogue().run(flags)
                self.assertTrue(flags["archive_discovered"])
                self.assertEqual(flags["archive_reported"], reported)

                quest_log = QuestLog()
                quest_log.sync_story_flags(flags)
                self.assertEqual(quest_log.status("seals_echo"), "active")
                game_map.locations["echo_vault"].boss_defeated = True
                quest_log.refresh_from_world(game_map, flags)
                self.assertEqual(quest_log.status("seals_echo"), "ready")
                party = Party([data.create_healer("기록 수호자")], gold=0)
                inventory = []
                self.assertTrue(quest_log.claim("seals_echo", party, inventory, flags))
                self.assertEqual(party.gold, reward)
                self.assertEqual([item.name for item in inventory], ["달빛 영약"])
                self.assertFalse(quest_log.claim("seals_echo", party, inventory, flags))
                ending_lines = dialogues.ending_dialogue().nodes["end"].resolve_lines(flags)
                self.assertTrue(any("기록" in line for line in ending_lines))

                with tempfile.TemporaryDirectory() as directory:
                    game_map.move_to("echo_vault")
                    game_map.locations["echo_vault"].dialogue_played = True
                    game_map.locations["echo_vault"].loot_claimed = True
                    path = os.path.join(directory, "slot1.json")
                    save.save_game(party, inventory, game_map, flags,
                                   [data.ARCHIVE_LANTERN], path, quest_log=quest_log)
                    _, loaded_inventory, loaded_map, loaded_flags, loaded_equipment, loaded_log = save.load_game(path)
                self.assertEqual(loaded_map.current_id, "echo_vault")
                self.assertTrue(loaded_map.current.boss_defeated)
                self.assertTrue(loaded_map.current.loot_claimed)
                self.assertEqual(loaded_flags["archive_reported"], reported)
                self.assertEqual(loaded_log.status("seals_echo"), "completed")
                self.assertEqual(loaded_inventory[0].name, "달빛 영약")
                self.assertEqual(loaded_equipment[0].name, "기록실의 등불")

    def test_console_archive_boss_sets_story_flag(self):
        game_map = build_world()
        game_map.move_to("echo_vault")
        game_map.current.dialogue_played = True
        flags = {"archive_discovered": True, "archive_reported": False}
        party = Party([data.create_warrior("메아리 수호자")])
        equipment = []
        with patch("map.Battle") as battle_type, patch.object(
            builtins, "input", side_effect=["9", "y"]
        ), redirect_stdout(io.StringIO()):
            battle_type.return_value.run.return_value = True
            result = explore(game_map, party, [], flags, equipment)
        self.assertFalse(result)
        self.assertTrue(flags["echo_purified"])
        self.assertTrue(game_map.current.boss_defeated)
        self.assertEqual([item.name for item in equipment], ["기록실의 등불"])

    def test_elder_armory_uses_story_flag_and_registers_reward(self):
        game_map = build_world()
        label = "장로의 비밀 무기고로 들어간다"
        requirement = game_map.locations["village"].flag_requirements[label]
        self.assertFalse(requirement.is_met({"promised_elder": False}))
        self.assertTrue(requirement.is_met({"promised_elder": True}))
        self.assertEqual(game_map.locations["village"].exits[label], "elder_armory")
        self.assertIs(
            data.EQUIPMENT_BY_NAME["장로의 수호 인장"],
            data.ELDER_GUARDIAN_SIGIL,
        )

    def test_conditional_shop_unlock_and_discount_rules(self):
        shop = Shop(
            "시험 약초점", items=[data.MOONLIGHT_TONIC],
            required_flag="found_herbalist", discount_flag="escorted_herbalist",
            discount_rate=0.20,
        )
        self.assertFalse(shop.is_available({}))
        self.assertTrue(shop.is_available({"found_herbalist": True}))
        self.assertEqual(shop.price_for(data.MOONLIGHT_TONIC, {}), 35)
        self.assertEqual(
            shop.price_for(data.MOONLIGHT_TONIC, {"escorted_herbalist": True}), 28
        )
        self.assertIs(data.ITEMS_BY_NAME["달빛 영약"], data.MOONLIGHT_TONIC)

    def test_tower_summit_returns_directly_to_village(self):
        game_map = build_world()
        summit = game_map.locations["tower_summit"]
        self.assertEqual(
            summit.exits["탑의 마법진으로 마을에 귀환한다"], "village"
        )

    def test_repeat_tower_scales_and_grants_distinct_rewards(self):
        first_party = Party([data.create_warrior("첫 정복자")], gold=0)
        first_rewards = []
        first_count, first_gold, first_item = complete_tower_challenge(
            {}, first_party, first_rewards
        )
        self.assertEqual((first_count, first_gold, first_item), (1, 0, None))
        self.assertEqual(first_party.gold, 0)
        self.assertFalse(first_rewards)

        base = data.create_tower_guardian()
        flags = {"tower_clear_count": 1, "tower_challenge_active": True}
        scaled = create_scaled_tower_guardian(flags)
        self.assertIn("2단계", scaled.name)
        self.assertGreater(scaled.max_hp, base.max_hp)
        self.assertGreater(scaled.attack, base.attack)
        self.assertGreater(scaled.defense, base.defense)

        party = Party([data.create_warrior("도전자")], gold=0)
        equipment_inventory = []
        with patch("world.data.generate_random_equipment", return_value=data.IRON_SWORD):
            count, bonus_gold, reward = complete_tower_challenge(
                flags, party, equipment_inventory
            )
        self.assertEqual(count, 2)
        self.assertEqual(bonus_gold, 55)
        self.assertEqual(party.gold, 55)
        self.assertIs(reward, data.IRON_SWORD)
        self.assertEqual(equipment_inventory, [data.IRON_SWORD])
        self.assertFalse(flags["tower_challenge_active"])

    def test_tower_reset_supports_legacy_first_clear(self):
        game_map = build_world()
        game_map.locations["tower_summit"].boss_defeated = True
        flags = {}
        self.assertTrue(reset_tower_challenge(game_map, flags))
        self.assertFalse(game_map.locations["tower_summit"].boss_defeated)
        self.assertEqual(flags["tower_clear_count"], 1)
        self.assertTrue(flags["tower_challenge_active"])
        self.assertFalse(reset_tower_challenge(game_map, flags))

    def test_party_full_restore_recovers_every_status(self):
        party = Party([data.create_warrior("휴식자"), data.create_mage("마도사")])
        for member in party.members:
            member.hp = 0
            member.mp = 0
            member.guarding = True
            member.status_effects.append(
                StatusEffect("poison", "중독", 3, power=4)
            )
        party.full_restore()
        for member in party.members:
            self.assertEqual(member.hp, member.effective_max_hp)
            self.assertEqual(member.mp, member.effective_max_mp)
            self.assertFalse(member.status_effects)
            self.assertFalse(member.guarding)

    def test_seal_power_changes_stats_once(self):
        party = Party([data.create_warrior("레온")])
        game_map = build_world()
        game_map.current_id = "final_chamber"
        game_map.current.boss_defeated = True
        game_map.current.dialogue_played = True
        before = (party.members[0].max_hp, party.members[0].attack, party.members[0].defense)
        answers = iter(["9", "y"])
        with patch.object(builtins, "input", side_effect=lambda _="": next(answers)):
            self.assertFalse(explore(game_map, party, [], {"embraced_power": True}, []))
        after = (party.members[0].max_hp, party.members[0].attack, party.members[0].defense)
        self.assertEqual(after, (before[0] + 6, before[1] + 2, before[2] + 1))

    def test_final_boss_console_returns_to_village_after_loot_and_ending(self):
        party = Party([data.create_warrior("귀환자")])
        game_map = build_world()
        game_map.current_id = "final_chamber"
        game_map.current.dialogue_played = True
        game_map.locations["village"].dialogue_played = True
        equipment = []
        output = io.StringIO()
        with patch.object(Battle, "run", return_value=True), patch(
            "map.prompt_index", side_effect=lambda _, count: count - 1
        ), patch("map.prompt_yes_no", return_value=True), redirect_stdout(output):
            self.assertFalse(explore(game_map, party, [], {}, equipment))
        self.assertEqual(game_map.current_id, "village")
        self.assertTrue(game_map.locations["final_chamber"].boss_defeated)
        self.assertTrue(game_map.locations["final_chamber"].loot_claimed)
        self.assertTrue(game_map.locations["ending"].dialogue_played)
        self.assertEqual(sum(item.name == data.SEALBREAKER_BLADE.name for item in equipment), 1)
        self.assertIn("빛의 마법진", output.getvalue())

    def test_final_boss_console_rematch_returns_without_duplicate_loot(self):
        party = Party([data.create_warrior("재도전자")])
        game_map = build_world()
        game_map.current_id = "final_chamber"
        chamber = game_map.current
        chamber.dialogue_played = chamber.boss_defeated = chamber.loot_claimed = True
        game_map.locations["village"].dialogue_played = True
        equipment = [data.SEALBREAKER_BLADE]
        selections = iter([5])
        with patch.object(Battle, "run", return_value=True), patch(
            "map.prompt_index", side_effect=lambda _, count: next(selections, count - 1)
        ), patch("map.prompt_yes_no", return_value=True), redirect_stdout(io.StringIO()):
            self.assertFalse(explore(game_map, party, [], {}, equipment))
        self.assertEqual(game_map.current_id, "village")
        self.assertEqual(equipment, [data.SEALBREAKER_BLADE])

    def test_save_roundtrip_backup_and_corruption_detection(self):
        party = Party([data.create_warrior("저장자")], gold=37)
        game_map = build_world()
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "slot1.json")
            save.save_game(party, [data.POTION], game_map, {}, [], path)
            save.save_game(party, [data.POTION], game_map, {}, [], path)
            self.assertTrue(os.path.exists(path + ".bak"))
            loaded_party, inventory, *_ = save.load_game(path)
            self.assertEqual(loaded_party.gold, 37)
            self.assertEqual([item.name for item in inventory], ["포션"])

            with open(path, "w", encoding="utf-8") as stream:
                stream.write("{손상")
            with self.assertRaises(save.SaveGameError):
                save.load_game(path)

    def test_save_slot_metadata_and_play_time_roundtrip(self):
        with patch("models.time.monotonic", side_effect=[100.0, 3761.0, 4000.0]):
            party = Party([data.create_warrior("레온"), data.create_mage("리제")], gold=52)
            game_map = build_world()
            with tempfile.TemporaryDirectory() as directory:
                path = os.path.join(directory, "slot1.json")
                save.save_game(party, [], game_map, {}, [], path)

                with open(path, "r", encoding="utf-8") as stream:
                    payload = json.load(stream)
                metadata = payload["metadata"]
                self.assertEqual(payload["save_version"], 8)
                self.assertEqual(metadata["play_time_seconds"], 3661)
                self.assertEqual(metadata["location_name"], "시작 마을")
                self.assertEqual(metadata["party_jobs"], ["전사", "마법사"])
                self.assertEqual(metadata["average_level"], 1.0)

                summary = save._slot_summary(path)
                self.assertIn("평균 Lv.1", summary)
                self.assertIn("전사/마법사", summary)
                self.assertIn("시작 마을", summary)
                self.assertIn("01:01:01", summary)

                loaded_party, *_ = save.load_game(path)
                self.assertEqual(loaded_party.play_time_seconds, 3661)

    def test_legacy_slot_summary_uses_location_name(self):
        party = Party([data.create_healer("옛 저장")])
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "slot1.json")
            save.save_game(party, [], build_world(), {}, [], path)
            with open(path, "r", encoding="utf-8") as stream:
                payload = json.load(stream)
            payload["save_version"] = 6
            payload.pop("metadata")
            with open(path, "w", encoding="utf-8") as stream:
                json.dump(payload, stream, ensure_ascii=False)

            summary = save._slot_summary(path)
            self.assertIn("힐러", summary)
            self.assertIn("시작 마을", summary)
            loaded_party, *_ = save.load_game(path)
            self.assertEqual(loaded_party.play_time_seconds, 0)


if __name__ == "__main__":
    unittest.main()
