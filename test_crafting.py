"""장비 분해·무기 합성 규칙의 단위 및 저장 회귀 테스트."""

import os
import tempfile
import unittest
from dataclasses import replace
from unittest.mock import patch

import data
import save
from crafting import (
    DISMANTLE_SHARDS, ENHANCEMENT_DISMANTLE_BONUS, SYNTHESIS_RECIPES,
    bulk_dismantle_reason, dismantle_equipment, dismantle_equipment_many,
    dismantle_value, apply_reforge, can_reforge, equipment_affixes,
    preview_reforge, preview_stat_text, reforge_cost, shard_count,
    synthesize_weapon, synthesis_preview,
)
from models import EQUIPMENT_RARITIES, Party, WEAPON_FAMILIES
from world import build_world


class CraftingTests(unittest.TestCase):
    def test_dismantle_values_and_save_roundtrip(self):
        flags = {}
        equipment = []
        expected = 0
        for enhancement, rarity in enumerate(EQUIPMENT_RARITIES):
            item = replace(
                data.IRON_SWORD, rarity=rarity,
                enhancement_level=enhancement,
            )
            value = DISMANTLE_SHARDS[rarity] + ENHANCEMENT_DISMANTLE_BONUS[enhancement]
            self.assertEqual(dismantle_value(item), value)
            equipment.append(item)
            expected += value

        while equipment:
            dismantle_equipment(equipment, 0, flags)
        self.assertEqual(shard_count(flags), expected)

        party = Party([data.create_warrior("분해공")])
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "slot1.json")
            save.save_game(party, [], build_world(), flags, [], path)
            _, _, _, restored_flags, _, _ = save.load_game(path)
        self.assertEqual(restored_flags["equipment_shards"], expected)

    def test_enhancement_dismantle_bonus_uses_progressive_recovery_curve(self):
        expected = [0, 3, 7, 12, 18, 25]
        values = [
            dismantle_value(replace(data.IRON_SWORD, enhancement_level=level))
            - DISMANTLE_SHARDS["common"]
            for level in range(6)
        ]
        self.assertEqual(values, expected)
        self.assertEqual(
            dismantle_value(replace(data.IRON_SWORD, enhancement_level=99)),
            DISMANTLE_SHARDS["common"] + 25,
        )

    def test_bulk_dismantle_is_atomic_and_excludes_protected_categories(self):
        safe_sword = data.IRON_SWORD
        safe_staff = data.OAK_STAFF
        enhanced = replace(data.IRON_SWORD, enhancement_level=1, locked=False)
        legendary = replace(data.IRON_SWORD, rarity="legendary", locked=False)
        locked = replace(data.OAK_STAFF, locked=True)
        equipment = [safe_sword, enhanced, safe_staff, legendary, locked]
        flags = {"equipment_shards": 5}

        removed, gained = dismantle_equipment_many(equipment, [0, 2], flags)
        self.assertEqual(removed, [safe_sword, safe_staff])
        self.assertEqual(gained, 4)
        self.assertEqual(flags["equipment_shards"], 9)
        self.assertEqual(equipment, [enhanced, legendary, locked])
        self.assertEqual(bulk_dismantle_reason(enhanced), "강화 장비")
        self.assertEqual(bulk_dismantle_reason(legendary), "전설 장비")
        self.assertEqual(bulk_dismantle_reason(locked), "잠금 보호 장비")

        before = (list(equipment), dict(flags))
        for indices in ([0], [1], [2], [0, 0], [], [-1], [99], [True]):
            with self.subTest(indices=indices), self.assertRaises(ValueError):
                dismantle_equipment_many(equipment, indices, flags)
            self.assertEqual((equipment, flags), before)

    def test_synthesis_makes_exact_family_rarity_and_consumes_cost(self):
        party = Party([data.create_lancer("합성공")], gold=999)
        party.members[0].level = 7
        flags = {"equipment_shards": 999}
        equipment = []

        item, shard_cost, gold_cost = synthesize_weapon(
            party, equipment, flags, "epic", "spear"
        )

        self.assertIs(equipment[0], item)
        self.assertEqual((item.slot, item.weapon_family, item.rarity),
                         ("weapon", "spear", "epic"))
        self.assertEqual(item.name.split()[0], "Lv.7")
        self.assertEqual(len(item.special_effect.split("/")), 3)
        self.assertEqual((shard_cost, gold_cost), SYNTHESIS_RECIPES["epic"])
        self.assertEqual(flags["equipment_shards"], 999 - shard_cost)
        self.assertEqual(party.gold, 999 - gold_cost)

    def test_reforge_preview_preserves_base_enhancement_and_locked_state(self):
        with patch("data.random.sample", return_value=data.RANDOM_AFFIXES[:2]):
            original = data.generate_random_equipment(
                4, forced_rarity="rare", forced_slot="weapon", forced_family="sword",
            )
        original = replace(original, enhancement_level=3, locked=True)
        party = Party([data.create_warrior("재련공")], gold=500)
        flags = {"equipment_shards": 50}

        with patch("data.random.sample", return_value=["활력"]):
            result = preview_reforge(original, "예리함")

        self.assertEqual(equipment_affixes(result), ["예리함", "활력"])
        self.assertEqual((result.enhancement_level, result.locked), (3, True))
        self.assertEqual(result.attack_bonus, original.attack_bonus)
        self.assertEqual(result.defense_bonus, original.defense_bonus - 2)
        self.assertEqual(result.max_hp_bonus, original.max_hp_bonus + 8)
        self.assertEqual(reforge_cost(original, "예리함"), (12, 80))
        self.assertEqual((party.gold, flags["equipment_shards"]), (500, 50))

        equipment = [original]
        applied, shards, gold = apply_reforge(
            party, equipment, flags, 0, result, "예리함",
        )
        self.assertIs(equipment[0], applied)
        self.assertEqual((shards, gold), (12, 80))
        self.assertEqual((party.gold, flags["equipment_shards"]), (420, 38))

    def test_reforge_rejects_static_low_rarity_bad_lock_and_short_resources(self):
        party = Party([data.create_warrior("검증공")], gold=999)
        flags = {"equipment_shards": 999}
        self.assertFalse(can_reforge(party, flags, data.IRON_SWORD)[0])

        with patch("data.random.sample", return_value=data.RANDOM_AFFIXES[:2]):
            generated = data.generate_random_equipment(3, forced_rarity="rare")
        self.assertFalse(can_reforge(party, flags, generated, "없는 옵션")[0])
        self.assertFalse(can_reforge(Party(party.members, gold=0), flags, generated)[0])
        self.assertFalse(can_reforge(party, {"equipment_shards": 0}, generated)[0])

    def test_synthesis_preview_matches_level_family_ranges_and_party_jobs(self):
        lancer = data.create_lancer("연화")
        lancer.level = 7
        mage = data.create_mage("서린")
        mage.level = 5
        party = Party([lancer, mage])

        preview = synthesis_preview(party, "epic", "spear")
        self.assertEqual((preview["level"], preview["rarity_name"], preview["family_name"]),
                         (7, "영웅", "창"))
        self.assertEqual(preview["option_count"], 3)
        self.assertTrue(preview["options_random"])
        self.assertEqual(preview["compatible_members"], [{"name": "연화", "job": "창술가"}])

        ranges = {entry["field"]: (entry["min"], entry["max"])
                  for entry in preview["stat_ranges"]}
        self.assertEqual(ranges["attack_bonus"], (9, 11))
        self.assertEqual(ranges["defense_bonus"], (3, 5))
        self.assertEqual(ranges["critical_rate_bonus"], (0, 5))
        self.assertIn("공격력 +9~+11", preview_stat_text(preview))

        common = synthesis_preview(party, "common", "staff")
        self.assertEqual(common["option_count"], 0)
        self.assertFalse(common["options_random"])
        self.assertTrue(all(stat["min"] == stat["max"] for stat in common["stat_ranges"]))

    def test_invalid_inputs_never_consume_resources(self):
        party = Party([data.create_warrior("안전공")], gold=999)
        flags = {"equipment_shards": 999}
        equipment = [data.IRON_SWORD]
        before = (party.gold, dict(flags), list(equipment))

        for rarity, family in (("mythic", "sword"), ("rare", "gun")):
            with self.subTest(rarity=rarity, family=family):
                with self.assertRaises(ValueError):
                    synthesize_weapon(party, equipment, flags, rarity, family)
                self.assertEqual((party.gold, flags, equipment), before)

        for index in (-1, 1, True, "0"):
            with self.subTest(index=index):
                with self.assertRaises(ValueError):
                    dismantle_equipment(equipment, index, flags)
                self.assertEqual((party.gold, flags, equipment), before)

    def test_forced_generator_accepts_all_families_and_rejects_bad_values(self):
        for family in WEAPON_FAMILIES:
            item = data.generate_random_equipment(
                3, forced_rarity="legendary", forced_slot="weapon",
                forced_family=family,
            )
            self.assertEqual((item.slot, item.weapon_family, item.rarity),
                             ("weapon", family, "legendary"))
        for kwargs in (
            {"forced_rarity": "mythic"},
            {"forced_slot": "shield"},
            {"forced_slot": "weapon", "forced_family": "gun"},
            {"forced_slot": "armor", "forced_family": "sword"},
        ):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                data.generate_random_equipment(1, **kwargs)


if __name__ == "__main__":
    unittest.main()
