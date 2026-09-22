"""
equipment.py
파티원의 장비(무기/방어구/장신구)를 착용/해제하는 메뉴 UI입니다.
맵 탐험 메뉴("장비 관리")에서 호출됩니다.
"""

from typing import List

from models import PlayerCharacter, Party, Equipment, EQUIPMENT_SLOTS, WEAPON_FAMILIES
from input_utils import prompt_index

SLOT_NAMES_KR = {"weapon": "무기", "armor": "방어구", "accessory": "장신구"}


def protection_warning(item: Equipment) -> str:
    """잠금 해제 후에도 중요한 장비를 처분하기 전에 보여 줄 경고."""
    import data

    if item.name in data.PROTECTED_EQUIPMENT_NAMES:
        return "보스·탐험 전용 장비입니다. 다시 얻기 어려울 수 있습니다."
    if item.enhancement_level > 0:
        return f"+{item.enhancement_level} 강화 장비입니다."
    if item.rarity == "legendary":
        return "전설 등급 장비입니다."
    return ""


def manage_equipment(party: Party, equipment_inventory: List[Equipment]) -> None:
    """파티원을 선택해서 장비를 착용/해제하는 메뉴 루프."""
    while True:
        print("\n[장비 관리] - 파티원을 선택하세요")
        for i, member in enumerate(party.members, 1):
            worn = ", ".join(
                f"{SLOT_NAMES_KR[slot]}:{item.display_name if item else '없음'}"
                for slot, item in member.equipment.items()
            )
            print(f"  {i}) {member.name} ({member.job})  [{worn}]")
        protection_option = len(party.members) + 1
        back_option = protection_option + 1
        print(f"  {protection_option}) 보유 장비 잠금 설정")
        print(f"  {back_option}) 나가기")

        idx = prompt_index("> ", back_option)

        if idx == back_option - 1:
            return
        if idx == protection_option - 1:
            _manage_inventory_protection(equipment_inventory)
            continue
        if not (0 <= idx < len(party.members)):
            print("잘못된 입력입니다.")
            continue

        _manage_member_equipment(party.members[idx], equipment_inventory)


def _manage_inventory_protection(equipment_inventory: List[Equipment]) -> None:
    """미착용 장비의 잠금을 켜거나 끈다. 잠금 장비는 판매·분해·강화 재료에서 제외된다."""
    from dataclasses import replace

    while True:
        print("\n[장비 잠금 설정] - 잠금 장비는 판매·분해·강화 재료로 사용할 수 없습니다.")
        if not equipment_inventory:
            print("  (보유한 장비가 없습니다)")
            return
        for index, item in enumerate(equipment_inventory, 1):
            state = "🔒 잠금" if item.locked else "잠금 해제"
            print(f"  {index}) {item.display_name} - {state}")
        back = len(equipment_inventory) + 1
        print(f"  {back}) 뒤로 가기")
        selected = prompt_index("> ", back)
        if selected == back - 1:
            return
        item = equipment_inventory[selected]
        equipment_inventory[selected] = replace(item, locked=not item.locked)
        print(f"{item.display_name}: {'잠금 보호' if not item.locked else '잠금 해제'}했습니다.")


def _manage_member_equipment(member: PlayerCharacter, equipment_inventory: List[Equipment]) -> None:
    while True:
        print(f"\n--- {member.name}의 장비 ---")
        allowed = " · ".join(WEAPON_FAMILIES[item] for item in member.allowed_weapon_families)
        print(f"  사용 가능 무기 계열: {allowed or '없음'}")
        for slot in EQUIPMENT_SLOTS:
            current = member.equipment.get(slot)
            print(f"  {SLOT_NAMES_KR[slot]}: {current.display_name if current else '없음'}")

        print("\n[보유 장비함]")
        if not equipment_inventory:
            print("  (보유한 장비가 없습니다)")
        for i, item in enumerate(equipment_inventory, 1):
            effect = f" / {item.special_effect}" if item.special_effect else ""
            lock = " 🔒" if item.locked else ""
            print(f"  {i}) [{SLOT_NAMES_KR[item.slot]}] {item.display_name}{lock} - {item.display_description}{effect}")
        back_option = len(equipment_inventory) + 1
        print(f"  {back_option}) 뒤로 가기")

        idx = prompt_index("> ", back_option)

        if idx == back_option - 1:
            return
        if not (0 <= idx < len(equipment_inventory)):
            print("잘못된 입력입니다.")
            continue

        item = equipment_inventory[idx]
        try:
            previous = member.equip(item)
        except ValueError as error:
            print(error)
            continue
        equipment_inventory.pop(idx)
        print(f"{member.name}이(가) {item.display_name}을(를) 착용했다!")
        if previous:
            equipment_inventory.append(previous)
            print(f"({previous.name}을(를) 해제해서 보유 장비함에 넣었다.)")
