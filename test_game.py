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
import save
import balance_simulator
import equipment_simulator
from quests import QuestLog
from combat import Battle
from input_utils import prompt_index
from map import explore
from models import Party, StatusEffect
from shop import _sell_menu
from world import (
    build_world, complete_tower_challenge, create_scaled_tower_guardian,
    reset_tower_challenge,
)


class GameTests(unittest.TestCase):
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

    def test_world_links_are_valid(self):
        game_map = build_world()
        for location in game_map.locations.values():
            for target in location.exits.values():
                self.assertIn(target, game_map.locations)

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
        answers = iter(["8", "y"])
        with patch.object(builtins, "input", side_effect=lambda _="": next(answers)):
            self.assertFalse(explore(game_map, party, [], {"embraced_power": True}, []))
        after = (party.members[0].max_hp, party.members[0].attack, party.members[0].defense)
        self.assertEqual(after, (before[0] + 6, before[1] + 2, before[2] + 1))

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
                self.assertEqual(payload["save_version"], 7)
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
