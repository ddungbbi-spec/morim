"""
main.py
게임 실행 진입점. 지금은 파티 생성 -> 전투 데모로 구성되어 있습니다.
추후 여기에 맵 이동, 스토리 분기, 여러 전투를 잇는 흐름을 추가하면 됩니다.
"""

from models import Party
from world import build_world
from map import explore
import data
import save
from quests import QuestLog
from input_utils import prompt_index


def print_title():
    print("=" * 40)
    print("   미정의 전설 (가제) - 텍스트 RPG 데모")
    print("=" * 40)


PARTY_MEMBER_NAMES = ["레온", "리제", "셀린"]


def build_starting_party() -> Party:
    print("\n[파티 편성] 각 캐릭터의 직업을 선택하세요.")
    job_keys = list(data.JOB_CREATORS.keys())

    members = []
    for name in PARTY_MEMBER_NAMES:
        print(f"\n{name}의 직업:")
        for i, key in enumerate(job_keys, 1):
            print(f"  {i}) {data.JOB_LABELS[key]}")
        job_key = job_keys[prompt_index("> ", len(job_keys))]
        members.append(data.JOB_CREATORS[job_key](name))

    return Party(members, gold=30)


def start_new_game():
    party = build_starting_party()
    inventory = [data.POTION, data.ETHER]
    equipment_inventory = []  # 장비는 마을 상점에서 구매 (초기 골드 30G)
    game_map = build_world()
    flags = {}
    quest_log = QuestLog()
    return party, inventory, game_map, flags, equipment_inventory, quest_log


def main():
    print_title()

    if save.has_any_save():
        print("\n저장된 게임이 있습니다.")
        print("  1) 이어하기")
        print("  2) 새 게임 시작")
        choice = prompt_index("> ", 2) + 1
        if choice == 1:
            slot = save.prompt_load_slot()
            if slot is not None:
                try:
                    party, inventory, game_map, flags, equipment_inventory, quest_log = save.load_game(save.slot_path(slot))
                    print(f"\n[슬롯 {slot}의 저장된 게임을 불러왔습니다]")
                except (OSError, ValueError) as error:
                    print(f"\n저장 파일을 불러오지 못했습니다: {error}")
                    print("새 게임을 시작합니다.")
                    party, inventory, game_map, flags, equipment_inventory, quest_log = start_new_game()
            else:
                print("\n불러오기를 취소하고 새 게임을 시작합니다.")
                party, inventory, game_map, flags, equipment_inventory, quest_log = start_new_game()
        else:
            party, inventory, game_map, flags, equipment_inventory, quest_log = start_new_game()
    else:
        party, inventory, game_map, flags, equipment_inventory, quest_log = start_new_game()

    print("\n[파티 상태]")
    party.print_status()

    won = explore(game_map, party, inventory, flags, equipment_inventory, quest_log)

    if won:
        print("\n축하합니다! 데모 클리어!")
    else:
        print("\n게임을 종료합니다.")


if __name__ == "__main__":
    main()
