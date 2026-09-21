"""미착용 장비 분해와 무기 계열·등급 지정 합성 규칙."""

from typing import List, Tuple

from input_utils import prompt_index, prompt_yes_no
from models import (
    EQUIPMENT_RARITIES, RARITY_NAMES_KR, WEAPON_FAMILIES,
    Equipment, Party,
)


SHARD_FLAG = "equipment_shards"
DISMANTLE_SHARDS = {
    "common": 1, "uncommon": 3, "rare": 8, "epic": 20, "legendary": 50,
}
SYNTHESIS_RECIPES = {
    "common": (4, 15),
    "uncommon": (10, 35),
    "rare": (24, 80),
    "epic": (55, 180),
    "legendary": (120, 400),
}


def shard_count(flags: dict) -> int:
    value = flags.get(SHARD_FLAG, 0)
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else 0


def dismantle_value(item: Equipment) -> int:
    """등급 기본 조각에 강화 단계당 2조각을 더한다."""
    return DISMANTLE_SHARDS.get(item.rarity, 1) + max(0, item.enhancement_level) * 2


def dismantle_equipment(
    equipment_inventory: List[Equipment], index: int, flags: dict,
) -> Tuple[Equipment, int]:
    if not isinstance(index, int) or isinstance(index, bool) or not 0 <= index < len(equipment_inventory):
        raise ValueError("올바른 분해 장비를 선택하세요.")
    item = equipment_inventory.pop(index)
    gained = dismantle_value(item)
    flags[SHARD_FLAG] = shard_count(flags) + gained
    return item, gained


def synthesis_requirements(rarity: str) -> Tuple[int, int]:
    if rarity not in SYNTHESIS_RECIPES:
        raise ValueError("올바른 합성 등급을 선택하세요.")
    return SYNTHESIS_RECIPES[rarity]


def can_synthesize(party: Party, flags: dict, rarity: str, family: str) -> Tuple[bool, str]:
    if rarity not in EQUIPMENT_RARITIES:
        return False, "올바른 합성 등급을 선택하세요."
    if family not in WEAPON_FAMILIES:
        return False, "올바른 무기 계열을 선택하세요."
    shards, gold = SYNTHESIS_RECIPES[rarity]
    if shard_count(flags) < shards:
        return False, f"장비 조각이 부족합니다. ({shards}개 필요)"
    if party.gold < gold:
        return False, f"골드가 부족합니다. ({gold}G 필요)"
    return True, ""


def synthesize_weapon(
    party: Party, equipment_inventory: List[Equipment], flags: dict,
    rarity: str, family: str,
) -> Tuple[Equipment, int, int]:
    allowed, reason = can_synthesize(party, flags, rarity, family)
    if not allowed:
        raise ValueError(reason)
    shards, gold = SYNTHESIS_RECIPES[rarity]
    level = max((member.level for member in party.members), default=1)
    import data
    item = data.generate_random_equipment(
        level, forced_rarity=rarity, forced_slot="weapon", forced_family=family,
    )
    flags[SHARD_FLAG] = shard_count(flags) - shards
    party.gold -= gold
    equipment_inventory.append(item)
    return item, shards, gold


def run_crafting(
    party: Party, equipment_inventory: List[Equipment], flags: dict,
) -> None:
    while True:
        print(f"\n[분해·합성 공방] 장비 조각 {shard_count(flags)}개 / {party.gold}G")
        print("  1) 장비 분해")
        print("  2) 무기 합성")
        print("  3) 돌아가기")
        action = prompt_index("> ", 3)
        if action == 2:
            return
        if action == 0:
            if not equipment_inventory:
                print("분해할 미착용 장비가 없습니다.")
                continue
            for index, item in enumerate(equipment_inventory, 1):
                print(f"  {index}) {item.display_name} → 조각 {dismantle_value(item)}개")
            print(f"  {len(equipment_inventory) + 1}) 취소")
            selected = prompt_index("> ", len(equipment_inventory) + 1)
            if selected == len(equipment_inventory):
                continue
            item = equipment_inventory[selected]
            if prompt_yes_no(f"{item.display_name}을(를) 분해할까요? (y/n)> "):
                removed, gained = dismantle_equipment(equipment_inventory, selected, flags)
                print(f"{removed.display_name} 분해 완료! 장비 조각 {gained}개를 얻었습니다.")
            continue

        families = list(WEAPON_FAMILIES)
        for index, family in enumerate(families, 1):
            print(f"  {index}) {WEAPON_FAMILIES[family]}")
        print(f"  {len(families) + 1}) 취소")
        family_index = prompt_index("> ", len(families) + 1)
        if family_index == len(families):
            continue
        family = families[family_index]
        for index, rarity in enumerate(EQUIPMENT_RARITIES, 1):
            shards, gold = SYNTHESIS_RECIPES[rarity]
            print(f"  {index}) {RARITY_NAMES_KR[rarity]} · 조각 {shards}개 / {gold}G")
        print(f"  {len(EQUIPMENT_RARITIES) + 1}) 취소")
        rarity_index = prompt_index("> ", len(EQUIPMENT_RARITIES) + 1)
        if rarity_index == len(EQUIPMENT_RARITIES):
            continue
        rarity = EQUIPMENT_RARITIES[rarity_index]
        if not prompt_yes_no(f"{RARITY_NAMES_KR[rarity]} {WEAPON_FAMILIES[family]} 무기를 합성할까요? (y/n)> "):
            continue
        try:
            item, shards, gold = synthesize_weapon(
                party, equipment_inventory, flags, rarity, family,
            )
        except ValueError as error:
            print(error)
        else:
            print(f"합성 성공! {item.display_name} (조각 {shards}개 / {gold}G 사용)")
