"""외부 라이브러리 없이 실행되는 미정의 전설 웹 플레이 시제품."""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import random
import secrets
import threading
import time
import webbrowser
from http.cookies import CookieError, SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable, Dict, List, Optional

import data
import save as game_save
from blacksmith import (
    MAX_ENHANCEMENT, can_upgrade, enhance_equipment,
    matching_material_indices, upgrade_cost,
)
from combat import _describe_skill_result
from equipment import SLOT_NAMES_KR
from models import Enemy, Item, Party, PlayerCharacter, Skill
from quests import QuestLog, QUESTS
from shop import SELL_RATIO
from world import (
    build_world, complete_tower_challenge, create_scaled_tower_guardian,
    reset_tower_challenge, tower_challenge_tier, tower_clear_count,
)


WEB_ROOT = Path(__file__).with_name("web_ui")
mimetypes.add_type("application/manifest+json", ".webmanifest")
BOSS_JOBS = {"미니보스", "보스", "최종보스"}
DEFAULT_PARTY_SETUP = [
    {"name": "레온", "job": "warrior"},
    {"name": "리제", "job": "mage"},
    {"name": "셀린", "job": "healer"},
]

ENCOUNTERS: Dict[str, dict] = {
    "forest": {
        "name": "숲 입구 정찰",
        "description": "슬라임과 야생 늑대를 상대하는 기본 전투",
        "factory": lambda: [data.create_slime(), data.create_wild_wolf()],
    },
    "deep_forest": {
        "name": "깊은 숲 토벌",
        "description": "고블린과 독거미가 함께 등장하는 상태이상 전투",
        "factory": lambda: [data.create_goblin(), data.create_poison_spider()],
    },
    "dark_knight": {
        "name": "다크 나이트 결전",
        "description": "도주할 수 없는 보스 패턴 체험",
        "factory": lambda: [data.create_dark_knight()],
    },
}


class WebGame:
    """브라우저 요청 한 번에 행동 하나를 처리하는 전투 세션."""

    def __init__(self, save_dir: Optional[Path] = None):
        self.save_dir = os.fspath(save_dir) if save_dir is not None else None
        self.reset()

    def reset(self) -> None:
        self.party = Party([])
        self.inventory: List[Item] = []
        self.equipment_inventory = []
        self.game_map = build_world()
        self.flags = {}
        self.quest_log = QuestLog()
        self.enemies: List[Enemy] = []
        self.phase = "setup"
        self.result_message = "원정대의 이름과 직업을 선택하세요."
        self.logs = ["새 게임 준비 중입니다."]
        self.turn = 0
        self._order = []
        self._cursor = 0
        self.current_actor: Optional[PlayerCharacter] = None
        self._rewarded = False
        self.battle_context = ""
        self.dialogue = None
        self.dialogue_node_id = None
        self.dialogue_lines: List[str] = []

    def configure_party(self, members) -> dict:
        if self.phase != "setup":
            return self._error("새 게임 준비 화면에서만 파티를 편성할 수 있습니다.")
        if not isinstance(members, list) or len(members) != 3:
            return self._error("파티원 3명의 정보를 입력하세요.")
        normalized = []
        for member in members:
            if not isinstance(member, dict):
                return self._error("파티원 정보 형식이 올바르지 않습니다.")
            raw_name = member.get("name")
            if not isinstance(raw_name, str):
                return self._error("이름은 문자로 입력하세요.")
            name = raw_name.strip()
            job = member.get("job")
            if not name or len(name) > 12 or not name.isprintable():
                return self._error("이름은 1~12자의 표시 가능한 문자로 입력하세요.")
            if job not in data.JOB_CREATORS:
                return self._error("올바른 직업을 선택하세요.")
            normalized.append((name, job))
        names = [name for name, _ in normalized]
        if len(set(names)) != len(names):
            return self._error("파티원 이름은 서로 달라야 합니다.")

        self.party = Party(
            [data.JOB_CREATORS[job](name) for name, job in normalized], gold=30
        )
        self.inventory = [data.POTION, data.POTION, data.ETHER]
        self.equipment_inventory = []
        self.game_map = build_world()
        self.flags = {}
        self.quest_log = QuestLog()
        self.enemies = []
        self.logs = ["새 원정대가 모험을 시작했습니다."]
        self.result_message = "새로운 모험이 시작됩니다."
        self.turn = 0
        self.current_actor = None
        self.battle_context = ""
        self.dialogue = None
        self.dialogue_node_id = None
        self.dialogue_lines = []
        self.phase = "explore"
        self._enter_current_location()
        return {"ok": True, "state": self.state()}

    def move(self, exit_label: str) -> dict:
        if self.phase != "explore":
            return self._error("지금은 이동할 수 없습니다.")
        location = self.game_map.current
        if exit_label not in location.exits:
            return self._error("이동할 길을 찾을 수 없습니다.")

        if exit_label in location.locked_exits and exit_label not in location.unlocked_labels:
            required_name = location.locked_exits[exit_label]
            key = next((item for item in self.inventory if item.name == required_name), None)
            if key is None:
                return self._error(f"문이 잠겨 있습니다. [{required_name}]이(가) 필요합니다.")
            self.inventory.remove(key)
            location.unlocked_labels.add(exit_label)
            self._log(f"[{required_name}]을(를) 사용해 문을 열었습니다.")

        self.game_map.move_to(location.exits[exit_label])
        arrived = self.game_map.current
        self._log(f"{arrived.name}에 도착했습니다.")
        if arrived.encounter_pool and random.random() < arrived.encounter_chance:
            enemies = random.choice(arrived.encounter_pool)()
            self._begin_battle(enemies, "random", f"{arrived.name}의 습격")
        else:
            self._enter_current_location()
        return {"ok": True, "state": self.state()}

    def shop_action(self, operation: str, index) -> dict:
        if self.phase != "explore" or not self.game_map.current.has_shop:
            return self._error("현재 장소에서는 상점을 이용할 수 없습니다.")
        location = self.game_map.current
        try:
            if operation == "buy_item":
                item = location.shop_items[self._index(index, len(location.shop_items), "상품")]
                if self.party.gold < item.price:
                    raise ValueError("골드가 부족합니다.")
                self.party.gold -= item.price
                self.inventory.append(item)
                self._log(f"{item.name}을(를) {item.price}G에 구매했습니다.")
            elif operation == "buy_equipment":
                equipment = location.shop_equipment[
                    self._index(index, len(location.shop_equipment), "상품")
                ]
                if self.party.gold < equipment.price:
                    raise ValueError("골드가 부족합니다.")
                self.party.gold -= equipment.price
                self.equipment_inventory.append(equipment)
                self._log(f"{equipment.display_name}을(를) {equipment.price}G에 구매했습니다.")
            elif operation == "sell_item":
                sellable = [item for item in self.inventory if item.sellable]
                item = sellable[self._index(index, len(sellable), "판매 아이템")]
                price = int(item.price * SELL_RATIO)
                self.inventory.remove(item)
                self.party.gold += price
                self._log(f"{item.name}을(를) 판매해 {price}G를 받았습니다.")
            elif operation == "sell_equipment":
                equipment = self.equipment_inventory[
                    self._index(index, len(self.equipment_inventory), "판매 장비")
                ]
                price = int(equipment.price * SELL_RATIO)
                self.equipment_inventory.remove(equipment)
                self.party.gold += price
                self._log(f"{equipment.display_name}을(를) 판매해 {price}G를 받았습니다.")
            else:
                return self._error("지원하지 않는 상점 행동입니다.")
        except (IndexError, TypeError, ValueError) as error:
            return self._error(str(error))
        return {"ok": True, "state": self.state()}

    def inn_action(self) -> dict:
        if self.phase != "explore" or not self.game_map.current.has_inn:
            return self._error("여관은 시작 마을에서 이용할 수 있습니다.")
        self.party.full_restore()
        self._log("여관에서 쉬었습니다. 파티 전원의 HP·MP와 상태이상이 모두 회복되었습니다.")
        return {"ok": True, "state": self.state()}

    def tower_action(self, operation: str) -> dict:
        if self.phase != "explore" or self.game_map.current_id != "village":
            return self._error("탑 재도전은 시작 마을에서 준비할 수 있습니다.")
        if operation != "reset":
            return self._error("지원하지 않는 탑 행동입니다.")
        if not reset_tower_challenge(self.game_map, self.flags):
            return self._error("현재 진행 중인 탑 도전을 먼저 완료하세요.")
        self._log(
            f"도전의 탑 {tower_challenge_tier(self.flags)}단계가 열렸습니다. "
            "탑의 수호자가 더욱 강해졌습니다."
        )
        return {"ok": True, "state": self.state()}

    def boss_action(self, operation: str) -> dict:
        location = self.game_map.current
        if self.phase != "explore":
            return self._error("탐험 중에만 보스에게 다시 도전할 수 있습니다.")
        if operation != "retry":
            return self._error("지원하지 않는 보스 행동입니다.")
        if not location.boss or not location.boss_defeated:
            return self._error("현재 장소에는 다시 도전할 보스가 없습니다.")

        if location.id == "tower_summit" and tower_clear_count(self.flags) == 0:
            # 반복 도전 기능 도입 전 저장도 최초 정복을 끝낸 상태로 보정한다.
            self.flags["tower_clear_count"] = 1
        enemies = (
            [create_scaled_tower_guardian(self.flags)]
            if location.id == "tower_summit" else location.boss()
        )
        title = (
            f"{location.name} · {tower_challenge_tier(self.flags)}단계 재도전"
            if location.id == "tower_summit" else f"{location.name}의 보스 재도전"
        )
        self._begin_battle(enemies, "boss_retry", title)
        return {"ok": True, "state": self.state()}

    def blacksmith_action(self, equipment_index) -> dict:
        if self.phase != "explore" or self.game_map.current_id != "village":
            return self._error("대장간은 시작 마을에서 이용할 수 있습니다.")
        try:
            index = self._index(
                equipment_index, len(self.equipment_inventory), "강화 장비"
            )
            upgraded, cost = enhance_equipment(
                self.party, self.equipment_inventory, index
            )
        except (IndexError, TypeError, ValueError) as error:
            return self._error(str(error))
        self._log(f"대장간 강화 성공! {upgraded.display_name} ({cost}G 사용)")
        return {"ok": True, "state": self.state()}

    def equipment_action(self, operation: str, member_index, equipment_index=None, slot=None) -> dict:
        if self.phase != "explore":
            return self._error("탐험 중에만 장비를 변경할 수 있습니다.")
        try:
            member = self.party.members[
                self._index(member_index, len(self.party.members), "파티원")
            ]
            if operation == "equip":
                index = self._index(equipment_index, len(self.equipment_inventory), "장비")
                item = self.equipment_inventory.pop(index)
                previous = member.equip(item)
                if previous:
                    self.equipment_inventory.append(previous)
                self._log(f"{member.name}이(가) {item.display_name}을(를) 착용했습니다.")
            elif operation == "unequip":
                if slot not in member.equipment:
                    raise ValueError("올바른 장비 슬롯을 선택하세요.")
                previous = member.unequip(slot)
                if previous is None:
                    raise ValueError("해제할 장비가 없습니다.")
                self.equipment_inventory.append(previous)
                self._log(f"{member.name}이(가) {previous.display_name}을(를) 해제했습니다.")
            else:
                return self._error("지원하지 않는 장비 행동입니다.")
        except (IndexError, TypeError, ValueError) as error:
            return self._error(str(error))
        return {"ok": True, "state": self.state()}

    def quest_action(self, operation: str, quest_id: str) -> dict:
        if self.phase != "explore" or self.game_map.current_id != "village":
            return self._error("퀘스트 게시판은 시작 마을에서 이용할 수 있습니다.")
        if quest_id not in QUESTS:
            return self._error("존재하지 않는 퀘스트입니다.")
        self.quest_log.refresh_from_world(self.game_map, self.flags)
        if operation == "accept":
            if not self.quest_log.accept(quest_id):
                return self._error("지금은 이 퀘스트를 수락할 수 없습니다.")
            self.quest_log.refresh_from_world(self.game_map, self.flags)
            self._log(f"퀘스트 [{QUESTS[quest_id].title}]을(를) 수락했습니다.")
        elif operation == "claim":
            if not self.quest_log.claim(
                quest_id, self.party, self.inventory, self.flags
            ):
                return self._error("아직 퀘스트 보상을 받을 수 없습니다.")
            self._log(f"퀘스트 [{QUESTS[quest_id].title}] 보상을 받았습니다.")
        else:
            return self._error("지원하지 않는 퀘스트 행동입니다.")
        return {"ok": True, "state": self.state()}

    def save_action(self, operation: str, slot, backup=None) -> dict:
        if operation == "save" and self.phase != "explore":
            return self._error("탐험 화면에서만 저장할 수 있습니다.")
        if operation in {"load", "restore"} and self.phase not in {"explore", "setup"}:
            return self._error("현재 화면에서는 저장을 불러올 수 없습니다.")
        try:
            slot_number = int(slot)
        except (TypeError, ValueError):
            return self._error("올바른 저장 슬롯을 선택하세요.")
        if not 1 <= slot_number <= game_save.MAX_SLOTS:
            return self._error("올바른 저장 슬롯을 선택하세요.")
        path = game_save.slot_path(slot_number, self.save_dir)
        try:
            if operation == "save":
                game_save.save_game(
                    self.party, self.inventory, self.game_map, self.flags,
                    self.equipment_inventory, path=path, quest_log=self.quest_log,
                )
                self._log(f"슬롯 {slot_number}에 저장했습니다.")
                return {
                    "ok": True,
                    "state": self.state(),
                    "slot": slot_number,
                    "backup": game_save.read_save_payload(path),
                }
            elif operation == "load":
                if not game_save.has_save(path):
                    return self._error("선택한 슬롯이 비어 있습니다.")
                (
                    self.party, self.inventory, self.game_map, self.flags,
                    self.equipment_inventory, self.quest_log,
                ) = game_save.load_game(path)
                self.enemies = []
                self.turn = 0
                self.current_actor = None
                self.battle_context = ""
                self.dialogue = None
                self.dialogue_node_id = None
                self.dialogue_lines = []
                self.logs = [f"슬롯 {slot_number}의 저장을 불러왔습니다."]
                self._enter_current_location()
            elif operation == "restore":
                if not isinstance(backup, dict):
                    return self._error("브라우저 백업 형식이 올바르지 않습니다.")
                game_save.write_save_payload(backup, path)
            else:
                return self._error("지원하지 않는 저장 행동입니다.")
        except (OSError, ValueError) as error:
            return self._error(f"저장 데이터를 처리하지 못했습니다: {error}")
        return {"ok": True, "state": self.state()}

    def advance_dialogue(self, choice=None) -> dict:
        if self.phase != "dialogue" or self.dialogue is None or self.dialogue_node_id is None:
            return self._error("진행 중인 대화가 없습니다.")
        node = self.dialogue.nodes[self.dialogue_node_id]
        if node.choices:
            try:
                index = self._index(choice, len(node.choices), "대화 선택지")
            except (TypeError, ValueError) as error:
                return self._error(str(error))
            label, next_id = node.choices[index]
            self._log(f"선택: {label}")
        else:
            next_id = None

        if next_id is None:
            self.game_map.current.dialogue_played = True
            self.dialogue = None
            self.dialogue_node_id = None
            self.dialogue_lines = []
            self.quest_log.sync_story_flags(self.flags)
            self._after_location_dialogue()
        else:
            self.dialogue_node_id = next_id
            self._show_dialogue_node()
        return {"ok": True, "state": self.state()}

    def _enter_current_location(self) -> None:
        location = self.game_map.current
        self.quest_log.sync_story_flags(self.flags)
        self.quest_log.refresh_from_world(self.game_map, self.flags)
        if location.dialogue and not location.dialogue_played:
            self.dialogue = location.dialogue
            self.dialogue_node_id = self.dialogue.start_id
            self.phase = "dialogue"
            self._show_dialogue_node()
            return
        self._after_location_dialogue()

    def _show_dialogue_node(self) -> None:
        node = self.dialogue.nodes[self.dialogue_node_id]
        self.dialogue_lines = node.resolve_lines(self.flags)
        if node.effect:
            node.effect(self.flags)

    def _after_location_dialogue(self) -> None:
        location = self.game_map.current
        if (
            location.id == "final_chamber"
            and self.flags.get("embraced_power")
            and not self.flags.get("seal_power_applied")
        ):
            for member in self.party.members:
                member.max_hp += 6
                member.attack += 2
                member.defense += 1
                member.hp = min(member.effective_max_hp, member.hp + 6)
            self.flags["seal_power_applied"] = True
            self._log("봉인의 힘이 파티에 깃들었습니다. 최대 HP +6, 공격력 +2, 방어력 +1")

        if location.boss and not location.boss_defeated:
            enemies = (
                [create_scaled_tower_guardian(self.flags)]
                if location.id == "tower_summit" else location.boss()
            )
            title = f"{location.name} · {tower_challenge_tier(self.flags)}단계" if location.id == "tower_summit" else f"{location.name}의 보스"
            self._begin_battle(enemies, "boss", title)
            return

        self._claim_location_loot()
        if location.is_ending:
            self.phase = "ending"
            self.result_message = "데모의 이야기를 완료했습니다."
        else:
            self.phase = "explore"
            self.result_message = location.description

    def _claim_location_loot(self) -> None:
        location = self.game_map.current
        if not location.has_loot or location.loot_claimed:
            return
        if location.boss and not location.boss_defeated:
            return
        if location.loot_item:
            self.inventory.append(location.loot_item)
            self._log(f"보물 [{location.loot_item.name}]을(를) 획득했습니다.")
        if location.loot_equipment:
            self.equipment_inventory.append(location.loot_equipment)
            self._log(f"보물 {location.loot_equipment.display_name}을(를) 획득했습니다.")
        location.loot_claimed = True

    def _begin_battle(self, enemies: List[Enemy], context: str, title: str) -> None:
        self.enemies = enemies
        self.phase = "battle"
        self.result_message = ""
        if context == "training":
            self.logs = [f"[{title}] 전투가 시작되었습니다!"]
        else:
            self._log(f"[{title}] 전투가 시작되었습니다!")
        self.turn = 0
        self._rewarded = False
        self.current_actor = None
        self.battle_context = context
        self._start_round()

    def start_battle(self, encounter_id: str) -> dict:
        if encounter_id not in ENCOUNTERS:
            return self._error("존재하지 않는 전투입니다.")
        if self.phase == "battle":
            return self._error("진행 중인 전투를 먼저 끝내세요.")
        if self.party.is_wiped_out:
            return self._error("파티가 전멸했습니다. 새 게임을 시작하세요.")

        encounter = ENCOUNTERS[encounter_id]
        self._begin_battle(encounter["factory"](), "training", encounter["name"])
        return {"ok": True, "state": self.state()}

    def act(self, action: dict) -> dict:
        if self.phase != "battle" or self.current_actor is None:
            return self._error("현재 행동할 수 있는 파티원이 없습니다.")
        actor = self.current_actor
        action_type = action.get("type")
        try:
            if action_type == "attack":
                target = self._enemy_target(action.get("target"))
                damage = actor.basic_attack(target)
                if target.last_damage_evaded:
                    self._log(f"{target.name}이(가) {actor.name}의 공격을 회피했습니다.")
                else:
                    critical = " 치명타!" if actor.last_attack_was_critical else ""
                    self._log(f"{actor.name} → {target.name}: {damage} 피해.{critical}")
            elif action_type == "skill":
                self._use_skill(actor, action)
            elif action_type == "item":
                self._use_item(action)
            elif action_type == "defend":
                actor.guarding = True
                self._log(f"{actor.name}이(가) 방어 태세를 취했습니다.")
            elif action_type == "flee":
                if self._attempt_flee():
                    return {"ok": True, "state": self.state()}
            else:
                return self._error("지원하지 않는 행동입니다.")
        except (IndexError, TypeError, ValueError) as error:
            return self._error(str(error) or "행동을 처리할 수 없습니다.")

        self.current_actor = None
        self._advance()
        return {"ok": True, "state": self.state()}

    def _start_round(self) -> None:
        self.turn += 1
        self._log(f"--- {self.turn}턴 ---")
        combatants = [*self.party.alive_members, *[e for e in self.enemies if e.is_alive]]
        self._order = sorted(combatants, key=lambda character: character.effective_speed, reverse=True)
        self._cursor = 0
        self._advance()

    def _advance(self) -> None:
        while self.phase == "battle":
            if self._finish_if_needed():
                return
            if self._cursor >= len(self._order):
                self.turn += 1
                self._log(f"--- {self.turn}턴 ---")
                combatants = [*self.party.alive_members, *[e for e in self.enemies if e.is_alive]]
                self._order = sorted(
                    combatants, key=lambda character: character.effective_speed, reverse=True
                )
                self._cursor = 0
                continue

            actor = self._order[self._cursor]
            self._cursor += 1
            if not actor.is_alive:
                continue
            if isinstance(actor, PlayerCharacter):
                actor.guarding = False

            paralyzed = actor.is_paralyzed()
            for message in actor.tick_status_effects():
                self._log(message)
            if not actor.is_alive:
                continue
            if paralyzed:
                self._log(f"{actor.name}은(는) 마비되어 행동하지 못했습니다.")
                continue

            if isinstance(actor, PlayerCharacter):
                self.current_actor = actor
                return
            self._enemy_action(actor)

    def _finish_if_needed(self) -> bool:
        if all(not enemy.is_alive for enemy in self.enemies):
            self._victory()
            return True
        if self.party.is_wiped_out:
            self.phase = "defeat"
            self.result_message = "파티가 전멸했습니다."
            self.current_actor = None
            self._log(self.result_message)
            return True
        return False

    def _victory(self) -> None:
        if self._rewarded:
            return
        self._rewarded = True
        total_exp = sum(enemy.exp_reward for enemy in self.enemies)
        total_gold = sum(enemy.gold_reward for enemy in self.enemies)
        self.party.gold += total_gold
        self._log(f"승리! 경험치 {total_exp}, 골드 {total_gold}G를 획득했습니다.")
        for member in self.party.alive_members:
            if member.gain_exp(total_exp):
                self._log(f"{member.name}이(가) Lv.{member.level}로 성장했습니다.")
                for message in member.last_growth_messages:
                    self._log(message)
        for enemy in self.enemies:
            for item, chance in enemy.loot_pool:
                if random.random() < chance:
                    self.inventory.append(item)
                    self._log(f"{enemy.name}: {item.name} 획득")
            if random.random() < enemy.equipment_drop_chance:
                equipment = data.generate_random_equipment(enemy.level)
                self.equipment_inventory.append(equipment)
                self._log(f"{enemy.name}: {equipment.display_name} 획득")
        self.current_actor = None
        context = self.battle_context
        self.battle_context = ""
        if context in {"boss", "boss_retry"}:
            location = self.game_map.current
            if location.id == "tower_summit":
                clear_count, bonus_gold, equipment = complete_tower_challenge(
                    self.flags, self.party, self.equipment_inventory
                )
                if clear_count == 1:
                    self._log("도전의 탑을 최초로 정복했습니다!")
                else:
                    self._log(
                        f"도전의 탑 {clear_count}회 클리어 보상: "
                        f"{bonus_gold}G, {equipment.display_name}"
                    )
            first_clear = not location.boss_defeated
            location.boss_defeated = True
            self.quest_log.refresh_from_world(self.game_map, self.flags)
            if first_clear:
                self._log(f"{location.name}의 위험이 사라졌습니다.")
            else:
                self._log(
                    f"{location.name}의 보스를 다시 쓰러뜨렸습니다. "
                    "이 장소에서 언제든 재도전할 수 있습니다."
                )
            self._after_location_dialogue()
        elif context == "random":
            self._enter_current_location()
        else:
            self.phase = "victory"
            self.result_message = "전투에서 승리했습니다. 다음 전투를 선택할 수 있습니다."

    def _use_skill(self, actor: PlayerCharacter, action: dict) -> None:
        skill_index = self._index(action.get("skill"), len(actor.skills), "스킬")
        skill = actor.skills[skill_index]
        if actor.mp < skill.mp_cost:
            raise ValueError("MP가 부족합니다.")

        allies = self.party.alive_members
        enemies = [enemy for enemy in self.enemies if enemy.is_alive]
        candidates = allies if skill.kind in ("heal", "buff") else enemies
        if skill.aoe:
            results = actor.use_skill_on_targets(skill, candidates)
        else:
            target_index = self._index(action.get("target"), len(candidates), "대상")
            target = candidates[target_index]
            amount, status_applied, effectiveness = actor.use_skill(skill, target)
            results = [(target, amount, status_applied, effectiveness)]

        for target, amount, status_applied, effectiveness in results:
            if skill.kind == "steal":
                self.party.gold += amount
            for message in _describe_skill_result(
                actor.name, target.name, skill, amount, status_applied, effectiveness,
                actor.last_attack_was_critical, target.last_damage_evaded,
            ):
                self._log(message)

    def _use_item(self, action: dict) -> None:
        usable = [item for item in self.inventory if item.usable_in_combat]
        item_index = self._index(action.get("item"), len(usable), "아이템")
        target_index = self._index(action.get("target"), len(self.party.alive_members), "대상")
        item = usable[item_index]
        target = self.party.alive_members[target_index]
        target.take_item(item)
        self.inventory.remove(item)
        self._log(f"{target.name}이(가) {item.name}을(를) 사용했습니다.")

    def _enemy_action(self, enemy: Enemy) -> None:
        skill, target = enemy.choose_action(self.party.alive_members)
        if target is None:
            return
        if skill is None:
            damage = enemy.basic_attack(target)
            if target.last_damage_evaded:
                self._log(f"{target.name}이(가) {enemy.name}의 공격을 회피했습니다.")
            else:
                self._log(f"{enemy.name} → {target.name}: {damage} 피해.")
            return

        targets = [enemy] if skill.kind in ("heal", "buff") else self.party.alive_members
        try:
            if skill.aoe:
                results = enemy.use_skill_on_targets(skill, targets)
            else:
                amount, applied, effectiveness = enemy.use_skill(skill, target)
                results = [(target, amount, applied, effectiveness)]
        except ValueError:
            return
        for affected, amount, applied, effectiveness in results:
            for message in _describe_skill_result(
                enemy.name, affected.name, skill, amount, applied, effectiveness,
                enemy.last_attack_was_critical, affected.last_damage_evaded,
            ):
                self._log(message)

    def _attempt_flee(self) -> bool:
        alive_enemies = [enemy for enemy in self.enemies if enemy.is_alive]
        if any(enemy.job in BOSS_JOBS for enemy in alive_enemies):
            self._log("보스 전투에서는 도망칠 수 없습니다.")
            return False
        party_speed = sum(member.effective_speed for member in self.party.alive_members) / len(self.party.alive_members)
        enemy_speed = sum(enemy.effective_speed for enemy in alive_enemies) / len(alive_enemies)
        chance = max(0.25, min(0.90, 0.60 + (party_speed - enemy_speed) * 0.05))
        if random.random() < chance:
            world_encounter = self.battle_context == "random"
            self.current_actor = None
            self.battle_context = ""
            self._log(f"도주 성공 ({chance:.0%})")
            if world_encounter:
                self._enter_current_location()
            else:
                self.phase = "fled"
                self.result_message = "도주에 성공했습니다. 전투 보상은 없습니다."
            return True
        self._log(f"도주 실패 ({chance:.0%})")
        return False

    def _enemy_target(self, value) -> Enemy:
        enemies = [enemy for enemy in self.enemies if enemy.is_alive]
        return enemies[self._index(value, len(enemies), "대상")]

    @staticmethod
    def _index(value, length: int, label: str) -> int:
        if not isinstance(value, int) or value < 0 or value >= length:
            raise ValueError(f"올바른 {label}을(를) 선택하세요.")
        return value

    def _log(self, message: str) -> None:
        self.logs.append(message)
        self.logs = self.logs[-100:]

    def _error(self, message: str) -> dict:
        return {"ok": False, "error": message, "state": self.state()}

    @staticmethod
    def _character_state(character) -> dict:
        return {
            "name": character.name,
            "job": character.job,
            "level": character.level,
            "hp": character.hp,
            "max_hp": character.effective_max_hp,
            "mp": character.mp,
            "max_mp": character.effective_max_mp,
            "alive": character.is_alive,
            "guarding": character.guarding,
            "statuses": [
                {"name": effect.name, "turns": effect.remaining_turns}
                for effect in character.status_effects
            ],
            "stats": {
                "attack": character.effective_attack,
                "defense": character.effective_defense,
                "speed": character.effective_speed,
            },
            "equipment": {
                slot: (WebGame._equipment_state(item) if item else None)
                for slot, item in character.equipment.items()
            },
        }

    @staticmethod
    def _equipment_state(item) -> dict:
        return {
            "name": item.name,
            "display_name": item.display_name,
            "slot": item.slot,
            "slot_name": SLOT_NAMES_KR[item.slot],
            "description": item.description,
            "special_effect": item.special_effect,
            "price": item.price,
            "rarity": item.rarity,
            "enhancement_level": item.enhancement_level,
        }

    def state(self) -> dict:
        actor = self.current_actor
        location = self.game_map.current
        skills = []
        if actor:
            skills = [
                {
                    "index": index, "name": skill.name, "mp_cost": skill.mp_cost,
                    "kind": skill.kind, "aoe": skill.aoe,
                    "description": skill.description,
                    "target_side": "party" if skill.kind in ("heal", "buff") else "enemy",
                }
                for index, skill in enumerate(actor.skills)
            ]
        usable_items = [item for item in self.inventory if item.usable_in_combat]
        exits = []
        for label, target_id in location.exits.items():
            locked = label in location.locked_exits and label not in location.unlocked_labels
            exits.append({
                "label": label,
                "target_id": target_id,
                "target_name": self.game_map.locations[target_id].name,
                "locked": locked,
                "required_item": location.locked_exits.get(label) if locked else None,
            })
        dialogue_state = None
        if self.phase == "dialogue" and self.dialogue is not None:
            node = self.dialogue.nodes[self.dialogue_node_id]
            dialogue_state = {
                "lines": self.dialogue_lines,
                "choices": [
                    {"index": index, "label": label}
                    for index, (label, _) in enumerate(node.choices)
                ],
                "can_continue": not node.choices,
            }
        shop_state = None
        if location.has_shop:
            sellable_items = [item for item in self.inventory if item.sellable]
            shop_state = {
                "items": [
                    {
                        "index": index, "name": item.name, "price": item.price,
                        "description": item.description,
                    }
                    for index, item in enumerate(location.shop_items)
                ],
                "equipment": [
                    {"index": index, **self._equipment_state(item)}
                    for index, item in enumerate(location.shop_equipment)
                ],
                "sell_items": [
                    {
                        "index": index, "name": item.name,
                        "price": int(item.price * SELL_RATIO), "description": item.description,
                    }
                    for index, item in enumerate(sellable_items)
                ],
                "sell_equipment": [
                    {
                        "index": index, **self._equipment_state(item),
                        "price": int(item.price * SELL_RATIO),
                    }
                    for index, item in enumerate(self.equipment_inventory)
                ],
            }
        blacksmith_state = None
        if location.id == "village":
            blacksmith_equipment = []
            for index, item in enumerate(self.equipment_inventory):
                allowed, reason = can_upgrade(
                    self.party, self.equipment_inventory, index
                )
                blacksmith_equipment.append({
                    "index": index,
                    **self._equipment_state(item),
                    "cost": (
                        None if item.enhancement_level >= MAX_ENHANCEMENT
                        else upgrade_cost(item)
                    ),
                    "materials": len(matching_material_indices(
                        self.equipment_inventory, index
                    )),
                    "can_upgrade": allowed,
                    "reason": reason,
                })
            blacksmith_state = {
                "max_level": MAX_ENHANCEMENT,
                "equipment": blacksmith_equipment,
            }
        slots = [
            {"slot": number, "exists": exists, "summary": summary}
            for number, exists, summary in game_save.list_slots(save_dir=self.save_dir)
        ]
        return {
            "phase": self.phase,
            "turn": self.turn,
            "result_message": self.result_message,
            "gold": self.party.gold,
            "party": [self._character_state(member) for member in self.party.members],
            "enemies": [
                {
                    **self._character_state(enemy),
                    "weakness": enemy.weakness,
                    "resistance": enemy.resistance,
                    "boss": enemy.job in BOSS_JOBS,
                }
                for enemy in self.enemies
            ],
            "current_actor": actor.name if actor else None,
            "skills": skills,
            "items": [
                {"index": index, "name": item.name, "description": item.description}
                for index, item in enumerate(usable_items)
            ],
            "inventory_count": len(self.inventory),
            "equipment_count": len(self.equipment_inventory),
            "logs": self.logs,
            "location": {
                "id": location.id,
                "name": location.name,
                "description": location.description,
                "exits": exits,
                "visited": [
                    {"id": loc_id, "name": loc.name, "current": loc_id == location.id}
                    for loc_id, loc in self.game_map.locations.items()
                    if loc_id in self.game_map.visited
                ],
            },
            "dialogue": dialogue_state,
            "story_flags": dict(self.flags),
            "quests": [
                {
                    "id": quest_id,
                    "title": definition.title,
                    "status": self.quest_log.status(quest_id),
                    "objective": definition.objective,
                    "description": definition.description,
                    "gold_reward": definition.gold_reward,
                    "bonus_gold_reward": definition.bonus_gold_reward,
                }
                for quest_id, definition in QUESTS.items()
            ],
            "shop": shop_state,
            "blacksmith": blacksmith_state,
            "inn": location.has_inn,
            "boss_retry": {
                "available": (
                    self.phase == "explore"
                    and bool(location.boss)
                    and location.boss_defeated
                ),
                "location_name": location.name,
            },
            "tower": {
                "clear_count": tower_clear_count(self.flags),
                "next_tier": tower_challenge_tier(self.flags),
                "can_retry": (
                    location.id == "village"
                    and self.game_map.locations["tower_summit"].boss_defeated
                ),
                "active": bool(self.flags.get("tower_challenge_active")),
            },
            "equipment_inventory": [
                {"index": index, **self._equipment_state(item)}
                for index, item in enumerate(self.equipment_inventory)
            ],
            "save_slots": slots,
            "setup": {
                "defaults": DEFAULT_PARTY_SETUP,
                "jobs": [
                    {"id": job_id, "label": label}
                    for job_id, label in data.JOB_LABELS.items()
                ],
            },
            "encounters": [
                {"id": key, "name": value["name"], "description": value["description"]}
                for key, value in ENCOUNTERS.items()
            ],
        }


GAME = WebGame()
GAME_LOCK = threading.Lock()


def _enabled(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class SessionStore:
    """브라우저별 게임과 잠금을 메모리에 보관하고 저장 폴더를 분리한다."""

    def __init__(self, base_save_dir: Optional[Path] = None, max_sessions: int = 500):
        self.base_save_dir = Path(base_save_dir) if base_save_dir else None
        self.max_sessions = max_sessions
        self._entries = {}
        self._lock = threading.Lock()

    def get(self, session_id: str):
        now = time.monotonic()
        with self._lock:
            entry = self._entries.get(session_id)
            if entry is None:
                if len(self._entries) >= self.max_sessions:
                    oldest_id = min(
                        self._entries, key=lambda key: self._entries[key][2]
                    )
                    self._entries.pop(oldest_id, None)
                base = self.base_save_dir or Path(game_save.SAVE_DIR)
                game = WebGame(save_dir=base / "web" / session_id)
                entry = [game, threading.Lock(), now]
                self._entries[session_id] = entry
            else:
                entry[2] = now
            return entry[0], entry[1]


SESSION_COOKIE_NAME = "undefined_legend_session"


class GameHandler(BaseHTTPRequestHandler):
    server_version = "UndefinedLegend"
    sys_version = ""
    multi_session_enabled = _enabled("RPG_MULTI_SESSION")
    session_store = SessionStore()

    def _game_session(self):
        if not self.multi_session_enabled:
            return GAME, GAME_LOCK
        cookie = SimpleCookie()
        try:
            cookie.load(self.headers.get("Cookie", ""))
        except CookieError:
            cookie = SimpleCookie()
        morsel = cookie.get(SESSION_COOKIE_NAME)
        session_id = morsel.value if morsel else ""
        if len(session_id) != 32 or any(char not in "0123456789abcdef" for char in session_id):
            session_id = secrets.token_hex(16)
        secure = _enabled("RPG_COOKIE_SECURE") or (
            self.headers.get("X-Forwarded-Proto", "").split(",", 1)[0].strip() == "https"
        )
        self._session_cookie = (
            f"{SESSION_COOKIE_NAME}={session_id}; Path=/; Max-Age=31536000; "
            f"HttpOnly; SameSite=Lax{'; Secure' if secure else ''}"
        )
        return self.session_store.get(session_id)

    def end_headers(self):
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header(
            "Permissions-Policy", "camera=(), microphone=(), geolocation=()"
        )
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
            "connect-src 'self'; object-src 'none'; base-uri 'self'; "
            "frame-ancestors 'none'",
        )
        super().end_headers()

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path == "/api/health":
            self._json({"ok": True, "service": "undefined-legend"})
            return
        if path == "/api/state":
            game, game_lock = self._game_session()
            with game_lock:
                self._json({"ok": True, "state": game.state()})
            return
        self._static(path)

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length) or b"{}")
        except (ValueError, json.JSONDecodeError):
            self._json({"ok": False, "error": "JSON 요청 형식이 올바르지 않습니다."}, 400)
            return
        game, game_lock = self._game_session()
        with game_lock:
            if self.path == "/api/new":
                game.reset()
                result = {"ok": True, "state": game.state()}
            elif self.path == "/api/setup":
                result = game.configure_party(payload.get("members"))
            elif self.path == "/api/start":
                result = game.start_battle(payload.get("encounter", ""))
            elif self.path == "/api/move":
                result = game.move(payload.get("exit", ""))
            elif self.path == "/api/dialogue":
                result = game.advance_dialogue(payload.get("choice"))
            elif self.path == "/api/shop":
                result = game.shop_action(payload.get("operation", ""), payload.get("index"))
            elif self.path == "/api/inn":
                result = game.inn_action()
            elif self.path == "/api/blacksmith":
                result = game.blacksmith_action(payload.get("equipment"))
            elif self.path == "/api/tower":
                result = game.tower_action(payload.get("operation", ""))
            elif self.path == "/api/boss":
                result = game.boss_action(payload.get("operation", ""))
            elif self.path == "/api/equipment":
                result = game.equipment_action(
                    payload.get("operation", ""), payload.get("member"),
                    payload.get("equipment"), payload.get("slot"),
                )
            elif self.path == "/api/quest":
                result = game.quest_action(payload.get("operation", ""), payload.get("quest", ""))
            elif self.path == "/api/save":
                result = game.save_action(
                    payload.get("operation", ""), payload.get("slot"), payload.get("backup")
                )
            elif self.path == "/api/action":
                result = game.act(payload)
            else:
                self._json({"ok": False, "error": "API 경로를 찾을 수 없습니다."}, 404)
                return
        self._json(result, 200 if result.get("ok") else 400)

    def _static(self, request_path: str) -> None:
        relative = "index.html" if request_path == "/" else request_path.lstrip("/")
        candidate = (WEB_ROOT / relative).resolve()
        try:
            candidate.relative_to(WEB_ROOT.resolve())
        except ValueError:
            self.send_error(403)
            return
        if not candidate.is_file():
            self.send_error(404)
            return
        content = candidate.read_bytes()
        mime = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
        self.send_response(200)
        if mime.startswith("text/") or mime in {
            "application/javascript", "application/json", "application/manifest+json",
            "image/svg+xml",
        }:
            mime = f"{mime}; charset=utf-8"
        self.send_header("Content-Type", mime)
        cache_control = (
            "no-cache" if candidate.name in {"index.html", "sw.js", "manifest.webmanifest"}
            else "public, max-age=3600"
        )
        self.send_header("Cache-Control", cache_control)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _json(self, payload: dict, status: int = 200) -> None:
        content = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        if getattr(self, "_session_cookie", None):
            self.send_header("Set-Cookie", self._session_cookie)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def log_message(self, format, *args):
        return


def main() -> None:
    parser = argparse.ArgumentParser(description="미정의 전설 웹 플레이")
    parser.add_argument("--host", default=os.environ.get("HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8000")))
    parser.add_argument("--open", action="store_true", help="시작 후 기본 브라우저 열기")
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), GameHandler)
    url = f"http://{args.host}:{args.port}"
    print(f"웹 플레이 실행 중: {url}")
    print("종료: Ctrl+C")
    if args.open:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n서버를 종료합니다.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
