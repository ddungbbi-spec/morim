"""무기 계열의 획득·전투 능력치·강화·저장 연동 검증."""
import unittest
from unittest.mock import patch

import data
import save
from blacksmith import enhance_equipment, preview_upgrade
from models import JOB_WEAPON_FAMILIES, Party, WEAPON_FAMILIES
from web_app import WebGame, DEFAULT_PARTY_SETUP


class WeaponFamilyTests(unittest.TestCase):
    def test_shop_purchase_and_equipped_combat_stats(self):
        game = WebGame()
        game.configure_party(DEFAULT_PARTY_SETUP)
        game.advance_dialogue(1)
        game.advance_dialogue()
        game.party.gold = 9999
        shop = next(i for i, s in enumerate(game.game_map.current.shops)
                    if data.IRON_SWORD in s.equipment)
        self.assertIn("권갑, 일곱 계열", game.game_map.current.shops[shop].description)
        self.assertEqual({w.weapon_family for w in data.SHOP_WEAPONS}, set(WEAPON_FAMILIES))
        compatible_creators = {
            "sword": data.create_warrior,
            "staff": data.create_mage,
            "dagger": data.create_rogue,
            "spear": data.create_lancer,
            "bow": data.create_archer,
            "axe": data.create_warrior,
            "fist": data.create_monk,
        }
        for index, weapon in enumerate(data.SHOP_WEAPONS):
            with self.subTest(family=weapon.weapon_family):
                self.assertTrue(game.shop_action("buy_equipment", index, shop)["ok"])
                target = len(game.equipment_inventory) - 1
                game.party.members[0] = compatible_creators[weapon.weapon_family]("무기 검증")
                self.assertTrue(game.equipment_action("equip", 0, target)["ok"])
                hero = game.party.members[0]
                self.assertEqual(hero.effective_attack, hero.attack + weapon.attack_bonus)
                self.assertEqual(hero.effective_speed, max(1, hero.speed + weapon.speed_bonus))
                self.assertEqual(hero.effective_max_mp, hero.max_mp + weapon.max_mp_bonus)
                self.assertAlmostEqual(hero.effective_critical_rate, hero.critical_rate + weapon.critical_rate_bonus)
                self.assertAlmostEqual(hero.effective_evasion_rate, hero.evasion_rate + weapon.evasion_rate_bonus)
                self.assertEqual(hero.effective_defense, hero.defense + weapon.defense_bonus)
                state = game._equipment_state(weapon)
                self.assertIn(weapon.family_label + " 계열", state["description"])
                self.assertEqual(state["weapon_family"], weapon.weapon_family)

    def test_job_weapon_matrix_rejects_incompatible_items_without_losing_inventory(self):
        self.assertEqual(set(JOB_WEAPON_FAMILIES), {
            "전사", "마법사", "힐러", "도적", "궁수",
            "소환술사", "기사", "무도가", "창술가", "마도사",
        })
        game = WebGame()
        self.assertTrue(game.configure_party([
            {"name": "창끝", "job": "lancer"},
            {"name": "비전", "job": "arcanist"},
            {"name": "철권", "job": "monk"},
        ])["ok"])
        game.advance_dialogue(1)
        game.advance_dialogue()
        game.equipment_inventory = [data.HUNTER_BOW, data.GUARD_SPEAR, data.IRON_SWORD,
                                    data.OAK_STAFF, data.IRON_GAUNTLET]

        before = list(game.equipment_inventory)
        rejected = game.equipment_action("equip", 0, 0)
        self.assertFalse(rejected["ok"])
        self.assertIn("사용 가능 무기: 창", rejected["error"])
        self.assertEqual(game.equipment_inventory, before)
        self.assertIsNone(game.party.members[0].equipment["weapon"])

        self.assertTrue(game.equipment_action("equip", 0, 1)["ok"])
        self.assertTrue(game.equipment_action("equip", 1, 1)["ok"])
        staff_index = game.equipment_inventory.index(data.OAK_STAFF)
        self.assertTrue(game.equipment_action("equip", 1, staff_index)["ok"])
        fist_index = game.equipment_inventory.index(data.IRON_GAUNTLET)
        self.assertTrue(game.equipment_action("equip", 2, fist_index)["ok"])

        state = game.state()
        self.assertEqual(state["party"][0]["allowed_weapon_families"], [{"id": "spear", "name": "창"}])
        self.assertEqual(
            {family["id"] for family in state["party"][1]["allowed_weapon_families"]},
            {"staff", "sword"},
        )

    def test_all_families_drop_and_save(self):
        for base in data.RANDOM_WEAPON_BASES:
            with self.subTest(family=base[1]), patch("data.random.choices", return_value=["common"]), patch(
                "data.random.choice", side_effect=[("강철검", "weapon"), base]
            ):
                weapon = data.generate_random_equipment(4)
                self.assertEqual(weapon.weapon_family, base[1])
                self.assertEqual(save._equipment_from_data(save._equipment_to_dict(weapon)), weapon)
                self.assertNotIn("+-", weapon.description)

    def test_preview_and_both_materials_preserve_family_and_traits(self):
        for weapon in data.SHOP_WEAPONS:
            for material in ("duplicate", "star_ore"):
                party = Party([data.create_warrior("검증")], gold=99999)
                equipment = [weapon]
                ores = [data.STAR_ORE] * 15
                for level in range(1, 6):
                    if material == "duplicate":
                        equipment.append(weapon)
                    expected = preview_upgrade(equipment[0])
                    actual, _ = enhance_equipment(party, equipment, 0, ores,
                                                  {"star_rift_closed": True}, material)
                    self.assertEqual(actual, expected)
                    self.assertEqual(actual.weapon_family, weapon.weapon_family)
                    self.assertEqual(actual.attack_bonus, weapon.attack_bonus + 2 * level)
                    self.assertEqual(actual.speed_bonus, weapon.speed_bonus)
                    self.assertEqual(actual.critical_rate_bonus, weapon.critical_rate_bonus)
                    self.assertEqual(actual.evasion_rate_bonus, weapon.evasion_rate_bonus)
                self.assertEqual(len(ores), 0 if material == "star_ore" else 15)

    def test_legacy_save_classifies_without_rebalancing(self):
        for weapon in (data.IRON_SWORD, data.OAK_STAFF, data.MITHRIL_DAGGER, data.SEALBREAKER_BLADE):
            record = save._equipment_to_dict(preview_upgrade(weapon))
            record.pop("weapon_family")
            loaded = save._equipment_from_data(record)
            self.assertEqual(loaded.weapon_family, weapon.weapon_family)
            self.assertEqual(loaded.attack_bonus, record["attack_bonus"])
        old_drop = {"name": "Lv.3 여행자 지팡이 · 예리함", "slot": "weapon", "attack_bonus": 7}
        loaded = save._equipment_from_data(old_drop)
        self.assertEqual((loaded.weapon_family, loaded.attack_bonus, loaded.max_mp_bonus), ("staff", 7, 0))
        for family in ("unknown", [], 1):
            with self.assertRaises(save.SaveGameError):
                save._equipment_from_data(dict(old_drop, weapon_family=family))
