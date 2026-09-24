"""전투에서 발견한 적과 처치 기록을 저장하는 적 도감."""

from __future__ import annotations

from typing import Iterable

from models import Enemy


BESTIARY_FLAG = "enemy_bestiary"
MASTERED_DEFEATS = 5


def _count(value, default: int = 0) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return default


def _records(flags: dict) -> dict:
    records = flags.get(BESTIARY_FLAG)
    if not isinstance(records, dict):
        records = {}
        flags[BESTIARY_FLAG] = records
    return records


def _snapshot(enemy: Enemy) -> dict:
    return {
        "name": enemy.name,
        "job": enemy.job,
        "level": max(1, int(enemy.level)),
        "max_hp": max(1, int(enemy.effective_max_hp)),
        "attack": max(0, int(enemy.effective_attack)),
        "defense": max(0, int(enemy.effective_defense)),
        "speed": max(0, int(enemy.effective_speed)),
        "weakness": enemy.weakness or "없음",
        "resistance": enemy.resistance or "없음",
    }


def discover_enemies(flags: dict, enemies: Iterable[Enemy]) -> list[str]:
    """적을 도감에 등록하고 조우 횟수를 누적한다. 새 이름 목록을 반환한다."""
    records = _records(flags)
    discovered = []
    for enemy in enemies:
        key = str(enemy.name)
        previous = records.get(key)
        if not isinstance(previous, dict):
            previous = {"encounters": 0, "defeats": 0}
            discovered.append(key)
        record = {
            **_snapshot(enemy),
            "encounters": _count(previous.get("encounters")) + 1,
            "defeats": _count(previous.get("defeats")),
        }
        records[key] = record
    return discovered


def record_enemy_defeats(flags: dict, enemies: Iterable[Enemy]) -> list[str]:
    """승리한 전투의 적 처치를 누적하고 숙련(5회) 달성 이름을 반환한다."""
    records = _records(flags)
    mastered = []
    for enemy in enemies:
        key = str(enemy.name)
        previous = records.get(key)
        if not isinstance(previous, dict):
            previous = {**_snapshot(enemy), "encounters": 1, "defeats": 0}
        before = _count(previous.get("defeats"))
        previous.update(_snapshot(enemy))
        previous["encounters"] = max(1, _count(previous.get("encounters"), 1))
        previous["defeats"] = before + 1
        records[key] = previous
        if before < MASTERED_DEFEATS <= previous["defeats"]:
            mastered.append(key)
    return mastered


def bestiary_state(flags: dict) -> dict:
    """웹과 다른 표시 계층에서 사용할 정규화된 도감 상태를 만든다."""
    records = flags.get(BESTIARY_FLAG, {})
    if not isinstance(records, dict):
        records = {}
    entries = []
    numeric_fields = ("level", "max_hp", "attack", "defense", "speed", "encounters", "defeats")
    for key, raw in records.items():
        if not isinstance(raw, dict):
            continue
        try:
            entry = {field: max(0, int(raw.get(field, 0))) for field in numeric_fields}
        except (TypeError, ValueError):
            continue
        entry.update({
            "name": str(raw.get("name") or key),
            "job": str(raw.get("job") or "미상"),
            "weakness": str(raw.get("weakness") or "없음"),
            "resistance": str(raw.get("resistance") or "없음"),
            "mastered": entry["defeats"] >= MASTERED_DEFEATS,
        })
        entries.append(entry)
    entries.sort(key=lambda item: (-item["defeats"], item["name"]))
    return {
        "discovered": len(entries),
        "total_defeats": sum(entry["defeats"] for entry in entries),
        "mastered": sum(entry["mastered"] for entry in entries),
        "mastered_defeats": MASTERED_DEFEATS,
        "entries": entries,
    }
