"""마을 대장간의 확정 장비 강화 규칙과 콘솔 메뉴."""

from dataclasses import replace
from typing import List, Tuple

from input_utils import prompt_index, prompt_yes_no
from models import Equipment, Party

MAX_ENHANCEMENT = 5
RARITY_COST_MULTIPLIERS = {
    "common": 1.0, "uncommon": 1.2, "rare": 1.5, "legendary": 2.0,
}


def upgrade_cost(item: Equipment) -> int:
    """다음 강화 단계의 비용을 계산한다."""
    next_level = item.enhancement_level + 1
    base = max(12, item.price // 4)
    multiplier = RARITY_COST_MULTIPLIERS.get(item.rarity, 1.0)
    return max(1, round(base * multiplier * next_level))


def matching_material_indices(
    equipment_inventory: List[Equipment], target_index: int,
) -> List[int]:
    """대상과 이름이 같은 장비를 낮은 강화 단계 순으로 반환한다."""
    if not 0 <= target_index < len(equipment_inventory):
        return []
    target = equipment_inventory[target_index]
    matches = [
        index for index, item in enumerate(equipment_inventory)
        if index != target_index and item.name == target.name
    ]
    return sorted(matches, key=lambda index: equipment_inventory[index].enhancement_level)


def can_upgrade(
    party: Party, equipment_inventory: List[Equipment], target_index: int,
) -> Tuple[bool, str]:
    if not 0 <= target_index < len(equipment_inventory):
        return False, "올바른 강화 장비를 선택하세요."
    target = equipment_inventory[target_index]
    if target.enhancement_level >= MAX_ENHANCEMENT:
        return False, "이미 최대 강화 단계입니다."
    if not matching_material_indices(equipment_inventory, target_index):
        return False, "같은 이름의 장비가 재료로 하나 더 필요합니다."
    cost = upgrade_cost(target)
    if party.gold < cost:
        return False, f"골드가 부족합니다. ({cost}G 필요)"
    return True, ""


def enhance_equipment(
    party: Party, equipment_inventory: List[Equipment], target_index: int,
) -> Tuple[Equipment, int]:
    """골드와 동일 장비 하나를 소비하고 대상 장비를 한 단계 강화한다."""
    allowed, reason = can_upgrade(party, equipment_inventory, target_index)
    if not allowed:
        raise ValueError(reason)

    target = equipment_inventory[target_index]
    material_index = matching_material_indices(equipment_inventory, target_index)[0]
    cost = upgrade_cost(target)
    next_level = target.enhancement_level + 1
    bonuses = {}
    if target.slot == "weapon":
        bonuses["attack_bonus"] = target.attack_bonus + 2
    elif target.slot == "armor":
        bonuses["defense_bonus"] = target.defense_bonus + 1
        bonuses["max_hp_bonus"] = target.max_hp_bonus + 3
    elif target.slot == "accessory":
        bonuses["speed_bonus"] = target.speed_bonus + 1
        bonuses["max_mp_bonus"] = target.max_mp_bonus + 2
    else:
        raise ValueError("강화할 수 없는 장비 슬롯입니다.")

    base_description = target.description.split(" · 강화 +", 1)[0]
    upgraded = replace(
        target, enhancement_level=next_level,
        description=f"{base_description} · 강화 +{next_level}",
        price=target.price + max(1, cost // 2), generated=True, **bonuses,
    )
    party.gold -= cost
    equipment_inventory.pop(material_index)
    if material_index < target_index:
        target_index -= 1
    equipment_inventory[target_index] = upgraded
    return upgraded, cost


def run_blacksmith(party: Party, equipment_inventory: List[Equipment]) -> None:
    """시작 마을에서 사용하는 콘솔 대장간 메뉴."""
    while True:
        print(f"\n[마을 대장간] 보유 골드: {party.gold}G")
        if not equipment_inventory:
            print("  강화할 장비가 없습니다.")
            return
        for index, item in enumerate(equipment_inventory):
            materials = len(matching_material_indices(equipment_inventory, index))
            detail = (
                "최대 강화" if item.enhancement_level >= MAX_ENHANCEMENT
                else f"{upgrade_cost(item)}G / 동일 장비 {materials}개"
            )
            print(f"  {index + 1}) {item.display_name} - {detail}")
        back = len(equipment_inventory) + 1
        print(f"  {back}) 나가기")
        selected = prompt_index("> ", back)
        if selected == back - 1:
            return
        allowed, reason = can_upgrade(party, equipment_inventory, selected)
        if not allowed:
            print(reason)
            continue
        target = equipment_inventory[selected]
        if not prompt_yes_no(
            f"{target.display_name}을(를) {upgrade_cost(target)}G에 강화할까요? (y/n)> "
        ):
            continue
        upgraded, cost = enhance_equipment(party, equipment_inventory, selected)
        print(f"강화 성공! {upgraded.display_name} ({cost}G 사용)")
