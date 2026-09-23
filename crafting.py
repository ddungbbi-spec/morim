"""미착용 장비 분해와 무기 계열·등급 지정 합성 규칙."""

from dataclasses import replace
from itertools import combinations
from typing import List, Sequence, Tuple

from input_utils import prompt_index, prompt_yes_no
from equipment import protection_warning
from models import (
    EQUIPMENT_RARITIES, RARITY_NAMES_KR, WEAPON_FAMILIES,
    Equipment, Party,
)


SHARD_FLAG = "equipment_shards"
DISMANTLE_SHARDS = {
    "common": 1, "uncommon": 3, "rare": 8, "epic": 20, "legendary": 50,
}
ENHANCEMENT_DISMANTLE_BONUS = {
    0: 0, 1: 3, 2: 7, 3: 12, 4: 18, 5: 25,
}
SYNTHESIS_RECIPES = {
    "common": (4, 15),
    "uncommon": (10, 35),
    "rare": (24, 80),
    "epic": (55, 180),
    "legendary": (120, 400),
}
REFORGE_COSTS = {
    "rare": (6, 40), "epic": (12, 90), "legendary": (25, 180),
}


def shard_count(flags: dict) -> int:
    value = flags.get(SHARD_FLAG, 0)
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else 0


def dismantle_value(item: Equipment) -> int:
    """등급 기본 조각에 강화 투자량을 반영한 단계별 회수 보너스를 더한다."""
    level = min(5, max(0, item.enhancement_level))
    return DISMANTLE_SHARDS.get(item.rarity, 1) + ENHANCEMENT_DISMANTLE_BONUS[level]


def dismantle_equipment(
    equipment_inventory: List[Equipment], index: int, flags: dict,
) -> Tuple[Equipment, int]:
    if not isinstance(index, int) or isinstance(index, bool) or not 0 <= index < len(equipment_inventory):
        raise ValueError("올바른 분해 장비를 선택하세요.")
    if equipment_inventory[index].locked:
        raise ValueError("잠금 보호된 장비는 분해할 수 없습니다. 장비 관리에서 잠금을 해제하세요.")
    item = equipment_inventory.pop(index)
    gained = dismantle_value(item)
    flags[SHARD_FLAG] = shard_count(flags) + gained
    return item, gained


def bulk_dismantle_reason(item: Equipment) -> str:
    """안전 일괄 분해에서 자동 제외해야 할 이유를 반환한다."""
    if item.locked:
        return "잠금 보호 장비"
    if item.rarity == "legendary":
        return "전설 장비"
    if item.enhancement_level > 0:
        return "강화 장비"
    return ""


def dismantle_equipment_many(
    equipment_inventory: List[Equipment], indices: Sequence[int], flags: dict,
) -> Tuple[List[Equipment], int]:
    """안전 대상 여러 장을 검증 후 한 번에 분해한다.

    모든 항목 검증을 먼저 끝낸 뒤 역순으로 제거하여, 잘못된 요청이 일부만
    처리되는 일을 막는다. 전설·강화·잠금 장비는 단일 분해와 달리 일괄
    처리에서 항상 제외한다.
    """
    if not isinstance(indices, (list, tuple)) or not indices:
        raise ValueError("분해할 장비를 한 개 이상 선택하세요.")
    if any(not isinstance(index, int) or isinstance(index, bool) for index in indices):
        raise ValueError("올바른 분해 장비를 선택하세요.")
    unique = sorted(set(indices))
    if len(unique) != len(indices):
        raise ValueError("같은 장비를 중복 선택할 수 없습니다.")
    if unique[0] < 0 or unique[-1] >= len(equipment_inventory):
        raise ValueError("올바른 분해 장비를 선택하세요.")

    selected = [equipment_inventory[index] for index in unique]
    blocked = [bulk_dismantle_reason(item) for item in selected]
    if any(blocked):
        reason = next(reason for reason in blocked if reason)
        raise ValueError(f"{reason}는 안전 일괄 분해에서 자동 제외됩니다.")

    gained = sum(dismantle_value(item) for item in selected)
    for index in reversed(unique):
        equipment_inventory.pop(index)
    flags[SHARD_FLAG] = shard_count(flags) + gained
    return selected, gained


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


def synthesis_preview(party: Party, rarity: str, family: str) -> dict:
    """합성 결과의 확정 요소와 무작위 능력치 범위를 실제 생성 규칙으로 계산한다."""
    if rarity not in EQUIPMENT_RARITIES:
        raise ValueError("올바른 합성 등급을 선택하세요.")
    if family not in WEAPON_FAMILIES:
        raise ValueError("올바른 무기 계열을 선택하세요.")

    import data
    level = max((member.level for member in party.members), default=1)
    base = data.equipment_base_bonuses(level, "weapon", family)
    option_count = data.RARITY_AFFIX_COUNTS[rarity]
    outcomes = []
    for selected in combinations(data.RANDOM_AFFIXES, option_count):
        values = dict(base)
        for _, affix in selected:
            for field, amount in affix.items():
                values[field] += amount
        outcomes.append(values)
    if not outcomes:
        outcomes = [base]

    labels = {
        "attack_bonus": "공격력", "defense_bonus": "방어력",
        "speed_bonus": "속도", "max_hp_bonus": "최대 HP",
        "max_mp_bonus": "최대 MP", "critical_rate_bonus": "치명타율",
        "evasion_rate_bonus": "회피율", "damage_reduction_bonus": "피해 감소",
    }
    percent_fields = {
        "critical_rate_bonus", "evasion_rate_bonus", "damage_reduction_bonus",
    }
    stat_ranges = []
    for field, label in labels.items():
        minimum = min(values[field] for values in outcomes)
        maximum = max(values[field] for values in outcomes)
        if minimum == maximum == 0:
            continue
        if field in percent_fields:
            minimum, maximum = round(minimum * 100), round(maximum * 100)
            unit = "%"
        else:
            unit = ""
        stat_ranges.append({
            "field": field, "label": label,
            "min": minimum, "max": maximum, "unit": unit,
        })

    compatible_members = [
        {"name": member.name, "job": member.job}
        for member in party.members
        if family in member.allowed_weapon_families
    ]
    return {
        "level": level,
        "rarity": rarity,
        "rarity_name": RARITY_NAMES_KR[rarity],
        "family": family,
        "family_name": WEAPON_FAMILIES[family],
        "option_count": option_count,
        "options_random": option_count > 0,
        "stat_ranges": stat_ranges,
        "compatible_members": compatible_members,
    }


def preview_stat_text(preview: dict) -> str:
    parts = []
    for stat in preview["stat_ranges"]:
        low = f"{stat['min']:+g}{stat['unit']}"
        high = f"{stat['max']:+g}{stat['unit']}"
        value = low if stat["min"] == stat["max"] else f"{low}~{high}"
        parts.append(f"{stat['label']} {value}")
    return " · ".join(parts) or "능력치 보너스 없음"


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


def equipment_affixes(item: Equipment) -> List[str]:
    """생성 장비에 저장된 무작위 옵션 이름을 안전하게 반환한다."""
    if not item.special_effect:
        return []
    return [name for name in item.special_effect.split("/") if name]


def reforge_cost(item: Equipment, locked_affix: str = "") -> Tuple[int, int]:
    if item.rarity not in REFORGE_COSTS:
        raise ValueError("옵션 재련은 희귀 이상 장비만 가능합니다.")
    shards, gold = REFORGE_COSTS[item.rarity]
    multiplier = 2 if locked_affix else 1
    return shards * multiplier, gold * multiplier


def can_reforge(
    party: Party, flags: dict, item: Equipment, locked_affix: str = "",
) -> Tuple[bool, str]:
    """재련 대상·고정 옵션·보유 자원을 실제 소비 전에 검증한다."""
    import data

    affix_names = equipment_affixes(item)
    known = {name for name, _ in data.RANDOM_AFFIXES}
    if not item.generated or item.rarity not in REFORGE_COSTS:
        return False, "옵션 재련은 무작위 옵션이 있는 희귀 이상 생성 장비만 가능합니다."
    if len(affix_names) != data.RARITY_AFFIX_COUNTS[item.rarity] or any(
        name not in known for name in affix_names
    ):
        return False, "이 장비의 고유 효과는 옵션 재련으로 변경할 수 없습니다."
    if not isinstance(locked_affix, str) or (locked_affix and locked_affix not in affix_names):
        return False, "고정할 옵션을 올바르게 선택하세요."
    shards, gold = reforge_cost(item, locked_affix)
    if shard_count(flags) < shards:
        return False, f"장비 조각이 부족합니다. ({shards}개 필요)"
    if party.gold < gold:
        return False, f"골드가 부족합니다. ({gold}G 필요)"
    return True, ""


def preview_reforge(item: Equipment, locked_affix: str = "") -> Equipment:
    """자원을 소비하지 않고 옵션 하나의 고정을 반영한 새 장비를 만든다."""
    import data

    current_names = equipment_affixes(item)
    known_affixes = dict(data.RANDOM_AFFIXES)
    if not item.generated or item.rarity not in REFORGE_COSTS:
        raise ValueError("옵션 재련은 무작위 옵션이 있는 희귀 이상 생성 장비만 가능합니다.")
    if len(current_names) != data.RARITY_AFFIX_COUNTS[item.rarity] or any(
        name not in known_affixes for name in current_names
    ):
        raise ValueError("이 장비의 고유 효과는 옵션 재련으로 변경할 수 없습니다.")
    if not isinstance(locked_affix, str) or (locked_affix and locked_affix not in current_names):
        raise ValueError("고정할 옵션을 올바르게 선택하세요.")

    fixed = [locked_affix] if locked_affix else []
    candidates = [name for name in known_affixes if name not in fixed]
    reroll_count = len(current_names) - len(fixed)
    new_names = fixed + data.random.sample(candidates, k=reroll_count)
    if set(new_names) == set(current_names):
        alternatives = [
            list(choice) for choice in combinations(candidates, reroll_count)
            if set(fixed + list(choice)) != set(current_names)
        ]
        if alternatives:
            new_names = fixed + data.random.choice(alternatives)

    bonuses = {
        "attack_bonus": item.attack_bonus,
        "defense_bonus": item.defense_bonus,
        "speed_bonus": item.speed_bonus,
        "max_hp_bonus": item.max_hp_bonus,
        "max_mp_bonus": item.max_mp_bonus,
        "critical_rate_bonus": item.critical_rate_bonus,
        "evasion_rate_bonus": item.evasion_rate_bonus,
        "damage_reduction_bonus": item.damage_reduction_bonus,
    }
    for name in current_names:
        for field, amount in known_affixes[name].items():
            bonuses[field] -= amount
    for name in new_names:
        for field, amount in known_affixes[name].items():
            bonuses[field] += amount

    base_name = item.name.split(" · ", 1)[0]
    return replace(
        item,
        name=f"{base_name} · {'/'.join(new_names)}",
        special_effect="/".join(new_names),
        **bonuses,
    )


def apply_reforge(
    party: Party, equipment_inventory: List[Equipment], flags: dict,
    index: int, result: Equipment, locked_affix: str = "",
) -> Tuple[Equipment, int, int]:
    if not isinstance(index, int) or isinstance(index, bool) or not 0 <= index < len(equipment_inventory):
        raise ValueError("올바른 재련 장비를 선택하세요.")
    original = equipment_inventory[index]
    allowed, reason = can_reforge(party, flags, original, locked_affix)
    if not allowed:
        raise ValueError(reason)
    if not isinstance(result, Equipment) or result.rarity != original.rarity:
        raise ValueError("재련 결과가 변경되었습니다. 다시 미리보기를 확인하세요.")
    shards, gold = reforge_cost(original, locked_affix)
    flags[SHARD_FLAG] = shard_count(flags) - shards
    party.gold -= gold
    equipment_inventory[index] = result
    return result, shards, gold


def run_crafting(
    party: Party, equipment_inventory: List[Equipment], flags: dict,
) -> None:
    while True:
        print(f"\n[분해·합성·재련 공방] 장비 조각 {shard_count(flags)}개 / {party.gold}G")
        print("  1) 장비 분해")
        print("  2) 무기 합성")
        print("  3) 장비 옵션 재련")
        print("  4) 돌아가기")
        action = prompt_index("> ", 4)
        if action == 3:
            return
        if action == 0:
            if not equipment_inventory:
                print("분해할 미착용 장비가 없습니다.")
                continue
            available = [item for item in equipment_inventory if not item.locked]
            if not available:
                print("분해할 수 있는 장비가 없습니다. 잠금 장비는 보호됩니다.")
                continue
            for index, item in enumerate(available, 1):
                print(f"  {index}) {item.display_name} → 조각 {dismantle_value(item)}개")
            print(f"  {len(available) + 1}) 취소")
            selected = prompt_index("> ", len(available) + 1)
            if selected == len(available):
                continue
            item = available[selected]
            warning = protection_warning(item)
            if warning:
                print(f"주의: {warning}")
            if prompt_yes_no(f"{item.display_name}을(를) 분해할까요? (y/n)> "):
                removed, gained = dismantle_equipment(equipment_inventory, equipment_inventory.index(item), flags)
                print(f"{removed.display_name} 분해 완료! 장비 조각 {gained}개를 얻었습니다.")
            continue

        if action == 2:
            available = [
                item for item in equipment_inventory
                if item.generated and item.rarity in REFORGE_COSTS
            ]
            if not available:
                print("재련할 수 있는 희귀 이상 미착용 장비가 없습니다.")
                continue
            for index, item in enumerate(available, 1):
                shards, gold = reforge_cost(item)
                print(
                    f"  {index}) {item.display_name} · {item.special_effect} "
                    f"→ 조각 {shards}개 / {gold}G"
                )
            print(f"  {len(available) + 1}) 취소")
            selected = prompt_index("> ", len(available) + 1)
            if selected == len(available):
                continue
            item = available[selected]
            affixes = equipment_affixes(item)
            print("  1) 옵션 고정 없음")
            for index, name in enumerate(affixes, 2):
                print(f"  {index}) {name} 고정 (비용 2배)")
            print(f"  {len(affixes) + 2}) 취소")
            lock_choice = prompt_index("> ", len(affixes) + 2)
            if lock_choice == len(affixes) + 1:
                continue
            locked_affix = "" if lock_choice == 0 else affixes[lock_choice - 1]
            allowed, reason = can_reforge(party, flags, item, locked_affix)
            if not allowed:
                print(reason)
                continue
            result = preview_reforge(item, locked_affix)
            shards, gold = reforge_cost(item, locked_affix)
            print(f"  변경 전: {item.special_effect} / {item.display_description}")
            print(f"  변경 후: {result.special_effect} / {result.display_description}")
            if not prompt_yes_no(
                f"장비 조각 {shards}개와 {gold}G를 사용해 이 결과를 확정할까요? (y/n)> "
            ):
                continue
            index = equipment_inventory.index(item)
            applied, used_shards, used_gold = apply_reforge(
                party, equipment_inventory, flags, index, result, locked_affix,
            )
            print(
                f"재련 완료! {applied.special_effect} "
                f"(조각 {used_shards}개 / {used_gold}G 사용)"
            )
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
        preview = synthesis_preview(party, rarity, family)
        compatible = ", ".join(
            f"{member['name']}({member['job']})"
            for member in preview["compatible_members"]
        ) or "현재 파티에 없음"
        option_text = (
            f"무작위 부가 옵션 {preview['option_count']}개"
            if preview["options_random"] else "부가 옵션 없음"
        )
        print(f"  예상 결과: Lv.{preview['level']} {preview['rarity_name']} {preview['family_name']}")
        print(f"  능력치 범위: {preview_stat_text(preview)}")
        print(f"  {option_text} / 장착 가능: {compatible}")
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
