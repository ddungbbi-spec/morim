"""
map.py
맵 이동을 담당하는 엔진입니다.
실제 맵 데이터(장소, 연결 관계, 등장 몬스터, 상점 재고)는 world.py 에 정의합니다.
"""

from __future__ import annotations
import random
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

from models import Party, Enemy, Item, Equipment
from combat import Battle
from story import Dialogue
from input_utils import prompt_index, prompt_yes_no
from shop import Shop


@dataclass(frozen=True)
class FlagRequirement:
    """스토리 flag가 기대값일 때만 통과할 수 있는 이동 조건."""

    flag: str
    description: str
    expected: object = True
    failure_message: str = "아직 이 길을 이용할 조건을 갖추지 못했다."
    predicate: Optional[Callable[[dict], bool]] = None

    def is_met(self, flags: dict) -> bool:
        if self.predicate is not None:
            return bool(self.predicate(flags))
        return flags.get(self.flag) == self.expected


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
        shops: Optional[List[Shop]] = None,
        loot_item: Optional[Item] = None,
        loot_equipment: Optional[Equipment] = None,
        locked_exits: Optional[Dict[str, str]] = None,
        flag_requirements: Optional[Dict[str, FlagRequirement]] = None,
        has_inn: bool = False,
    ):
        self.id = loc_id
        self.name = name
        self.description = description
        # exits: {"선택지로 보여줄 문구": "이동할 location id"}
        self.exits = exits or {}
        self.encounter_chance = encounter_chance
        self.encounter_pool = encounter_pool or []
        self.boss = boss              # 보스가 있는 장소면 전투 함수를 넣는다 (최초 처치 후 수동 재도전 가능)
        self.boss_defeated = False
        self.is_ending = is_ending
        self.dialogue = dialogue      # 이 장소에 처음 들어왔을 때 재생할 대화 (1회성)
        self.dialogue_played = False
        legacy_items = shop_items or []
        legacy_equipment = shop_equipment or []
        self.shops = list(shops or [])
        if not self.shops and (legacy_items or legacy_equipment):
            self.shops.append(Shop("상점", legacy_items, legacy_equipment))
        # 이전 코드가 Location의 단일 재고를 읽어도 전체 상품을 볼 수 있게 유지한다.
        self.shop_items = [item for shop in self.shops for item in shop.items]
        self.shop_equipment = [item for shop in self.shops for item in shop.equipment]
        self.loot_item = loot_item            # 보물상자 등에서 얻는 아이템 (1회성)
        self.loot_equipment = loot_equipment  # 보물상자 등에서 얻는 장비 (1회성)
        self.loot_claimed = False
        self.locked_exits = locked_exits or {}  # {"exits의 문구": "필요한 아이템 이름"} - 열쇠 아이템을 소모해서 연다
        self.flag_requirements = flag_requirements or {}  # 대화 선택 등 flags 조건. 충족 전에는 통과 불가
        self.unlocked_labels = set()            # 이미 열어서 더는 열쇠가 필요 없는 문구들 (1회 소모, 이후 영구)
        self.has_inn = has_inn                  # 파티 전체를 완전히 회복할 수 있는 여관

    @property
    def has_shop(self) -> bool:
        return bool(self.shops)

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


def _claim_location_loot(loc: Location, inventory: list, equipment_inventory: list) -> None:
    if not loc.has_loot or loc.loot_claimed or (loc.boss and not loc.boss_defeated):
        return
    print("\n보물을 발견했다!")
    if loc.loot_item:
        inventory.append(loc.loot_item)
        print(f"[{loc.loot_item.name}]을(를) 손에 넣었다!")
    if loc.loot_equipment:
        equipment_inventory.append(loc.loot_equipment)
        print(f"{loc.loot_equipment.display_name}을(를) 손에 넣었다! (장비 관리에서 착용할 수 있다)")
    loc.loot_claimed = True


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
        quest_log.refresh_from_world(game_map, flags)
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
            if loc.id == "echo_vault":
                flags["echo_purified"] = True
            if loc.id == "final_chamber":
                flags["demon_lord_defeated"] = True
            if loc.id == "star_rift":
                from blacksmith import award_star_ore
                print(award_star_ore(flags, inventory))
                from world import star_chapter_epilogue
                for line in star_chapter_epilogue(flags):
                    print(line)
            if loc.id == "void_throne":
                flags["void_observer_defeated"] = True
                from world import astral_chapter_epilogue
                for line in astral_chapter_epilogue(flags):
                    print(line)
            if loc.id == "nameless_sanctum":
                flags["nameless_swordmaster_defeated"] = True
            print(f"\n{loc.name}의 위험이 사라졌다. 계속 진행할 수 있다.")
            if loc.id == "final_chamber":
                _claim_location_loot(loc, inventory, equipment_inventory)
                ending = game_map.locations["ending"]
                if ending.dialogue and not ending.dialogue_played:
                    ending.dialogue.run(flags)
                    ending.dialogue_played = True
                game_map.move_to("village")
                print("\n빛의 마법진이 파티를 시작 마을로 돌려보냈다.")
            continue  # 보스 처치 후 같은 장소를 다시 보여주고 이동 선택으로 넘어감

        # 보물(아이템/장비)이 있는 장소면 1회성으로 획득 (보스가 있다면 처치 후에만 가능)
        _claim_location_loot(loc, inventory, equipment_inventory)

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
        if loc.boss and loc.boss_defeated:
            options.append(("보스에게 다시 도전", "boss_retry", None))
        if loc.id == "village":
            options.append(("의뢰 게시판", "quest_board", None))
            options.append(("전직 교관 · 2차 직업", "advancement", None))
            options.append(("대장간에서 장비 강화", "blacksmith", None))
            options.append(("장비 분해·무기 합성", "crafting", None))
            tower_summit = game_map.locations.get("tower_summit")
            if tower_summit and tower_summit.boss_defeated:
                from world import tower_challenge_tier
                next_tier = max(2, tower_challenge_tier(flags))
                options.append((f"도전의 탑 {next_tier}단계 개방", "tower_retry", None))
        if loc.has_inn:
            options.append(("여관에서 쉬기 (전원 완전 회복)", "inn", None))
        for shop in loc.shops:
            label = f"{shop.name} 이용하기"
            if not shop.is_available(flags):
                label += f" (🔒 {shop.unlock_description})"
            options.append((label, "shop", shop))
        options.append(("게임 저장", "save", None))
        options.append(("저장 후 게임 종료", "save_exit", None))
        options.append(("저장하지 않고 종료", "quit", None))

        if not loc.exits:
            print("\n더 이상 갈 곳이 없다. (막다른 길)")

        print("\n[행동을 선택하세요]")
        for i, (label, action, _) in enumerate(options, 1):
            display = label
            requirement = loc.flag_requirements.get(label) if action == "move" else None
            if requirement and not requirement.is_met(flags):
                display = f"{label} (🔒 {requirement.description})"
            elif action == "move" and label in loc.locked_exits and label not in loc.unlocked_labels:
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
            print("\n" + quest_log.render_journal(flags))
            continue

        if action == "boss_retry":
            print("\n쓰러뜨린 보스의 기운이 다시 모여든다...!")
            if loc.id == "tower_summit":
                from world import (
                    create_scaled_tower_guardian, tower_challenge_tier,
                    tower_clear_count,
                )
                if tower_clear_count(flags) == 0:
                    flags["tower_clear_count"] = 1
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
                print(
                    f"\n도전의 탑 {clear_count}회 클리어! "
                    f"추가 보상 {bonus_gold}G와 {equipment.display_name}을(를) 획득했다."
                )
            print(f"\n{loc.name}의 보스를 다시 쓰러뜨렸다. 다시 이곳에 오면 재도전할 수 있다.")
            if loc.id == "star_rift":
                from blacksmith import award_star_ore
                print(award_star_ore(flags, inventory))
            if loc.id == "final_chamber":
                game_map.move_to("village")
                print("\n빛의 마법진이 파티를 시작 마을로 돌려보냈다.")
            continue

        if action == "quest_board":
            from quests import run_quest_board
            run_quest_board(quest_log, party, inventory, game_map, flags)
            continue

        if action == "advancement":
            from advancement import ADVANCEMENT_LEVEL, advance, options_for
            print(f"\n[전직 교관] Lv.{ADVANCEMENT_LEVEL}부터 2차 직업을 선택할 수 있다.")
            for i, member in enumerate(party.members, 1):
                status = member.job if member.advanced_job_id else (
                    "전직 가능" if member.level >= ADVANCEMENT_LEVEL else f"Lv.{ADVANCEMENT_LEVEL} 필요"
                )
                print(f"  {i}) {member.name} · {member.job} · Lv.{member.level} ({status})")
            print(f"  {len(party.members) + 1}) 돌아가기")
            member_index = prompt_index("> ", len(party.members) + 1)
            if member_index == len(party.members):
                continue
            member = party.members[member_index]
            if member.advanced_job_id or member.level < ADVANCEMENT_LEVEL:
                print("\n아직 전직할 수 없다.")
                continue
            choices = options_for(member)
            for i, job in enumerate(choices, 1):
                print(f"  {i}) {job.name} · {job.description} · [{job.skill.name}]")
            print(f"  {len(choices) + 1}) 돌아가기")
            selection = prompt_index("> ", len(choices) + 1)
            if selection < len(choices):
                job = advance(member, choices[selection].id)
                print(f"\n{member.name}이(가) {job.name}(으)로 전직하고 [{job.skill.name}]을(를) 습득했다!")
            continue

        if action == "blacksmith":
            from blacksmith import run_blacksmith
            run_blacksmith(party, equipment_inventory, inventory, flags)
            continue

        if action == "crafting":
            from crafting import run_crafting
            run_crafting(party, equipment_inventory, flags)
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
            if not payload.is_available(flags):
                print(f"\n{payload.unlock_description} 후에 이용할 수 있다.")
                continue
            discount_rate = payload.active_discount(flags)
            run_shop(
                party, inventory, equipment_inventory,
                payload.items, payload.equipment, shop_name=payload.name,
                discount_rate=discount_rate,
                discount_description=payload.discount_description,
            )
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
            requirement = loc.flag_requirements.get(label)
            if requirement and not requirement.is_met(flags):
                print(f"\n{requirement.failure_message}")
                continue
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
