"""
save.py
파티 상태 / 골드 / 인벤토리 / 장비 / 맵 진행 상황 / 스토리 flags를 JSON 파일로 저장하고 불러옵니다.

주의: 게임 규칙(캐릭터 능력치 필드 등)을 models.py에서 바꾸면
      _character_to_dict / _character_from_dict 도 함께 맞춰줘야 합니다.
"""

import json
import os
import shutil
import tempfile
from datetime import datetime
from typing import List, Optional, Tuple

from models import (
    PlayerCharacter, Party, Item, Equipment, StatusEffect,
    EQUIPMENT_SLOTS, EQUIPMENT_RARITIES,
)
from map import GameMap
import data
from input_utils import prompt_index, prompt_yes_no

SAVE_DIR = os.path.abspath(
    os.environ.get(
        "RPG_SAVE_DIR",
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "saves"),
    )
)
MAX_SLOTS = 3
SAVE_VERSION = 8


class SaveGameError(ValueError):
    """저장 파일의 형식이나 콘텐츠가 현재 게임과 맞지 않을 때 발생합니다."""


def slot_path(slot: int, save_dir: Optional[str] = None) -> str:
    return os.path.join(save_dir or SAVE_DIR, f"slot{slot}.json")


DEFAULT_SAVE_PATH = slot_path(1)  # path를 직접 안 넘기면 슬롯 1을 사용 (예전 단일 저장 방식과 호환)


# ---------------------------------------------------------------------------
# 캐릭터 <-> dict 변환
# ---------------------------------------------------------------------------
def _equipment_to_dict(eq: Equipment) -> dict:
    return {
        "name": eq.name,
        "slot": eq.slot,
        "attack_bonus": eq.attack_bonus,
        "defense_bonus": eq.defense_bonus,
        "speed_bonus": eq.speed_bonus,
        "max_hp_bonus": eq.max_hp_bonus,
        "max_mp_bonus": eq.max_mp_bonus,
        "description": eq.description,
        "price": eq.price,
        "rarity": eq.rarity,
        "critical_rate_bonus": eq.critical_rate_bonus,
        "evasion_rate_bonus": eq.evasion_rate_bonus,
        "damage_reduction_bonus": eq.damage_reduction_bonus,
        "special_effect": eq.special_effect,
        "generated": eq.generated,
        "enhancement_level": eq.enhancement_level,
    }


def _equipment_from_data(record):
    """버전 1~5의 이름 문자열과 버전 6의 전체 장비 데이터를 모두 읽는다."""
    if record is None:
        return None
    if isinstance(record, str):
        if record not in data.EQUIPMENT_BY_NAME:
            raise SaveGameError(f"알 수 없는 장비: {record}")
        return data.EQUIPMENT_BY_NAME[record]
    if not isinstance(record, dict):
        raise SaveGameError("장비 데이터 형식이 올바르지 않습니다.")

    required = {"name", "slot"}
    missing = required - set(record)
    if missing:
        raise SaveGameError(f"장비 필수 항목이 없습니다: {sorted(missing)}")
    if record["slot"] not in EQUIPMENT_SLOTS:
        raise SaveGameError(f"알 수 없는 장비 슬롯입니다: {record['slot']}")
    rarity = record.get("rarity", "common")
    if rarity not in EQUIPMENT_RARITIES:
        raise SaveGameError(f"알 수 없는 장비 등급입니다: {rarity}")

    return Equipment(
        name=record["name"], slot=record["slot"],
        attack_bonus=record.get("attack_bonus", 0),
        defense_bonus=record.get("defense_bonus", 0),
        speed_bonus=record.get("speed_bonus", 0),
        max_hp_bonus=record.get("max_hp_bonus", 0),
        max_mp_bonus=record.get("max_mp_bonus", 0),
        description=record.get("description", ""), price=record.get("price", 0),
        rarity=rarity,
        critical_rate_bonus=record.get("critical_rate_bonus", 0.0),
        evasion_rate_bonus=record.get("evasion_rate_bonus", 0.0),
        damage_reduction_bonus=record.get("damage_reduction_bonus", 0.0),
        special_effect=record.get("special_effect", ""),
        generated=record.get("generated", False),
        enhancement_level=record.get("enhancement_level", 0),
    )


def _character_to_dict(ch: PlayerCharacter) -> dict:
    return {
        "name": ch.name,
        "job": ch.job,
        "level": ch.level,
        "hp": ch.hp,
        "max_hp": ch.max_hp,
        "mp": ch.mp,
        "max_mp": ch.max_mp,
        "attack": ch.attack,
        "defense": ch.defense,
        "speed": ch.speed,
        "critical_rate": ch.critical_rate,
        "evasion_rate": ch.evasion_rate,
        "exp": ch.exp,
        "skills": [s.name for s in ch.skills],  # 스킬은 이름으로만 저장, 불러올 때 data.py에서 조회
        "equipment": {
            slot: (_equipment_to_dict(item) if item else None)
            for slot, item in ch.equipment.items()
        },
        "status_effects": [
            {
                "kind": e.kind,
                "name": e.name,
                "remaining_turns": e.remaining_turns,
                "power": e.power,
                "attack_mod": e.attack_mod,
                "defense_mod": e.defense_mod,
                "speed_mod": e.speed_mod,
            }
            for e in ch.status_effects
        ],
    }


def _character_from_dict(d: dict) -> PlayerCharacter:
    ch = PlayerCharacter(
        name=d["name"],
        job=d["job"],
        level=d["level"],
        max_hp=d["max_hp"],
        max_mp=d["max_mp"],
        attack=d["attack"],
        defense=d["defense"],
        speed=d["speed"],
        skills=[data.SKILLS_BY_NAME[n] for n in d["skills"] if n in data.SKILLS_BY_NAME],
        skill_progression=data.JOB_SKILL_GROWTH_BY_JOB.get(d["job"], {}),
        # 버전 1~2 저장 파일의 도적도 새 고유 특성을 자동으로 얻는다.
        critical_rate=d.get("critical_rate", 0.20 if d["job"] == "도적" else 0.0),
        evasion_rate=d.get("evasion_rate", 0.15 if d["job"] == "도적" else 0.0),
    )
    ch.hp = d["hp"]
    ch.mp = d["mp"]
    ch.exp = d["exp"]
    ch.sync_skills_for_level()
    ch.last_growth_messages = []
    for slot, equipment_data in d.get("equipment", {}).items():
        if slot in EQUIPMENT_SLOTS and equipment_data:
            ch.equipment[slot] = _equipment_from_data(equipment_data)
    ch.status_effects = [
        StatusEffect(
            kind=s["kind"], name=s["name"],
            remaining_turns=s["remaining_turns"], power=s.get("power", 0),
            attack_mod=s.get("attack_mod", 0),
            defense_mod=s.get("defense_mod", 0),
            speed_mod=s.get("speed_mod", 0),
        )
        for s in d.get("status_effects", [])
    ]
    return ch


# ---------------------------------------------------------------------------
# 저장
# ---------------------------------------------------------------------------
def save_game(
    party: Party,
    inventory: List[Item],
    game_map: GameMap,
    flags: dict,
    equipment_inventory: Optional[List[Equipment]] = None,
    path: str = DEFAULT_SAVE_PATH,
    quest_log=None,
) -> None:
    equipment_inventory = equipment_inventory or []

    location_states = {
        loc_id: {
            "boss_defeated": loc.boss_defeated,
            "dialogue_played": loc.dialogue_played,
            "loot_claimed": loc.loot_claimed,
            "unlocked_labels": list(loc.unlocked_labels),
        }
        for loc_id, loc in game_map.locations.items()
    }

    payload = {
        "save_version": SAVE_VERSION,
        "party": [_character_to_dict(m) for m in party.members],
        "gold": party.gold,
        "inventory": [it.name for it in inventory],
        "equipment_inventory": [_equipment_to_dict(it) for it in equipment_inventory],
        "current_location": game_map.current_id,
        "visited_locations": list(game_map.visited),
        "location_states": location_states,
        "flags": flags,
        "quest_states": dict(quest_log.states) if quest_log is not None else {},
        "metadata": {
            "saved_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "play_time_seconds": party.total_play_time_seconds,
            "location_name": game_map.current.name,
            "party_jobs": [member.job for member in party.members],
            "average_level": round(
                sum(member.level for member in party.members) / len(party.members), 1
            ),
        },
    }

    write_save_payload(payload, path)


def write_save_payload(payload: dict, path: str = DEFAULT_SAVE_PATH) -> None:
    """검증된 저장 데이터를 원자적으로 기록한다.

    웹판은 이 함수를 이용해 브라우저에 보관한 백업을 서버 저장 슬롯으로
    복원한다. 검증을 먼저 수행하므로 임의 JSON이 저장 파일이 되지 않는다.
    """
    _validate_payload(payload)
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    fd, temp_path = tempfile.mkstemp(prefix=".save-", suffix=".tmp", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        if os.path.exists(path):
            shutil.copy2(path, path + ".bak")
        os.replace(temp_path, path)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


# ---------------------------------------------------------------------------
# 불러오기
# ---------------------------------------------------------------------------
def load_game(path: str = DEFAULT_SAVE_PATH):
    payload = read_save_payload(path)

    party = Party(
        [_character_from_dict(d) for d in payload["party"]],
        gold=payload.get("gold", 0),
        play_time_seconds=payload.get("metadata", {}).get("play_time_seconds", 0),
    )
    inventory = [data.ITEMS_BY_NAME[n] for n in payload["inventory"]]
    equipment_inventory = [
        _equipment_from_data(record)
        for record in payload.get("equipment_inventory", [])
    ]

    # world를 여기서 import (map.py <-> save.py 순환 참조 방지용 지연 import)
    from world import build_world
    game_map = build_world()
    if payload["current_location"] not in game_map.locations:
        raise SaveGameError(f"존재하지 않는 현재 위치입니다: {payload['current_location']}")
    game_map.current_id = payload["current_location"]
    visited = set(payload.get("visited_locations", [payload["current_location"]]))
    unknown_locations = visited - set(game_map.locations)
    if unknown_locations:
        raise SaveGameError(f"존재하지 않는 방문 위치가 있습니다: {sorted(unknown_locations)}")
    game_map.visited = visited
    for loc_id, state in payload.get("location_states", {}).items():
        if loc_id in game_map.locations:
            game_map.locations[loc_id].boss_defeated = state.get("boss_defeated", False)
            game_map.locations[loc_id].dialogue_played = state.get("dialogue_played", False)
            game_map.locations[loc_id].loot_claimed = state.get("loot_claimed", False)
            game_map.locations[loc_id].unlocked_labels = set(state.get("unlocked_labels", []))

    flags = payload.get("flags", {})
    from quests import QuestLog
    quest_log = QuestLog(payload.get("quest_states", {}))
    quest_log.sync_story_flags(flags)
    quest_log.refresh_from_world(game_map, flags)
    return party, inventory, game_map, flags, equipment_inventory, quest_log


def read_save_payload(path: str = DEFAULT_SAVE_PATH) -> dict:
    """저장 파일을 읽고 호환성 검증을 마친 JSON 데이터를 반환한다."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            payload = json.load(f)
    except json.JSONDecodeError as error:
        raise SaveGameError("JSON 형식이 손상되었습니다.") from error

    _validate_payload(payload)
    return payload


def _validate_payload(payload: dict) -> None:
    if not isinstance(payload, dict):
        raise SaveGameError("저장 데이터의 최상위 형식이 올바르지 않습니다.")
    version = payload.get("save_version", 1)
    if not isinstance(version, int) or version < 1 or version > SAVE_VERSION:
        raise SaveGameError(f"지원하지 않는 저장 버전입니다: {version}")

    required = {"party", "inventory", "current_location"}
    missing = required - set(payload)
    if missing:
        raise SaveGameError(f"필수 저장 항목이 없습니다: {sorted(missing)}")
    if not isinstance(payload["party"], list) or not payload["party"]:
        raise SaveGameError("파티 정보가 없거나 올바르지 않습니다.")
    if not isinstance(payload["inventory"], list):
        raise SaveGameError("인벤토리 형식이 올바르지 않습니다.")
    if not isinstance(payload.get("quest_states", {}), dict):
        raise SaveGameError("퀘스트 상태 형식이 올바르지 않습니다.")
    metadata = payload.get("metadata", {})
    if not isinstance(metadata, dict):
        raise SaveGameError("저장 메타데이터 형식이 올바르지 않습니다.")
    play_time = metadata.get("play_time_seconds", 0)
    if not isinstance(play_time, (int, float)) or play_time < 0:
        raise SaveGameError("플레이 시간 정보가 올바르지 않습니다.")
    from quests import QUESTS, QUEST_STATUSES
    invalid_quests = set(payload.get("quest_states", {})) - set(QUESTS)
    invalid_statuses = {
        status for status in payload.get("quest_states", {}).values()
        if status not in QUEST_STATUSES
    }
    if invalid_quests:
        raise SaveGameError(f"알 수 없는 퀘스트가 있습니다: {sorted(invalid_quests)}")
    if invalid_statuses:
        raise SaveGameError(f"알 수 없는 퀘스트 상태가 있습니다: {sorted(invalid_statuses)}")

    character_fields = {
        "name", "job", "level", "hp", "max_hp", "mp", "max_mp",
        "attack", "defense", "speed", "exp", "skills",
    }
    unknown_skills = set()
    for character in payload["party"]:
        if not isinstance(character, dict):
            raise SaveGameError("캐릭터 데이터 형식이 올바르지 않습니다.")
        missing_character = character_fields - set(character)
        if missing_character:
            raise SaveGameError(f"캐릭터 필수 항목이 없습니다: {sorted(missing_character)}")
        unknown_skills.update(set(character["skills"]) - set(data.SKILLS_BY_NAME))
        equipment_data = character.get("equipment", {})
        if not isinstance(equipment_data, dict):
            raise SaveGameError("착용 장비 형식이 올바르지 않습니다.")
        for slot, record in equipment_data.items():
            if slot not in EQUIPMENT_SLOTS:
                raise SaveGameError(f"알 수 없는 장비 슬롯입니다: {slot}")
            _equipment_from_data(record)

    unknown_items = set(payload["inventory"]) - set(data.ITEMS_BY_NAME)
    equipment_inventory = payload.get("equipment_inventory", [])
    if not isinstance(equipment_inventory, list):
        raise SaveGameError("보유 장비함 형식이 올바르지 않습니다.")
    for record in equipment_inventory:
        _equipment_from_data(record)
    errors = []
    if unknown_skills:
        errors.append(f"알 수 없는 스킬 {sorted(unknown_skills)}")
    if unknown_items:
        errors.append(f"알 수 없는 아이템 {sorted(unknown_items)}")
    if errors:
        raise SaveGameError("저장 콘텐츠가 현재 게임과 맞지 않습니다: " + ", ".join(errors))


def has_save(path: str = DEFAULT_SAVE_PATH) -> bool:
    return os.path.exists(path)


def has_any_save(max_slots: int = MAX_SLOTS, save_dir: Optional[str] = None) -> bool:
    return any(
        os.path.exists(slot_path(i, save_dir)) for i in range(1, max_slots + 1)
    )


def delete_save(path: str = DEFAULT_SAVE_PATH) -> None:
    if os.path.exists(path):
        os.remove(path)


# ---------------------------------------------------------------------------
# 저장 슬롯 목록/선택 UI
# ---------------------------------------------------------------------------
def _slot_summary(path: str) -> Optional[str]:
    """저장 파일 하나의 요약 문구를 만듭니다 (슬롯 목록에 보여줄 용도)."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        party = payload.get("party", [])
        if not party:
            return None
        metadata = payload.get("metadata", {})
        levels = [member.get("level", 0) for member in party]
        average_level = float(
            metadata.get("average_level", round(sum(levels) / len(levels), 1))
        )
        jobs = metadata.get("party_jobs", [member.get("job", "?") for member in party])
        if not isinstance(jobs, list):
            return None
        gold = payload.get("gold", 0)
        location = metadata.get("location_name") or _location_name(payload.get("current_location", "?"))
        play_time = _format_play_time(metadata.get("play_time_seconds", 0))
        saved_at = _format_saved_at(metadata.get("saved_at"), path)
        return (
            f"평균 Lv.{average_level:g} · {'/'.join(str(job) for job in jobs)} · "
            f"{location} · {gold}G · {play_time} · {saved_at}"
        )
    except (
        OSError, json.JSONDecodeError, KeyError, TypeError, IndexError,
        ValueError, ZeroDivisionError,
    ):
        return None


def _location_name(location_id: str) -> str:
    """기존 저장 파일의 장소 ID를 현재 월드의 표시 이름으로 바꾼다."""
    try:
        from world import build_world
        return build_world().locations[location_id].name
    except (KeyError, TypeError):
        return str(location_id)


def _format_play_time(seconds) -> str:
    try:
        total = max(0, int(seconds))
    except (TypeError, ValueError):
        total = 0
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def _format_saved_at(value, path: str) -> str:
    """저장 시각을 간단히 표시하고 기존 저장은 파일 수정 시각을 사용한다."""
    try:
        moment = datetime.fromisoformat(value) if value else datetime.fromtimestamp(os.path.getmtime(path))
        return moment.strftime("%Y-%m-%d %H:%M")
    except (OSError, TypeError, ValueError):
        return "시각 미상"


def list_slots(
    max_slots: int = MAX_SLOTS, save_dir: Optional[str] = None
) -> List[Tuple[int, bool, Optional[str]]]:
    """[(슬롯 번호, 저장 있는지 여부, 요약 문구 또는 None), ...] 를 반환합니다."""
    slots = []
    for i in range(1, max_slots + 1):
        path = slot_path(i, save_dir)
        exists = os.path.exists(path)
        summary = _slot_summary(path) if exists else None
        slots.append((i, exists, summary))
    return slots


def prompt_save_slot(max_slots: int = MAX_SLOTS) -> Optional[int]:
    """저장할 슬롯을 고르는 메뉴. 취소하면 None을 반환합니다."""
    print("\n[저장할 슬롯을 선택하세요]")
    for i, exists, summary in list_slots(max_slots):
        status = f"(덮어쓰기: {summary or '손상된 저장 파일'})" if exists else "(비어있음)"
        print(f"  {i}) 슬롯 {i} {status}")
    cancel_option = max_slots + 1
    print(f"  {cancel_option}) 취소")

    num = prompt_index("> ", cancel_option) + 1
    if 1 <= num <= max_slots:
        if list_slots(max_slots)[num - 1][1] and not prompt_yes_no("기존 저장을 덮어쓸까요? (y/n)> "):
            return None
        return num
    return None


def prompt_load_slot(max_slots: int = MAX_SLOTS) -> Optional[int]:
    """불러올 슬롯을 고르는 메뉴. 취소하거나 빈 슬롯을 고르면 None을 반환합니다."""
    print("\n[불러올 슬롯을 선택하세요]")
    slots = list_slots(max_slots)
    for i, exists, summary in slots:
        status = summary if summary is not None else ("(손상됨)" if exists else "(비어있음)")
        print(f"  {i}) 슬롯 {i} - {status}")
    cancel_option = max_slots + 1
    print(f"  {cancel_option}) 취소")

    num = prompt_index("> ", cancel_option) + 1
    if 1 <= num <= max_slots and slots[num - 1][1] and slots[num - 1][2] is not None:
        return num
    return None
