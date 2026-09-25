"""외부 라이브러리 없이 실행되는 미정의 전설 웹 플레이 시제품."""

from __future__ import annotations

import argparse
from dataclasses import replace
import hmac
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
from commissions import (
    accept_commission, claim_commission, commission_state, offer_commission,
    record_defeats, record_visit,
)
from combo import ComboChain, can_chain
from bestiary import bestiary_state, discover_enemies, record_enemy_defeats
from achievements import achievement_state, claim_achievement
from protection import AllyProtection
import save as game_save
from blacksmith import (
    MAX_ENHANCEMENT, can_upgrade, enhance_equipment,
    matching_material_indices, upgrade_cost, upgrade_preview_text,
    STAR_ORE_NAME, star_ore_cost, award_star_ore,
)
from crafting import (
    ENHANCEMENT_DISMANTLE_BONUS, SHARD_FLAG, SYNTHESIS_RECIPES,
    REFORGE_COSTS, apply_reforge, bulk_dismantle_reason, can_reforge,
    can_synthesize, dismantle_equipment, equipment_affixes, reforge_cost,
    dismantle_equipment_many, dismantle_value, shard_count,
    synthesize_weapon, synthesis_preview, preview_reforge, preview_stat_text,
)
from combat import _describe_skill_result
from equipment import SLOT_NAMES_KR, protection_warning
from models import (
    EQUIPMENT_RARITIES, RARITY_NAMES_KR, WEAPON_FAMILIES,
    Enemy, Item, Party, PlayerCharacter, Skill,
)
from quests import QuestLog, QUESTS
from shop import SELL_RATIO
from advancement import ADVANCEMENT_LEVEL, advance, options_for
from world import (
    MAP_REGIONS, TOWER_MAX_FLOOR, build_world, complete_tower_challenge,
    create_scaled_tower_boss, grant_tower_boss_reward,
    region_for_location, reset_tower_challenge, tower_challenge_tier,
    tower_clear_count, tower_floor_number,
)
from dungeon import (
    DUNGEON_ENTRY_FEE, DUNGEON_LOCATION_ID, DUNGEON_MAX_DEPTH,
    create_dungeon_floor, dungeon_clear_count, floor_bank_reward,
    floor_shard_reward, full_clear_shard_bonus,
)


WEB_ROOT = Path(__file__).with_name("web_ui")
mimetypes.add_type("application/manifest+json", ".webmanifest")
BOSS_JOBS = {"미니보스", "보스", "최종보스"}
DEFAULT_PARTY_SETUP = [
    {"name": "레온", "job": "warrior"},
    {"name": "리제", "job": "mage"},
    {"name": "셀린", "job": "healer"},
]

AUTO_BATTLE_STRATEGIES = {
    "balanced": {
        "label": "균형",
        "heal_threshold": 0.45,
        "defend_threshold": 0.25,
        "skill_margin": 1,
    },
    "aggressive": {
        "label": "공세",
        "heal_threshold": 0.30,
        "defend_threshold": 0.15,
        "skill_margin": -1,
    },
    "survival": {
        "label": "안정",
        "heal_threshold": 0.65,
        "defend_threshold": 0.40,
        "skill_margin": 2,
    },
}

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
        self._forge_key = secrets.token_bytes(32)
        self._craft_key = secrets.token_bytes(32)
        self._reforge_pending = None
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
        self.phase_transition_id = 0
        self.phase_transition_message = ""
        self.turn = 0
        self._order = []
        self._cursor = 0
        self.current_actor: Optional[PlayerCharacter] = None
        self._rewarded = False
        self.combo = ComboChain()
        self.protection = AllyProtection()
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

        target_id = location.exits[exit_label]
        if target_id == DUNGEON_LOCATION_ID:
            return self.dungeon_action("enter")
        if (
            location.id == DUNGEON_LOCATION_ID
            and target_id == "village"
            and self.flags.get("dungeon_active")
        ):
            return self.dungeon_action("retreat")

        requirement = location.flag_requirements.get(exit_label)
        if requirement and not requirement.is_met(self.flags):
            return self._error(requirement.failure_message)

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
        for title in record_visit(self.flags, arrived.id):
            self._log(f"NPC 의뢰 [{title}]의 목표를 달성했습니다.")
        if arrived.encounter_pool and random.random() < arrived.encounter_chance:
            enemies = random.choice(arrived.encounter_pool)()
            self._begin_battle(enemies, "random", f"{arrived.name}의 습격")
        else:
            self._enter_current_location()
        return {"ok": True, "state": self.state()}

    def travel_action(self, target_id: str) -> dict:
        current = self.game_map.current
        if self.phase != "explore" or not current.is_village:
            return self._error("마을 안에서만 마을 간 이동을 이용할 수 있습니다.")
        target = self.game_map.locations.get(target_id)
        if target is None or not target.is_village or target.id not in self.game_map.visited:
            return self._error("먼저 직접 방문한 마을로만 이동할 수 있습니다.")
        if target is current:
            return self._error("현재 머무는 마을입니다.")
        self.game_map.move_to(target.id)
        self._log(f"마을 이동로를 이용해 {target.name}에 도착했습니다.")
        for title in record_visit(self.flags, target.id):
            self._log(f"NPC 의뢰 [{title}]의 목표를 달성했습니다.")
        self._enter_current_location()
        return {"ok": True, "state": self.state()}

    def shop_action(self, operation: str, index, shop_index=0) -> dict:
        if self.phase != "explore" or not self.game_map.current.has_shop:
            return self._error("현재 장소에서는 상점을 이용할 수 없습니다.")
        location = self.game_map.current
        try:
            shop = location.shops[self._index(shop_index, len(location.shops), "상점")]
            if not shop.is_available(self.flags):
                raise ValueError(f"{shop.unlock_description} 후에 이용할 수 있습니다.")
            if operation == "buy_item":
                item = shop.items[self._index(index, len(shop.items), "상품")]
                price = shop.price_for(item, self.flags)
                if self.party.gold < price:
                    raise ValueError("골드가 부족합니다.")
                self.party.gold -= price
                self.inventory.append(item)
                self._log(f"{item.name}을(를) {price}G에 구매했습니다.")
            elif operation == "buy_equipment":
                equipment = shop.equipment[
                    self._index(index, len(shop.equipment), "상품")
                ]
                price = shop.price_for(equipment, self.flags)
                if self.party.gold < price:
                    raise ValueError("골드가 부족합니다.")
                self.party.gold -= price
                self.equipment_inventory.append(equipment)
                self._log(f"{equipment.display_name}을(를) {price}G에 구매했습니다.")
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
                if equipment.locked:
                    raise ValueError("잠금 보호된 장비는 판매할 수 없습니다. 장비 관리에서 잠금을 해제하세요.")
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
            return self._error("현재 장소에서는 여관을 이용할 수 없습니다.")
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

    def _start_dungeon_floor(self) -> None:
        enemies, modifier = create_dungeon_floor(self.flags)
        self.flags["dungeon_modifier"] = modifier["id"]
        self.flags["dungeon_modifier_name"] = modifier["name"]
        self.flags["dungeon_modifier_description"] = modifier["description"]
        self.flags["dungeon_modifier_reward"] = modifier["reward"]
        depth = int(self.flags["dungeon_depth"])
        self._log(
            f"심연 {depth}층 위험 변이: {modifier['name']} · {modifier['description']}"
        )
        self._begin_battle(enemies, "dungeon", f"심연 변이 던전 · {depth}층")

    def _finish_dungeon_run(self, full_clear: bool) -> None:
        bank = max(0, int(self.flags.get("dungeon_reward_bank", 0)))
        shard_bank = max(0, int(self.flags.get("dungeon_shard_bank", 0)))
        clear_count_before = dungeon_clear_count(self.flags)
        full_clear_bonus = full_clear_shard_bonus(clear_count_before) if full_clear else 0
        confirmed_shards = shard_bank + full_clear_bonus
        self.party.gold += bank
        if bank:
            self._log(f"심연 누적 보상 {bank}G를 확정했습니다.")
        if confirmed_shards:
            self.flags[SHARD_FLAG] = shard_count(self.flags) + confirmed_shards
            bonus_text = f" (완주 보너스 {full_clear_bonus}개 포함)" if full_clear_bonus else ""
            self._log(f"심연 장비 조각 {confirmed_shards}개를 확정했습니다.{bonus_text}")
        if full_clear:
            clear_count = clear_count_before + 1
            self.flags["dungeon_clear_count"] = clear_count
            party_level = max((member.level for member in self.party.members), default=1)
            equipment = data.generate_random_equipment(
                max(party_level + 2, DUNGEON_MAX_DEPTH + clear_count + 1)
            )
            self.equipment_inventory.append(equipment)
            self._log(f"심연 완주 보상: {equipment.display_name}")
        self.flags["dungeon_active"] = False
        self.flags["dungeon_reward_bank"] = 0
        self.flags["dungeon_shard_bank"] = 0
        self.flags["dungeon_cleared_depth"] = 0
        self.game_map.move_to("village")
        self.enemies = []
        self.phase = "explore"
        self.current_actor = None
        self.result_message = "심연 원정을 마치고 시작 마을로 귀환했습니다."

    def dungeon_action(self, operation: str) -> dict:
        if operation == "enter":
            if self.phase != "explore" or self.game_map.current_id != "village":
                return self._error("심연 원정은 시작 마을에서 준비할 수 있습니다.")
            if not self.flags.get("demon_lord_defeated"):
                return self._error("봉인된 마왕을 처치한 뒤에 입장할 수 있습니다.")
            if self.party.gold < DUNGEON_ENTRY_FEE:
                return self._error(f"입장 준비금 {DUNGEON_ENTRY_FEE}G가 필요합니다.")
            self.party.gold -= DUNGEON_ENTRY_FEE
            self.flags.update({
                "dungeon_active": True, "dungeon_depth": 1,
                "dungeon_cleared_depth": 0, "dungeon_reward_bank": 0,
                "dungeon_shard_bank": 0,
            })
            self.game_map.move_to(DUNGEON_LOCATION_ID)
            self._log(f"{DUNGEON_ENTRY_FEE}G를 사용해 심연 변이 던전에 진입했습니다.")
            self._start_dungeon_floor()
        elif operation == "advance":
            if (
                self.phase != "explore" or self.game_map.current_id != DUNGEON_LOCATION_ID
                or not self.flags.get("dungeon_active")
            ):
                return self._error("현재 심연 원정을 진행하고 있지 않습니다.")
            depth = int(self.flags.get("dungeon_depth", 1))
            if int(self.flags.get("dungeon_cleared_depth", 0)) != depth:
                return self._error("현재 층의 적을 먼저 처치하세요.")
            if depth >= DUNGEON_MAX_DEPTH:
                return self._error("심연 최하층을 이미 돌파했습니다.")
            self.flags["dungeon_depth"] = depth + 1
            self._start_dungeon_floor()
        elif operation == "retreat":
            if (
                self.phase != "explore" or self.game_map.current_id != DUNGEON_LOCATION_ID
                or not self.flags.get("dungeon_active")
            ):
                return self._error("확정할 심연 원정 보상이 없습니다.")
            if int(self.flags.get("dungeon_cleared_depth", 0)) < 1:
                return self._error("첫 층을 돌파해야 안전하게 귀환할 수 있습니다.")
            self._finish_dungeon_run(False)
        else:
            return self._error("지원하지 않는 심연 원정 행동입니다.")
        return {"ok": True, "state": self.state()}

    def boss_action(self, operation: str) -> dict:
        location = self.game_map.current
        if self.phase != "explore":
            return self._error("탐험 중에만 보스에게 다시 도전할 수 있습니다.")
        if operation != "retry":
            return self._error("지원하지 않는 보스 행동입니다.")
        if not location.boss or not location.boss_defeated:
            return self._error("현재 장소에는 다시 도전할 보스가 없습니다.")

        if tower_floor_number(location.id) is not None:
            return self._error("도전의 탑 보스는 한 회차에 한 번만 처치할 수 있습니다. 100층 정복 후 새 도전을 시작하세요.")

        self._begin_battle(location.boss(), "boss_retry", f"{location.name}의 보스 재도전")
        return {"ok": True, "state": self.state()}

    def _forge_quote(self, index, material):
        """Bind confirmation to this session, exact inventory order and resources."""
        snapshot = repr((index, material, self.party.gold,
                         bool(self.flags.get("star_rift_closed")),
                         [(id(item), item) for item in self.equipment_inventory],
                         [item.name for item in self.inventory]))
        return hmac.new(self._forge_key, snapshot.encode(), "sha256").hexdigest()

    def blacksmith_action(self, equipment_index, material="duplicate", quote=None) -> dict:
        if self.phase != "explore" or "blacksmith" not in self.game_map.current.services:
            return self._error("현재 마을에서는 대장간을 이용할 수 없습니다.")
        try:
            index = self._index(
                equipment_index, len(self.equipment_inventory), "강화 장비"
            )
            if not isinstance(quote, str) or not secrets.compare_digest(
                quote, self._forge_quote(index, material)
            ):
                raise ValueError("장비 또는 재료 상태가 변경되었습니다. 새 목록에서 강화 내용을 다시 확인하세요.")
            upgraded, cost = enhance_equipment(
                self.party, self.equipment_inventory, index,
                self.inventory, self.flags, material,
            )
        except (IndexError, TypeError, ValueError) as error:
            return self._error(str(error))
        self._forge_key = secrets.token_bytes(32)
        self._log(f"대장간 강화 성공! {upgraded.display_name} ({cost}G 사용)")
        return {"ok": True, "state": self.state()}

    def _craft_quote(self, operation, target):
        """Bind a crafting confirmation to the exact resources and inventory."""
        snapshot = repr((
            operation, target, self.party.gold, shard_count(self.flags),
            [member.level for member in self.party.members],
            [(id(item), item) for item in self.equipment_inventory],
        ))
        return hmac.new(self._craft_key, snapshot.encode(), "sha256").hexdigest()

    def crafting_action(
        self, operation, equipment_index=None, rarity=None, family=None, quote=None,
        equipment_indices=None, locked_affix="", reforge_token=None,
    ) -> dict:
        if self.phase != "explore" or "crafting" not in self.game_map.current.services:
            return self._error("현재 마을에서는 분해·합성 공방을 이용할 수 없습니다.")
        try:
            if operation == "dismantle":
                index = self._index(
                    equipment_index, len(self.equipment_inventory), "분해 장비"
                )
                if not isinstance(quote, str) or not secrets.compare_digest(
                    quote, self._craft_quote("dismantle", index)
                ):
                    raise ValueError(
                        "장비 또는 재료 상태가 변경되었습니다. 새 목록에서 분해 내용을 다시 확인하세요."
                    )
                item, gained = dismantle_equipment(
                    self.equipment_inventory, index, self.flags
                )
                self._log(
                    f"{item.display_name} 분해 완료! 장비 조각 {gained}개를 얻었습니다."
                )
            elif operation == "bulk_dismantle":
                if not isinstance(quote, str) or not secrets.compare_digest(
                    quote, self._craft_quote("bulk_dismantle", None)
                ):
                    raise ValueError(
                        "장비 상태가 변경되었습니다. 새 목록에서 일괄 분해 내용을 다시 확인하세요."
                    )
                items, gained = dismantle_equipment_many(
                    self.equipment_inventory, equipment_indices, self.flags
                )
                self._log(
                    f"장비 {len(items)}개 일괄 분해 완료! "
                    f"장비 조각 {gained}개를 얻었습니다."
                )
            elif operation == "synthesize":
                target = (rarity, family)
                if not isinstance(quote, str) or not secrets.compare_digest(
                    quote, self._craft_quote("synthesize", target)
                ):
                    raise ValueError(
                        "등급 또는 재료 상태가 변경되었습니다. 새 목록에서 합성 내용을 다시 확인하세요."
                    )
                item, used_shards, gold = synthesize_weapon(
                    self.party, self.equipment_inventory, self.flags, rarity, family,
                )
                self._log(
                    f"무기 합성 성공! {item.display_name} "
                    f"(장비 조각 {used_shards}개 / {gold}G 사용)"
                )
            elif operation == "reforge_preview":
                index = self._index(
                    equipment_index, len(self.equipment_inventory), "재련 장비"
                )
                if not isinstance(quote, str) or not secrets.compare_digest(
                    quote, self._craft_quote("reforge", index)
                ):
                    raise ValueError(
                        "장비 또는 재료 상태가 변경되었습니다. 새 목록에서 재련 내용을 다시 확인하세요."
                    )
                item = self.equipment_inventory[index]
                allowed, reason = can_reforge(
                    self.party, self.flags, item, locked_affix,
                )
                if not allowed:
                    raise ValueError(reason)
                result = preview_reforge(item, locked_affix)
                shards, gold = reforge_cost(item, locked_affix)
                token = secrets.token_urlsafe(24)
                self._reforge_pending = {
                    "token": token,
                    "index": index,
                    "original": item,
                    "result": result,
                    "locked_affix": locked_affix,
                    "gold": self.party.gold,
                    "shards": shard_count(self.flags),
                }
                return {
                    "ok": True,
                    "state": self.state(),
                    "reforge_preview": {
                        "token": token,
                        "before": self._equipment_state(item),
                        "after": self._equipment_state(result),
                        "locked_affix": locked_affix,
                        "shard_cost": shards,
                        "gold_cost": gold,
                    },
                }
            elif operation == "reforge_apply":
                pending = self._reforge_pending
                if (
                    not pending or not isinstance(reforge_token, str)
                    or not secrets.compare_digest(reforge_token, pending["token"])
                    or pending["index"] >= len(self.equipment_inventory)
                    or self.equipment_inventory[pending["index"]] is not pending["original"]
                    or self.party.gold != pending["gold"]
                    or shard_count(self.flags) != pending["shards"]
                ):
                    raise ValueError(
                        "재련 대상 또는 재료 상태가 변경되었습니다. 결과를 다시 미리보세요."
                    )
                item, used_shards, gold = apply_reforge(
                    self.party, self.equipment_inventory, self.flags,
                    pending["index"], pending["result"], pending["locked_affix"],
                )
                self._log(
                    f"옵션 재련 완료! {item.display_name} "
                    f"(장비 조각 {used_shards}개 / {gold}G 사용)"
                )
            else:
                return self._error("지원하지 않는 분해·합성 행동입니다.")
        except (IndexError, TypeError, ValueError) as error:
            return self._error(str(error))
        self._craft_key = secrets.token_bytes(32)
        self._reforge_pending = None
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
                item = self.equipment_inventory[index]
                previous = member.equip(item)
                self.equipment_inventory.pop(index)
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
            elif operation in {"lock", "unlock"}:
                desired = operation == "lock"
                if equipment_index is not None:
                    index = self._index(equipment_index, len(self.equipment_inventory), "장비")
                    item = self.equipment_inventory[index]
                    if item.locked == desired:
                        raise ValueError("이미 같은 보호 상태입니다.")
                    self.equipment_inventory[index] = replace(item, locked=desired)
                    changed = self.equipment_inventory[index]
                else:
                    if slot not in member.equipment or member.equipment[slot] is None:
                        raise ValueError("잠금 상태를 바꿀 장비를 선택하세요.")
                    item = member.equipment[slot]
                    if item.locked == desired:
                        raise ValueError("이미 같은 보호 상태입니다.")
                    member.equipment[slot] = replace(item, locked=desired)
                    changed = member.equipment[slot]
                state_label = "잠금 보호" if desired else "잠금 해제"
                self._log(f"{changed.display_name}: {state_label}했습니다.")
            else:
                return self._error("지원하지 않는 장비 행동입니다.")
        except (IndexError, TypeError, ValueError) as error:
            return self._error(str(error))
        return {"ok": True, "state": self.state()}

    def quest_action(self, operation: str, quest_id: str) -> dict:
        if self.phase != "explore" or "quest_board" not in self.game_map.current.services:
            return self._error("현재 마을에는 이야기 의뢰 게시판이 없습니다.")
        if quest_id not in QUESTS:
            return self._error("존재하지 않는 퀘스트입니다.")
        self.quest_log.refresh_from_world(self.game_map, self.flags)
        if operation == "accept":
            if not self.quest_log.accept(quest_id, self.flags):
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

    def commission_action(self, operation: str) -> dict:
        location = self.game_map.current
        if self.phase != "explore" or not location.is_village or not location.quest_npc:
            return self._error("현재 장소에는 의뢰를 주는 NPC가 없습니다.")
        if operation == "offer":
            _, template = offer_commission(self.flags, location.id)
            self._log(f"{location.quest_npc}이(가) [{template.title}] 의뢰를 제시했습니다.")
        elif operation == "accept":
            view = commission_state(self.flags, location.id)
            if not accept_commission(self.flags, location.id):
                return self._error("지금 수락할 수 있는 NPC 의뢰가 없습니다.")
            self._log(f"NPC 의뢰 [{view['title']}]을(를) 수락했습니다.")
        elif operation == "claim":
            template = claim_commission(
                self.flags, location.id, self.party, self.inventory,
            )
            if template is None:
                return self._error("아직 NPC 의뢰 보상을 받을 수 없습니다.")
            self._log(
                f"NPC 의뢰 [{template.title}] 완료! {template.gold_reward}G와 보상을 받았습니다."
            )
        else:
            return self._error("지원하지 않는 NPC 의뢰 행동입니다.")
        return {"ok": True, "state": self.state()}

    def achievement_action(self, achievement_id: str) -> dict:
        if self.phase != "explore":
            return self._error("탐험 중에만 업적 보상을 받을 수 있습니다.")
        if not isinstance(achievement_id, str):
            return self._error("올바른 업적을 선택하세요.")
        achievement = claim_achievement(
            self.flags, achievement_id, self.party,
            len(self.game_map.visited), len(self.game_map.visited_villages),
        )
        if achievement is None:
            return self._error("아직 달성하지 않았거나 이미 보상을 받은 업적입니다.")
        self._log(
            f"업적 [{achievement.title}] 달성 보상으로 "
            f"{achievement.gold_reward}G를 받았습니다."
        )
        return {"ok": True, "state": self.state()}

    def advancement_action(self, member_index, job_id: str) -> dict:
        if self.phase != "explore" or "advancement" not in self.game_map.current.services:
            return self._error("현재 마을에는 전직 교관이 없습니다.")
        try:
            member = self.party.members[self._index(member_index, len(self.party.members), "파티원")]
            job = advance(member, job_id)
        except ValueError as error:
            return self._error(str(error))
        self._log(f"{member.name}이(가) {job.name}(으)로 전직하고 [{job.skill.name}]을(를) 습득했습니다!")
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
                self._forge_key = secrets.token_bytes(32)
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
            tower_floor = tower_floor_number(location.id)
            enemies = ([create_scaled_tower_boss(tower_floor, self.flags)]
                       if tower_floor else location.boss())
            title = (f"{location.name} · {tower_challenge_tier(self.flags)}단계"
                     if tower_floor else f"{location.name}의 보스")
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
        self.combo.reset()
        self.protection.reset()
        self.current_actor = None
        self.battle_context = context
        for name in discover_enemies(self.flags, enemies):
            self._log(f"적 도감 신규 등록: {name}")
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
                bonus = self.combo.bonus(actor, target)
                damage = actor.basic_attack(target, bonus_power=bonus)
                landed = not target.last_damage_evaded
                finisher = self.combo.apply_finisher(actor, target, landed)
                self.combo.record(actor, target, landed)
                if target.last_damage_evaded:
                    self._log(f"{target.name}이(가) {actor.name}의 공격을 회피했습니다.")
                else:
                    critical = " 치명타!" if actor.last_attack_was_critical else ""
                    self._log(f"{actor.name} → {target.name}: {damage} 피해.{critical}")
                    if bonus:
                        self._log(f"연계 공격! 추가 위력 +{bonus}")
                    if finisher:
                        self._log(finisher)
            elif action_type == "skill":
                self._use_skill(actor, action)
            elif action_type == "item":
                self._use_item(action)
                self.combo.reset()
            elif action_type == "defend":
                actor.guarding = True
                self.combo.reset()
                self._log(f"{actor.name}이(가) 방어 태세를 취했습니다.")
            elif action_type == "protect":
                allies = self.party.alive_members
                target = allies[self._index(action.get("target"), len(allies), "엄호 대상")]
                self.protection.protect(actor, target)
                actor.guarding = True
                self.combo.reset()
                self._log(f"{actor.name}이(가) 방어 태세로 {target.name}을(를) 엄호합니다.")
            elif action_type == "flee":
                self.combo.reset()
                if self._attempt_flee():
                    return {"ok": True, "state": self.state()}
            else:
                return self._error("지원하지 않는 행동입니다.")
        except (IndexError, TypeError, ValueError) as error:
            return self._error(str(error) or "행동을 처리할 수 없습니다.")

        self.current_actor = None
        self._advance()
        return {"ok": True, "state": self.state()}

    def auto_action(self, strategy: str = "balanced") -> dict:
        """현재 파티원의 상황을 판단해 한 번의 행동만 안전하게 실행한다."""
        if self.phase != "battle" or self.current_actor is None:
            return self._error("자동 전투로 처리할 파티원 행동이 없습니다.")
        if not isinstance(strategy, str) or strategy not in AUTO_BATTLE_STRATEGIES:
            return self._error("지원하지 않는 자동 전투 전술입니다.")
        try:
            action, description = self._choose_auto_action(strategy)
        except ValueError as error:
            return self._error(str(error))
        label = AUTO_BATTLE_STRATEGIES[strategy]["label"]
        self._log(f"자동 전투[{label}] · {self.current_actor.name}: {description}")
        return self.act(action)

    def _choose_auto_action(self, strategy: str = "balanced") -> tuple[dict, str]:
        actor = self.current_actor
        allies = self.party.alive_members
        enemies = [enemy for enemy in self.enemies if enemy.is_alive]
        if actor is None or not enemies:
            raise ValueError("자동 전투 행동을 선택할 수 없습니다.")
        settings = AUTO_BATTLE_STRATEGIES.get(strategy) if isinstance(strategy, str) else None
        if settings is None:
            raise ValueError("지원하지 않는 자동 전투 전술입니다.")

        affordable = [
            (index, skill) for index, skill in enumerate(actor.skills)
            if actor.mp >= skill.mp_cost
        ]
        wounded = sorted(allies, key=lambda member: member.hp / member.effective_max_hp)
        lowest = wounded[0]
        lowest_ratio = lowest.hp / lowest.effective_max_hp
        heal_skills = [(index, skill) for index, skill in affordable if skill.kind == "heal"]
        if heal_skills and lowest_ratio <= settings["heal_threshold"]:
            widespread = sum(
                member.hp / member.effective_max_hp <= 0.70 for member in allies
            ) >= 2
            candidates = [entry for entry in heal_skills if entry[1].aoe == widespread]
            if not candidates:
                candidates = heal_skills
            skill_index, skill = max(candidates, key=lambda entry: entry[1].power)
            action = {"type": "skill", "skill": skill_index}
            if not skill.aoe:
                action["target"] = allies.index(lowest)
            target_label = "파티 전체" if skill.aoe else lowest.name
            return action, f"[{skill.name}] → {target_label} 회복"

        if lowest is actor and lowest_ratio <= settings["defend_threshold"]:
            return {"type": "defend"}, "위험한 체력으로 방어"

        buff_skills = [
            (index, skill) for index, skill in affordable
            if skill.kind == "buff"
            and not actor.has_status(f"buff_{skill.buff_stat}")
        ]
        if buff_skills:
            skill_index, skill = max(
                buff_skills,
                key=lambda entry: entry[1].buff_amount * entry[1].buff_duration,
            )
            action = {"type": "skill", "skill": skill_index}
            if not skill.aoe:
                action["target"] = allies.index(actor)
            return action, f"[{skill.name}] 강화"

        preferred_target = (
            self.combo.target
            if self.combo.target in enemies and can_chain(actor) and self.combo.actor is not actor
            else min(enemies, key=lambda enemy: (enemy.hp, enemy.effective_defense))
        )
        debuff_skills = [
            (index, skill) for index, skill in affordable
            if skill.kind == "debuff"
            and not preferred_target.has_status(f"debuff_{skill.buff_stat}")
        ]
        if debuff_skills:
            skill_index, skill = max(
                debuff_skills,
                key=lambda entry: entry[1].buff_amount * entry[1].buff_duration,
            )
            action = {"type": "skill", "skill": skill_index}
            if not skill.aoe:
                action["target"] = enemies.index(preferred_target)
            return action, f"[{skill.name}] → {preferred_target.name} 약화"

        attack_options = []
        for skill_index, skill in affordable:
            if skill.kind == "steal":
                target = next(
                    (enemy for enemy in enemies if not enemy.has_been_stolen_from), None
                )
                if target is not None:
                    attack_options.append((3, skill_index, skill, target))
                continue
            if skill.kind != "attack":
                continue
            if skill.aoe:
                score = skill.power * len(enemies)
                score += sum(
                    4 for enemy in enemies
                    if skill.element and skill.element == enemy.weakness
                )
                score -= sum(
                    3 for enemy in enemies
                    if skill.element and skill.element == enemy.resistance
                )
                target = preferred_target
            else:
                target = max(
                    enemies,
                    key=lambda enemy: (
                        bool(skill.element and skill.element == enemy.weakness),
                        not skill.element or skill.element != enemy.resistance,
                        -enemy.hp,
                    ),
                )
                score = skill.power
                if skill.element and skill.element == target.weakness:
                    score += 5
                elif skill.element and skill.element == target.resistance:
                    score -= 4
                if skill.inflict_status and not target.has_status(skill.inflict_status):
                    score += 2
            if skill.mp_cost == 0:
                score += 2
            attack_options.append((score, skill_index, skill, target))

        basic_score = max(
            1,
            actor.effective_attack - preferred_target.effective_defense // 2
            + self.combo.bonus(actor, preferred_target),
        )
        if attack_options:
            score, skill_index, skill, target = max(attack_options, key=lambda entry: entry[0])
            if score > basic_score + settings["skill_margin"]:
                action = {"type": "skill", "skill": skill_index}
                if not skill.aoe:
                    action["target"] = enemies.index(target)
                target_label = "적 전체" if skill.aoe else target.name
                return action, f"[{skill.name}] → {target_label}"

        return (
            {"type": "attack", "target": enemies.index(preferred_target)},
            f"기본 공격 → {preferred_target.name}",
        )

    def _start_round(self) -> None:
        self.combo.reset()
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
                self.combo.reset()
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
                self.protection.clear_protector(actor)
                actor.guarding = False

            paralyzed = actor.is_paralyzed()
            for message in actor.tick_status_effects():
                self._log(message)
            if not actor.is_alive:
                continue
            if paralyzed:
                if isinstance(actor, PlayerCharacter):
                    self.combo.reset()
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
            if self.battle_context == "dungeon":
                lost = max(0, int(self.flags.get("dungeon_reward_bank", 0)))
                lost_shards = max(0, int(self.flags.get("dungeon_shard_bank", 0)))
                self.flags["dungeon_active"] = False
                self.flags["dungeon_reward_bank"] = 0
                self.flags["dungeon_shard_bank"] = 0
                self.flags["dungeon_cleared_depth"] = 0
                for member in self.party.members:
                    member.hp = max(1, member.effective_max_hp // 4)
                    member.mp = 0
                    member.status_effects = []
                    member.guarding = False
                self.game_map.move_to("village")
                self.enemies = []
                self.phase = "explore"
                self.battle_context = ""
                self.current_actor = None
                self.result_message = "심연에서 구조되어 시작 마을로 돌아왔습니다."
                self._log(
                    f"심연 원정 실패. 누적 보상 {lost}G와 "
                    f"장비 조각 {lost_shards}개를 잃었습니다."
                )
                return True
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
        for title in record_defeats(self.flags, [enemy.name for enemy in self.enemies]):
            self._log(f"NPC 의뢰 [{title}]의 목표를 달성했습니다.")
        for name in record_enemy_defeats(self.flags, self.enemies):
            self._log(f"적 도감 숙련 달성: {name}을(를) 5회 처치했습니다.")
        self.current_actor = None
        context = self.battle_context
        self.battle_context = ""
        if context in {"boss", "boss_retry"}:
            location = self.game_map.current
            tower_floor = tower_floor_number(location.id)
            if tower_floor:
                reward_gold, reward_equipment = grant_tower_boss_reward(
                    self.flags, tower_floor, self.party, self.equipment_inventory
                )
                reward_text = f"{reward_gold}G"
                if reward_equipment:
                    reward_text += f", {reward_equipment.display_name}"
                self._log(f"도전의 탑 {tower_floor}층 보스 보상: {reward_text}")
            if location.id == "tower_summit":
                clear_count, bonus_gold, equipment = complete_tower_challenge(
                    self.flags, self.party, self.equipment_inventory
                )
                if clear_count == 1:
                    self._log("도전의 탑 100층을 최초로 정복했습니다!")
                else:
                    self._log(
                        f"도전의 탑 {clear_count}회 클리어 보상: "
                        f"{bonus_gold}G, {equipment.display_name}"
                    )
            first_clear = not location.boss_defeated
            location.boss_defeated = True
            if location.id == "echo_vault":
                self.flags["echo_purified"] = True
            if location.id == "final_chamber":
                self.flags["demon_lord_defeated"] = True
            if location.id == "star_rift":
                self._log(award_star_ore(self.flags, self.inventory))
                if first_clear:
                    from world import star_chapter_epilogue
                    for line in star_chapter_epilogue(self.flags):
                        self._log(line)
            if location.id == "void_throne":
                self.flags["void_observer_defeated"] = True
                if first_clear:
                    from world import astral_chapter_epilogue
                    for line in astral_chapter_epilogue(self.flags):
                        self._log(line)
            if location.id == "nameless_sanctum":
                self.flags["nameless_swordmaster_defeated"] = True
            self.quest_log.refresh_from_world(self.game_map, self.flags)
            if first_clear:
                self._log(f"{location.name}의 위험이 사라졌습니다.")
            elif location.id == "final_chamber":
                self._log(f"{location.name}의 보스를 다시 쓰러뜨렸습니다. 다시 이곳에 오면 재도전할 수 있습니다.")
            else:
                self._log(
                    f"{location.name}의 보스를 다시 쓰러뜨렸습니다. "
                    "이 장소에서 언제든 재도전할 수 있습니다."
                )
            self._after_location_dialogue()
            if location.id == "final_chamber":
                ending = self.game_map.locations["ending"]
                if ending.dialogue and not ending.dialogue_played:
                    node = ending.dialogue.nodes[ending.dialogue.start_id]
                    for line in node.resolve_lines(self.flags):
                        self._log(line)
                    if node.effect:
                        node.effect(self.flags)
                    ending.dialogue_played = True
                self.game_map.move_to("village")
                self._log("빛의 마법진이 파티를 시작 마을로 돌려보냈습니다.")
                self._enter_current_location()
                if self.phase == "explore":
                    self.result_message = "최종 보스를 처치하고 시작 마을로 귀환했습니다."
        elif context == "random":
            self._enter_current_location()
        elif context == "dungeon":
            depth = int(self.flags.get("dungeon_depth", 1))
            modifier = {
                "reward": float(self.flags.get("dungeon_modifier_reward", 1.0)),
            }
            earned = floor_bank_reward(depth, modifier, dungeon_clear_count(self.flags))
            earned_shards = floor_shard_reward(depth)
            self.flags["dungeon_reward_bank"] = int(
                self.flags.get("dungeon_reward_bank", 0)
            ) + earned
            self.flags["dungeon_shard_bank"] = int(
                self.flags.get("dungeon_shard_bank", 0)
            ) + earned_shards
            self.flags["dungeon_cleared_depth"] = depth
            self.phase = "explore"
            self.result_message = (
                f"심연 {depth}층 돌파 · 누적 보상 "
                f"{self.flags['dungeon_reward_bank']}G / 장비 조각 "
                f"{self.flags['dungeon_shard_bank']}개"
            )
            self._log(
                f"심연 {depth}층 보상 {earned}G와 장비 조각 "
                f"{earned_shards}개가 임시 보관되었습니다."
            )
            if depth >= DUNGEON_MAX_DEPTH:
                self._finish_dungeon_run(True)
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
            self.combo.reset()
        else:
            target_index = self._index(action.get("target"), len(candidates), "대상")
            target = candidates[target_index]
            bonus = self.combo.bonus(actor, target, skill)
            attack_skill = replace(skill, power=skill.power + bonus) if bonus else skill
            amount, status_applied, effectiveness = actor.use_skill(attack_skill, target)
            landed = not target.last_damage_evaded
            finisher = self.combo.apply_finisher(actor, target, landed, skill)
            self.combo.record(actor, target, landed, skill)
            if bonus:
                self._log(f"연계 공격! 추가 위력 +{bonus}")
            if finisher:
                self._log(finisher)
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
        if enemy.last_phase_message:
            self.phase_transition_id += 1
            self.phase_transition_message = enemy.last_phase_message
            self._log(f"★ {enemy.last_phase_message}")
        if target is None:
            return
        if skill is None:
            target, protection_message = self.protection.redirect(target)
            if protection_message:
                self._log(protection_message)
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
                target, protection_message = self.protection.redirect(target, skill)
                if protection_message:
                    self._log(protection_message)
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
        if self.battle_context == "dungeon":
            self._log("심연 변이 던전에서는 전투 중 도망칠 수 없습니다.")
            return False
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

    def _turn_timeline_state(self) -> dict:
        if self.phase != "battle":
            return {"current_round": [], "next_round": []}

        def entry(character, current=False):
            enemy = isinstance(character, Enemy)
            intent = character.preview_intent(self.party.alive_members) if enemy else None
            return {
                "name": character.name,
                "side": "enemy" if enemy else "party",
                "speed": character.effective_speed,
                "current": current,
                "intent": (
                    f"{intent['action']} → {intent['target']}" if intent else ""
                ),
            }

        remaining = []
        if self.current_actor is not None and self.current_actor.is_alive:
            remaining.append(entry(self.current_actor, current=True))
        remaining.extend(
            entry(character)
            for character in self._order[self._cursor:]
            if character.is_alive
        )
        combatants = [
            *self.party.alive_members,
            *[enemy for enemy in self.enemies if enemy.is_alive],
        ]
        forecast = sorted(
            combatants, key=lambda character: character.effective_speed, reverse=True,
        )
        return {
            "current_round": remaining,
            "next_round": [entry(character) for character in forecast],
        }

    @staticmethod
    def _character_state(character) -> dict:
        state = {
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
        if isinstance(character, PlayerCharacter):
            state["base_job"] = character.base_job
            state["allowed_weapon_families"] = [
                {"id": family, "name": WEAPON_FAMILIES[family]}
                for family in character.allowed_weapon_families
            ]
        return state

    @staticmethod
    def _equipment_state(item) -> dict:
        return {
            "name": item.name,
            "display_name": item.display_name,
            "slot": item.slot,
            "slot_name": SLOT_NAMES_KR[item.slot],
            "weapon_family": item.weapon_family,
            "family_label": item.family_label,
            "description": item.display_description,
            "special_effect": item.special_effect,
            "price": item.price,
            "rarity": item.rarity,
            "enhancement_level": item.enhancement_level,
            "locked": item.locked,
            "protection_warning": protection_warning(item),
        }

    def _map_state(self) -> dict:
        """전체 권역 지도와 현재 권역의 세부 지도를 분리해 구성한다."""
        current_region = region_for_location(self.game_map.current_id)
        world_regions = []
        for region in MAP_REGIONS:
            visited_count = sum(
                location_id in self.game_map.visited
                for location_id in region["locations"]
            )
            unlock_flag = region.get("unlock_flag", "")
            unlock_check = region.get("unlock_check")
            unlocked = (
                bool(unlock_check(self.flags)) if unlock_check
                else not unlock_flag or bool(self.flags.get(unlock_flag))
            )
            world_regions.append({
                "id": region["id"],
                "name": region["name"],
                "description": region["description"],
                "current": region["id"] == current_region["id"],
                "visited": visited_count > 0,
                "visited_count": visited_count,
                "total_count": len(region["locations"]),
                "locked": not unlocked,
                "lock_reason": region.get("unlock_description", ""),
            })

        region_ids = set(current_region["locations"])
        visible_ids = set(self.game_map.visited) & region_ids
        links = []
        seen_links = set()
        inbound_locks = {location_id: [] for location_id in region_ids}
        for origin_id in current_region["locations"]:
            origin = self.game_map.locations[origin_id]
            for label, target_id in origin.exits.items():
                if target_id not in region_ids:
                    continue
                requirement = origin.flag_requirements.get(label)
                flag_locked = bool(requirement and not requirement.is_met(self.flags))
                item_locked = label in origin.locked_exits and label not in origin.unlocked_labels
                locked = flag_locked or item_locked
                reason = (
                    requirement.description if flag_locked
                    else origin.locked_exits.get(label, "") if item_locked else ""
                )
                if origin_id in self.game_map.visited or target_id in self.game_map.visited:
                    visible_ids.update((origin_id, target_id))
                    edge_key = tuple(sorted((origin_id, target_id)))
                    if edge_key not in seen_links:
                        links.append({
                            "from": origin_id, "to": target_id,
                            "locked": locked, "lock_reason": reason,
                        })
                        seen_links.add(edge_key)
                if origin_id in self.game_map.visited:
                    inbound_locks[target_id].append((locked, reason))

        local_locations = []
        for location_id in current_region["locations"]:
            location = self.game_map.locations[location_id]
            routes = inbound_locks[location_id]
            locked_routes = bool(routes and all(route[0] for route in routes))
            lock_reason = next((reason for locked, reason in routes if locked and reason), "")
            local_locations.append({
                "id": location_id,
                "name": location.name if location_id in visible_ids else "미발견 장소",
                "current": location_id == self.game_map.current_id,
                "visited": location_id in self.game_map.visited,
                "visible": location_id in visible_ids,
                "locked": locked_routes,
                "lock_reason": lock_reason,
                "boss_defeated": location.boss_defeated,
            })

        return {
            "current_region_id": current_region["id"],
            "world": world_regions,
            "region": {
                "id": current_region["id"],
                "name": current_region["name"],
                "description": current_region["description"],
                "visited_count": sum(item["visited"] for item in local_locations),
                "total_count": len(local_locations),
                "locations": local_locations,
                "links": links,
            },
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
            requirement = location.flag_requirements.get(label)
            flag_locked = bool(requirement and not requirement.is_met(self.flags))
            item_locked = label in location.locked_exits and label not in location.unlocked_labels
            locked = flag_locked or item_locked
            exits.append({
                "label": label,
                "target_id": target_id,
                "target_name": self.game_map.locations[target_id].name,
                "locked": locked,
                "required_item": location.locked_exits.get(label) if item_locked else None,
                "lock_reason": (
                    requirement.description if flag_locked
                    else location.locked_exits.get(label) if item_locked else None
                ),
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
                "shops": [
                    {
                        "index": shop_index,
                        "name": shop.name,
                        "description": shop.description,
                        "available": shop.is_available(self.flags),
                        "unlock_description": shop.unlock_description,
                        "discount_rate": shop.active_discount(self.flags),
                        "discount_description": (
                            shop.discount_description if shop.active_discount(self.flags) else ""
                        ),
                        "items": [
                            {
                                "index": index, "name": item.name,
                                "price": shop.price_for(item, self.flags),
                                "base_price": item.price,
                                "description": item.description,
                            }
                            for index, item in enumerate(shop.items)
                        ],
                        "equipment": [
                            {
                                "index": index, **self._equipment_state(item),
                                "price": shop.price_for(item, self.flags),
                                "base_price": item.price,
                            }
                            for index, item in enumerate(shop.equipment)
                        ],
                    }
                    for shop_index, shop in enumerate(location.shops)
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
                        "shard_yield": dismantle_value(item),
                        "can_dismantle_here": "crafting" in location.services,
                    }
                    for index, item in enumerate(self.equipment_inventory)
                    if not item.locked
                ],
            }
        blacksmith_state = None
        crafting_state = None
        if {"blacksmith", "crafting"}.issubset(location.services):
            blacksmith_equipment = []
            for index, item in enumerate(self.equipment_inventory):
                allowed, reason = can_upgrade(
                    self.party, self.equipment_inventory, index
                )
                star_allowed, star_reason = can_upgrade(
                    self.party, self.equipment_inventory, index,
                    self.inventory, self.flags, "star_ore",
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
                    "preview": upgrade_preview_text(item),
                    "quote": self._forge_quote(index, "duplicate"),
                    "star_quote": self._forge_quote(index, "star_ore"),
                    "reason": reason,
                    "star_ore_cost": star_ore_cost(item),
                    "can_star_upgrade": star_allowed,
                    "star_reason": star_reason,
                })
            blacksmith_state = {
                "max_level": MAX_ENHANCEMENT,
                "equipment": blacksmith_equipment,
                "star_unlocked": bool(self.flags.get("star_rift_closed")),
                "star_ore_count": sum(item.name == STAR_ORE_NAME for item in self.inventory),
            }
            crafting_recipes = []
            for rarity in EQUIPMENT_RARITIES:
                shard_cost, gold_cost = SYNTHESIS_RECIPES[rarity]
                allowed, reason = can_synthesize(
                    self.party, self.flags, rarity, next(iter(WEAPON_FAMILIES))
                )
                previews = {}
                for family in WEAPON_FAMILIES:
                    preview = synthesis_preview(self.party, rarity, family)
                    previews[family] = {
                        **preview,
                        "stat_text": preview_stat_text(preview),
                    }
                crafting_recipes.append({
                    "rarity": rarity,
                    "rarity_name": RARITY_NAMES_KR[rarity],
                    "shard_cost": shard_cost,
                    "gold_cost": gold_cost,
                    "can_synthesize": allowed,
                    "reason": reason,
                    "previews": previews,
                    "quotes": {
                        family: self._craft_quote("synthesize", (rarity, family))
                        for family in WEAPON_FAMILIES
                    },
                })
            crafting_state = {
                "shards": shard_count(self.flags),
                "enhancement_bonuses": [
                    {"level": level, "shards": shards}
                    for level, shards in ENHANCEMENT_DISMANTLE_BONUS.items()
                    if level > 0
                ],
                "families": [
                    {"id": family, "name": name}
                    for family, name in WEAPON_FAMILIES.items()
                ],
                "dismantle": [
                    {
                        "index": index,
                        **self._equipment_state(item),
                        "shard_yield": dismantle_value(item),
                        "sale_price": int(item.price * SELL_RATIO),
                        "quote": self._craft_quote("dismantle", index),
                        "bulk_eligible": not bulk_dismantle_reason(item),
                        "bulk_exclusion_reason": bulk_dismantle_reason(item),
                        "compatible_with_party": (
                            item.slot != "weapon"
                            or not item.weapon_family
                            or any(
                                item.weapon_family in member.allowed_weapon_families
                                for member in self.party.members
                            )
                        ),
                    }
                    for index, item in enumerate(self.equipment_inventory)
                    if not item.locked
                ],
                "reforge": [
                    {
                        "index": index,
                        **self._equipment_state(item),
                        "affixes": equipment_affixes(item),
                        "base_shard_cost": reforge_cost(item)[0],
                        "base_gold_cost": reforge_cost(item)[1],
                        "lock_shard_cost": reforge_cost(item, equipment_affixes(item)[0])[0],
                        "lock_gold_cost": reforge_cost(item, equipment_affixes(item)[0])[1],
                        "can_reforge": can_reforge(self.party, self.flags, item)[0],
                        "reason": can_reforge(self.party, self.flags, item)[1],
                        "quote": self._craft_quote("reforge", index),
                    }
                    for index, item in enumerate(self.equipment_inventory)
                    if item.generated and item.rarity in REFORGE_COSTS
                    and equipment_affixes(item)
                ],
                "bulk_dismantle_quote": self._craft_quote("bulk_dismantle", None),
                "recipes": crafting_recipes,
            }
        slots = [
            {"slot": number, "exists": exists, "summary": summary}
            for number, exists, summary in game_save.list_slots(save_dir=self.save_dir)
        ]
        enemy_intents = {
            id(enemy): enemy.preview_intent(self.party.alive_members)
            for enemy in self.enemies
        }
        incoming_threats = {id(member): [] for member in self.party.members}
        if self.phase == "battle":
            members_by_name = {member.name: member for member in self.party.alive_members}
            for enemy in self.enemies:
                intent = enemy_intents[id(enemy)]
                if not enemy.is_alive or intent["target_type"] not in ("single", "all"):
                    continue
                for target_name in intent["target_names"]:
                    member = members_by_name.get(target_name)
                    if member is not None:
                        incoming_threats[id(member)].append({
                            "enemy": enemy.name,
                            "action": intent["action"],
                            "phase": intent["phase"],
                            "aoe": intent["target_type"] == "all",
                        })
        return {
            "phase": self.phase,
            "turn": self.turn,
            "result_message": self.result_message,
            "gold": self.party.gold,
            "party": [
                {
                    **self._character_state(member),
                    "guarded_by": (
                        self.protection.protector_for(member).name
                        if self.phase == "battle" and self.protection.protector_for(member) else ""
                    ),
                    "targeted_by": incoming_threats[id(member)],
                }
                for member in self.party.members
            ],
            "enemies": [
                {
                    **self._character_state(enemy),
                    "weakness": enemy.weakness,
                    "resistance": enemy.resistance,
                    "boss": enemy.job in BOSS_JOBS,
                    "intent": enemy_intents[id(enemy)],
                }
                for enemy in self.enemies
            ],
            "current_actor": actor.name if actor else None,
            "turn_timeline": self._turn_timeline_state(),
            "combo": {
                "target": self.enemies.index(self.combo.target)
                if self.combo.target in self.enemies and self.combo.target.is_alive else None,
                "streak": self.combo.streak,
                "eligible": bool(actor and can_chain(actor) and self.combo.actor is not actor),
                "next_bonus": (
                    self.combo.bonus(actor, self.combo.target)
                    if actor and self.combo.target in self.enemies and self.combo.target.is_alive else 0
                ),
                "finisher": (
                    self.combo.finisher_name(actor, self.combo.target)
                    if actor and self.combo.target in self.enemies and self.combo.target.is_alive else ""
                ),
            },
            "skills": skills,
            "items": [
                {"index": index, "name": item.name, "description": item.description}
                for index, item in enumerate(usable_items)
            ],
            "inventory_count": len(self.inventory),
            "equipment_count": len(self.equipment_inventory),
            "logs": self.logs,
            "phase_transition_id": self.phase_transition_id,
            "phase_transition_message": self.phase_transition_message,
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
            "maps": self._map_state(),
            "dialogue": dialogue_state,
            "story_flags": dict(self.flags),
            "bestiary": bestiary_state(self.flags),
            "achievements": achievement_state(
                self.flags, len(self.game_map.visited),
                len(self.game_map.visited_villages),
            ),
            "quests": [
                {
                    "id": quest_id,
                    "title": definition.title,
                    "status": self.quest_log.display_status(quest_id, self.flags),
                    "objective": definition.objective,
                    "description": definition.description,
                    "gold_reward": definition.gold_reward,
                    "bonus_gold_reward": definition.bonus_gold_reward,
                }
                for quest_id, definition in QUESTS.items()
            ],
            "quest_board": "quest_board" in location.services,
            "advancement_service": "advancement" in location.services,
            "village": {
                "is_village": location.is_village,
                "npc": location.quest_npc,
                "travel": [
                    {"id": village.id, "name": village.name}
                    for village in self.game_map.visited_villages
                    if village is not location
                ],
                "commission": (
                    commission_state(self.flags, location.id)
                    if location.quest_npc else None
                ),
            },
            "advancement": [
                {
                    "member": index,
                    "name": member.name,
                    "job": member.job,
                    "level": member.level,
                    "eligible": member.level >= ADVANCEMENT_LEVEL and not member.advanced_job_id,
                    "advanced_job_id": member.advanced_job_id,
                    "required_level": ADVANCEMENT_LEVEL,
                    "options": [
                        {"id": job.id, "name": job.name, "description": job.description,
                         "skill": job.skill.name}
                        for job in options_for(member)
                    ] if not member.advanced_job_id else [],
                }
                for index, member in enumerate(self.party.members)
            ],
            "shop": shop_state,
            "blacksmith": blacksmith_state,
            "crafting": crafting_state,
            "inn": location.has_inn,
            "boss_retry": {
                "available": (
                    self.phase == "explore"
                    and bool(location.boss)
                    and location.boss_defeated
                    and tower_floor_number(location.id) is None
                ),
                "location_name": location.name,
            },
            "tower": {
                "clear_count": tower_clear_count(self.flags),
                "next_tier": tower_challenge_tier(self.flags),
                "max_floor": TOWER_MAX_FLOOR,
                "current_floor": tower_floor_number(location.id) or 0,
                "highest_floor": int(self.flags.get("tower_highest_floor", 0)),
                "next_boss_floor": min(
                    TOWER_MAX_FLOOR,
                    ((int(self.flags.get("tower_highest_floor", 0)) // 5) + 1) * 5,
                ),
                "can_retry": (
                    location.id == "village"
                    and self.game_map.locations["tower_summit"].boss_defeated
                ),
                "active": bool(self.flags.get("tower_challenge_active")),
            },
            "dungeon": {
                "unlocked": bool(self.flags.get("demon_lord_defeated")),
                "entry_fee": DUNGEON_ENTRY_FEE,
                "active": bool(self.flags.get("dungeon_active")),
                "depth": int(self.flags.get("dungeon_depth", 0)),
                "max_depth": DUNGEON_MAX_DEPTH,
                "cleared_depth": int(self.flags.get("dungeon_cleared_depth", 0)),
                "reward_bank": int(self.flags.get("dungeon_reward_bank", 0)),
                "shard_bank": int(self.flags.get("dungeon_shard_bank", 0)),
                "full_clear_shard_bonus": full_clear_shard_bonus(
                    dungeon_clear_count(self.flags)
                ),
                "modifier": self.flags.get("dungeon_modifier_name", ""),
                "modifier_description": self.flags.get("dungeon_modifier_description", ""),
                "clear_count": dungeon_clear_count(self.flags),
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
        if not isinstance(payload, dict):
            self._json({"ok": False, "error": "JSON 요청은 객체 형식이어야 합니다."}, 400)
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
            elif self.path == "/api/travel":
                result = game.travel_action(payload.get("target", ""))
            elif self.path == "/api/dialogue":
                result = game.advance_dialogue(payload.get("choice"))
            elif self.path == "/api/shop":
                result = game.shop_action(
                    payload.get("operation", ""), payload.get("index"),
                    payload.get("shop", 0),
                )
            elif self.path == "/api/inn":
                result = game.inn_action()
            elif self.path == "/api/blacksmith":
                result = game.blacksmith_action(
                    payload.get("equipment"),
                    payload.get("material", "duplicate"),
                    payload.get("quote"),
                )
            elif self.path == "/api/crafting":
                result = game.crafting_action(
                    payload.get("operation", ""), payload.get("equipment"),
                    payload.get("rarity"), payload.get("family"),
                    payload.get("quote"), payload.get("equipment_indices"),
                    payload.get("locked_affix", ""), payload.get("reforge_token"),
                )
            elif self.path == "/api/tower":
                result = game.tower_action(payload.get("operation", ""))
            elif self.path == "/api/dungeon":
                result = game.dungeon_action(payload.get("operation", ""))
            elif self.path == "/api/boss":
                result = game.boss_action(payload.get("operation", ""))
            elif self.path == "/api/equipment":
                result = game.equipment_action(
                    payload.get("operation", ""), payload.get("member"),
                    payload.get("equipment"), payload.get("slot"),
                )
            elif self.path == "/api/quest":
                result = game.quest_action(payload.get("operation", ""), payload.get("quest", ""))
            elif self.path == "/api/commission":
                result = game.commission_action(payload.get("operation", ""))
            elif self.path == "/api/achievement":
                result = game.achievement_action(payload.get("achievement", ""))
            elif self.path == "/api/advancement":
                result = game.advancement_action(payload.get("member"), payload.get("job", ""))
            elif self.path == "/api/save":
                result = game.save_action(
                    payload.get("operation", ""), payload.get("slot"), payload.get("backup")
                )
            elif self.path == "/api/action":
                result = game.act(payload)
            elif self.path == "/api/auto":
                result = game.auto_action(payload.get("strategy", "balanced"))
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
            "no-cache"
            if candidate.name in {
                "index.html", "app.js", "styles.css", "sw.js", "manifest.webmanifest",
            }
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
