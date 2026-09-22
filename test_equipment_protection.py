"""장비 잠금·보호 규칙과 웹·저장 연동 회귀 테스트."""

import os
import tempfile
import unittest
from dataclasses import replace

import data
import save
from blacksmith import enhance_equipment, matching_material_indices
from crafting import dismantle_equipment
from models import Party
from web_app import WebGame
from world import build_world


class EquipmentProtectionTests(unittest.TestCase):
    def test_locked_equipment_cannot_be_sold_dismantled_or_used_as_material(self):
        game = WebGame()
        game.party = Party([data.create_warrior("보호공")], gold=999)
        game.phase = "explore"
        game.game_map.move_to("village")
        locked = replace(data.IRON_SWORD, locked=True)
        game.equipment_inventory = [data.IRON_SWORD, locked]

        state = game.state()
        self.assertEqual([item["index"] for item in state["shop"]["sell_equipment"]], [0])
        self.assertEqual([item["index"] for item in state["crafting"]["dismantle"]], [0])
        self.assertEqual(matching_material_indices(game.equipment_inventory, 0), [])

        before = (game.party.gold, list(game.equipment_inventory), dict(game.flags))
        self.assertFalse(game.shop_action("sell_equipment", 1)["ok"])
        with self.assertRaises(ValueError):
            dismantle_equipment(game.equipment_inventory, 1, game.flags)
        self.assertEqual(before, (game.party.gold, game.equipment_inventory, game.flags))

    def test_lock_toggle_is_per_copy_and_allows_equipping(self):
        game = WebGame()
        game.party = Party([data.create_warrior("잠금공")])
        game.phase = "explore"
        game.equipment_inventory = [data.IRON_SWORD, data.IRON_SWORD]

        self.assertTrue(game.equipment_action("lock", 0, 0)["ok"])
        self.assertTrue(game.equipment_inventory[0].locked)
        self.assertFalse(game.equipment_inventory[1].locked)
        self.assertTrue(game.equipment_action("equip", 0, 0)["ok"])
        self.assertTrue(game.party.members[0].equipment["weapon"].locked)
        self.assertTrue(game.equipment_action("unlock", 0, slot="weapon")["ok"])
        self.assertFalse(game.party.members[0].equipment["weapon"].locked)

    def test_legendary_boss_and_enhanced_equipment_default_to_locked(self):
        generated = data.generate_random_equipment(
            5, forced_rarity="legendary", forced_slot="weapon", forced_family="sword"
        )
        self.assertTrue(generated.locked)
        self.assertTrue(data.STARWARD_CHARM.locked)

        party = Party([data.create_warrior("강화공")], gold=999)
        equipment = [data.IRON_SWORD, data.IRON_SWORD]
        upgraded, _ = enhance_equipment(party, equipment, 0)
        self.assertTrue(upgraded.locked)

    def test_lock_state_roundtrip_and_legacy_auto_protection(self):
        party = Party([data.create_warrior("저장공")])
        manually_unlocked_boss_reward = replace(data.STARWARD_CHARM, locked=False)
        manually_locked_common = replace(data.IRON_SWORD, locked=True)
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "slot1.json")
            save.save_game(
                party, [], build_world(), {},
                [manually_unlocked_boss_reward, manually_locked_common], path,
            )
            _, _, _, _, restored, _ = save.load_game(path)
        self.assertFalse(restored[0].locked)
        self.assertTrue(restored[1].locked)

        legacy_boss = save._equipment_to_dict(data.STARWARD_CHARM)
        legacy_boss.pop("locked")
        legacy_enhanced = save._equipment_to_dict(replace(data.IRON_SWORD, enhancement_level=1))
        legacy_enhanced.pop("locked")
        self.assertTrue(save._equipment_from_data(legacy_boss).locked)
        self.assertTrue(save._equipment_from_data(legacy_enhanced).locked)


if __name__ == "__main__":
    unittest.main()
