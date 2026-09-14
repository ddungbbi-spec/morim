"""
map.py
맵 이동을 담당하는 엔진입니다.
실제 맵 데이터(장소, 연결 관계, 등장 몬스터, 상점 재고)는 world.py 에 정의합니다.
"""

from __future__ import annotations
import random
from typing import Callable, Dict, List, Optional

from models import Party, Enemy, Item, Equipment
from combat import Battle
from story import Dialogue
from input_utils import prompt_index, prompt_yes_no


class Location:
    """맵 위의 한 장소(방/지역)"""

    def __init__(
        self,
        loc_id: str,
        name: str,
        description: str,
        exits: Optional[Dict[str, str]] = None,
        encounter_chance: float = 0.0,
        encounter_pool: Optional[List[Callable[[], List[Enemy]]]] = None,
        boss: Optional[Callable[[], List[Enemy]]] = None,
        is_ending: bool = False,
        dialogue: Optional[Dialogue] = None,
        shop_items: Optional[List[Item]] = None,
        shop_equipment: Optional[List[Equipment]] = None,
        loot_item: Optional[Item] = None,
        loot_equipment: Optional[Equipment] = None,
        locked_exits: Optional[Dict[str, str]] = None,
        has_inn: bool = False,
    ):
        self.id = loc_id
        self.name = name
        self.description = description
        # exits: {"선택지로 보여줄 문구": "이동할 location id"}
        self.exits = exits or {}
        self.encounter_chance = encounter_chance
        self.encounter_pool = encounter_pool or []
        self.boss = boss              # 보스가 있는 장소면 전투 함수를 넣는다 (1회성, boss 처치 후에만 loot 획득 가능)
        self.boss_defeated = False
        self.is_ending = is_ending
        self.dialogue = dialogue      # 이 장소에 처음 들어왔을 때 재생할 대화 (1회성)
        self.dialogue_played = False
        self.shop_items = shop_items or []          # 이 장소에 상점이 있다면 파는 아이템 목록
        self.shop_equipment = shop_equipment or []  # 이 장소에 상점이 있다면 파는 장비 목록
        self.loot_item = loot_item            # 보물상자 등에서 얻는 아이템 (1회성)
        self.loot_equipment = loot_equipment  # 보물상자 등에서 얻는 장비 (1회성)
        self.loot_claimed = False
        self.locked_exits = locked_exits or {}  # {"exits의 문구": "필요한 아이템 이름"} - 열쇠 아이템을 소모해서 연다
        self.unlocked_labels = set()            # 이미 열어서 더는 열쇠가 필요 없는 문구들 (1회 소모, 이후 영구)
        self.has_inn = has_inn                  # 파티 전체를 완전히 회복할 수 있는 여관

    @property
    def has_shop(self) -> bool:
        return bool(self.shop_items or self.shop_equipment)

    @property
    def has_loot(self) -> bool:
        return bool(self.loot_item or self.loot_equipment)


class GameMap:
    """장소들의 모음과 현재 위치를 관리"""

    def __init__(self, locations: List[Location], start_id: str):
        self.locations: Dict[str, Location] = {loc.id: loc for loc in locations}
        self.current_id = start_id
        self.visited = {start_id}  # 지도 보기에서 이미 가본 곳만 보여주기 위한 기록

    @property
    def current(self) -> Location:
        return self.locations[self.current_id]

    def move_to(self, target_id: str):
        self.current_id = target_id
        self.visited.add(target_id)

    def render_overview(self) -> str:
        """지금까지 가본 장소 목록을 보여줍니다 (미발견 장소는 표시하지 않음)."""
        lines = ["[지금까지 발견한 장소]"]
        for loc_id, loc in self.locations.items():
            if loc_id not in self.visited:
                continue
            marker = "  ← 현재 위치" if loc_id == self.current_id else ""
            lines.append(f"  - {loc.name}{marker}")
        return "\n".join(lines)


def explore(
    game_map: GameMap,
    party: Party,
    inventory: list,
    flags: Optional[dict] = None,
    equipment_inventory: Optional[list] = None,
    quest_log=None,
) -> bool:
    """
    맵 탐험 메인 루프.
    flags는 스토리 선택 결과 등을 기억해두는 dict입니다 (없으면 새로 만듭니다).
    equipment_inventory는 아직 착용하지 않은 장비들의 목록입니다.
    파티가 전멸하면 False, 엔딩 지점에 도달하면 True를 반환합니다.
    """
    if flags is None:
        flags = {}
    if equipment_inventory is None:
        equipment_inventory = []
    if quest_log is None:
        from quests import QuestLog
        quest_log = QuestLog()

    while True:
        loc = game_map.current
        quest_log.sync_story_flags(flags)
        quest_log.refresh_from_world(game_map)
        print(f"\n=== {loc.name} ===")
        print(loc.description)

        # 이 장소에 처음 들어왔다면 대화 이벤트 재생 (1회만)
        if loc.dialogue and not loc.dialogue_played:
            loc.dialogue.run(flags)
            loc.dialogue_played = True
            quest_log.sync_story_flags(flags)

        # 봉인의 힘을 받아들인 선택을 최종 전투의 실제 능력치에 반영 (1회만)
        if (
            loc.id == "final_chamber"
            and flags.get("embraced_power")
            and not flags.get("seal_power_applied")
        ):
            for member in party.members:
                member.max_hp += 6
                member.attack += 2
                member.defense += 1
                member.hp = min(member.effective_max_hp, member.hp + 6)
            flags["seal_power_applied"] = True
            print("\n봉인의 힘이 파티에 깃들었다! 최대 HP +6, 공격력 +2, 방어력 +1")

        # 보스가 있는 장소면 진입 시 자동으로 전투 발생 (1회만)
        if loc.boss and not loc.boss_defeated:
            print("\n강력한 기운이 느껴진다...!")
            if loc.id == "tower_summit":
                from world import create_scaled_tower_guardian, tower_challenge_tier
                enemies = [create_scaled_tower_guardian(flags)]
                print(f"도전 단계: {tower_challenge_tier(flags)}")
            else:
                enemies = loc.boss()
            won = Battle(party, enemies, inventory, equipment_inventory).run()
            if not won:
                return False
            if loc.id == "tower_summit":
                from world import complete_tower_challenge
                clear_count, bonus_gold, equipment = complete_tower_challenge(
                    flags, party, equipment_inventory
                )
                if clear_count == 1:
                    print("\n도전의 탑을 최초로 정복했다!")
                else:
                    print(
                        f"\n도전의 탑 {clear_count}회 클리어! "
                        f"추가 보상 {bonus_gold}G와 {equipment.display_name}을(를) 획득했다."
                    )
            loc.boss_defeated = True
            print(f"\n{loc.name}의 위험이 사라졌다. 계속 진행할 수 있다.")
            continue  # 보스 처치 후 같은 장소를 다시 보여주고 이동 선택으로 넘어감

        # 보물(아이템/장비)이 있는 장소면 1회성으로 획득 (보스가 있다면 처치 후에만 가능)
        if loc.has_loot and not loc.loot_claimed and (not loc.boss or loc.boss_defeated):
            print("\n보물을 발견했다!")
            if loc.loot_item:
                inventory.append(loc.loot_item)
                print(f"[{loc.loot_item.name}]을(를) 손에 넣었다!")
            if loc.loot_equipment:
                equipment_inventory.append(loc.loot_equipment)
                print(f"{loc.loot_equipment.display_name}을(를) 손에 넣었다! (장비 관리에서 착용할 수 있다)")
            loc.loot_claimed = True

        if loc.is_ending:
            print("\n--- 이야기는 여기서 계속됩니다 (데모 종료 지점) ---")
            return True

        # ---- 이번 화면에서 고를 수 있는 선택지 구성 ----
        # 각 항목: (화면에 보여줄 문구, 행동 종류, 부가 데이터)
        options: List[tuple] = []
        for label, target_id in loc.exits.items():
            options.append((label, "move", target_id))
        options.append(("파티 상태 확인", "status", None))
        options.append(("장비 관리", "equip", None))
        options.append(("지도 보기", "map", None))
        options.append(("퀘스트 일지", "quests", None))
        if loc.id == "village":
            options.append(("의뢰 게시판", "quest_board", None))
            tower_summit = game_map.locations.get("tower_summit")
            if tower_summit and tower_summit.boss_defeated:
                from world import tower_challenge_tier
                next_tier = max(2, tower_challenge_tier(flags))
                options.append((f"도전의 탑 {next_tier}단계 개방", "tower_retry", None))
        if loc.has_inn:
            options.append(("여관에서 쉬기 (전원 완전 회복)", "inn", None))
        if loc.has_shop:
            options.append(("상점 이용하기", "shop", None))
        options.append(("게임 저장", "save", None))
        options.append(("저장 후 게임 종료", "save_exit", None))
        options.append(("저장하지 않고 종료", "quit", None))

        if not loc.exits:
            print("\n더 이상 갈 곳이 없다. (막다른 길)")

        print("\n[행동을 선택하세요]")
        for i, (label, action, _) in enumerate(options, 1):
            display = label
            if action == "move" and label in loc.locked_exits and label not in loc.unlocked_labels:
                display = f"{label} (🔒 {loc.locked_exits[label]} 필요)"
            print(f"  {i}) {display}")

        idx = prompt_index("> ", len(options))

        label, action, payload = options[idx]

        if action == "status":
            party.print_status()
            continue

        if action == "equip":
            from equipment import manage_equipment  # map.py <-> equipment.py 순환 참조 방지용 지연 import
            manage_equipment(party, equipment_inventory)
            continue

        if action == "map":
            print("\n" + game_map.render_overview())
            continue

        if action == "quests":
            print("\n" + quest_log.render_journal())
            continue

        if action == "quest_board":
            from quests import run_quest_board
            run_quest_board(quest_log, party, inventory, game_map)
            continue

        if action == "inn":
            party.full_restore()
            print("\n여관에서 충분히 쉬었다. 파티 전원의 HP·MP와 상태이상이 모두 회복되었다!")
            continue

        if action == "tower_retry":
            from world import reset_tower_challenge
            if reset_tower_challenge(game_map, flags):
                print("\n탑의 수호자가 더 강한 모습으로 부활했다. 마을 입구에서 다시 도전할 수 있다!")
            else:
                print("\n현재 진행 중인 탑 도전을 먼저 완료해야 한다.")
            continue

        if action == "shop":
            from shop import run_shop  # map.py <-> shop.py 순환 참조 방지용 지연 import
            run_shop(party, inventory, equipment_inventory, loc.shop_items, loc.shop_equipment, shop_name=loc.name)
            continue

        if action == "save":
            from save import save_game, prompt_save_slot, slot_path  # map.py <-> save.py 순환 참조 방지용 지연 import
            slot = prompt_save_slot()
            if slot is None:
                print("저장을 취소했습니다.")
            else:
                save_game(
                    party, inventory, game_map, flags, equipment_inventory,
                    path=slot_path(slot), quest_log=quest_log,
                )
                print(f"슬롯 {slot}에 저장했습니다.")
            continue

        if action == "save_exit":
            from save import save_game, prompt_save_slot, slot_path
            slot = prompt_save_slot()
            if slot is None:
                print("저장 후 종료를 취소했습니다.")
                continue
            save_game(
                party, inventory, game_map, flags, equipment_inventory,
                path=slot_path(slot), quest_log=quest_log,
            )
            print(f"슬롯 {slot}에 저장했습니다. 게임을 종료합니다.")
            return False

        if action == "quit":
            if prompt_yes_no("저장하지 않고 종료할까요? (y/n)> "):
                return False
            continue

        if action == "move":
            if label in loc.locked_exits and label not in loc.unlocked_labels:
                required_item_name = loc.locked_exits[label]
                owned_key = next((it for it in inventory if it.name == required_item_name), None)
                if owned_key is None:
                    print(f"\n문이 잠겨 있다. [{required_item_name}]이(가) 필요할 것 같다.")
                    continue
                inventory.remove(owned_key)
                loc.unlocked_labels.add(label)
                print(f"\n[{required_item_name}]을(를) 사용해 문을 열었다!")

            game_map.move_to(payload)
            new_loc = game_map.current

            # 새 장소로 이동했을 때 랜덤 인카운터 판정 (보스/엔딩 장소는 위에서 별도 처리)
            if new_loc.encounter_pool and random.random() < new_loc.encounter_chance:
                print("\n몬스터가 나타났다!")
                enemies = random.choice(new_loc.encounter_pool)()
                won = Battle(party, enemies, inventory, equipment_inventory).run()
                if not won:
                    return False
