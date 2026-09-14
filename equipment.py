"""
equipment.py
파티원의 장비(무기/방어구/장신구)를 착용/해제하는 메뉴 UI입니다.
맵 탐험 메뉴("장비 관리")에서 호출됩니다.
"""

from typing import List

from models import PlayerCharacter, Party, Equipment, EQUIPMENT_SLOTS
from input_utils import prompt_index

SLOT_NAMES_KR = {"weapon": "무기", "armor": "방어구", "accessory": "장신구"}


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
        back_option = len(party.members) + 1
        print(f"  {back_option}) 나가기")

        idx = prompt_index("> ", back_option)

        if idx == back_option - 1:
            return
        if not (0 <= idx < len(party.members)):
            print("잘못된 입력입니다.")
            continue

        _manage_member_equipment(party.members[idx], equipment_inventory)


def _manage_member_equipment(member: PlayerCharacter, equipment_inventory: List[Equipment]) -> None:
    while True:
        print(f"\n--- {member.name}의 장비 ---")
        for slot in EQUIPMENT_SLOTS:
            current = member.equipment.get(slot)
            print(f"  {SLOT_NAMES_KR[slot]}: {current.display_name if current else '없음'}")

        print("\n[보유 장비함]")
        if not equipment_inventory:
            print("  (보유한 장비가 없습니다)")
        for i, item in enumerate(equipment_inventory, 1):
            effect = f" / {item.special_effect}" if item.special_effect else ""
            print(f"  {i}) [{SLOT_NAMES_KR[item.slot]}] {item.display_name} - {item.description}{effect}")
        back_option = len(equipment_inventory) + 1
        print(f"  {back_option}) 뒤로 가기")

        idx = prompt_index("> ", back_option)

        if idx == back_option - 1:
            return
        if not (0 <= idx < len(equipment_inventory)):
            print("잘못된 입력입니다.")
            continue

        item = equipment_inventory.pop(idx)
        previous = member.equip(item)
        print(f"{member.name}이(가) {item.display_name}을(를) 착용했다!")
        if previous:
            equipment_inventory.append(previous)
            print(f"({previous.name}을(를) 해제해서 보유 장비함에 넣었다.)")
