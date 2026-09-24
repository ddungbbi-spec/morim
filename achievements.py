"""여러 콘텐츠의 진행도를 묶는 업적과 일회성 골드 보상."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from bestiary import bestiary_state


CLAIMED_FLAG = "claimed_achievements"


@dataclass(frozen=True)
class Achievement:
    achievement_id: str
    title: str
    description: str
    metric: str
    target: int
    gold_reward: int


ACHIEVEMENTS: Dict[str, Achievement] = {
    "first_victory": Achievement(
        "first_victory", "첫 승리", "적을 처음으로 처치한다.",
        "defeats", 1, 30,
    ),
    "field_researcher": Achievement(
        "field_researcher", "야전 연구가", "서로 다른 적 5종을 도감에 등록한다.",
        "species", 5, 75,
    ),
    "seasoned_hunter": Achievement(
        "seasoned_hunter", "노련한 사냥꾼", "적을 누적 25회 처치한다.",
        "defeats", 25, 150,
    ),
    "pathfinder": Achievement(
        "pathfinder", "길을 여는 자", "서로 다른 장소 10곳을 방문한다.",
        "locations", 10, 100,
    ),
    "village_envoy": Achievement(
        "village_envoy", "사방의 벗", "네 마을을 모두 방문한다.",
        "villages", 4, 125,
    ),
    "abyss_conqueror": Achievement(
        "abyss_conqueror", "심연 정복자", "심연 던전을 한 차례 완주한다.",
        "dungeon_clears", 1, 250,
    ),
}


def _count(value) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


def _claimed(flags: dict, repair: bool = False) -> dict:
    claimed = flags.get(CLAIMED_FLAG)
    if not isinstance(claimed, dict):
        claimed = {}
        if repair:
            flags[CLAIMED_FLAG] = claimed
    return claimed


def achievement_state(
    flags: dict, visited_locations: int, visited_villages: int,
) -> dict:
    bestiary = bestiary_state(flags)
    progress = {
        "defeats": bestiary["total_defeats"],
        "species": bestiary["discovered"],
        "locations": _count(visited_locations),
        "villages": _count(visited_villages),
        "dungeon_clears": _count(flags.get("dungeon_clear_count")),
    }
    claimed = _claimed(flags)
    entries = []
    for definition in ACHIEVEMENTS.values():
        current = progress[definition.metric]
        is_claimed = claimed.get(definition.achievement_id) is True
        completed = current >= definition.target
        entries.append({
            "id": definition.achievement_id,
            "title": definition.title,
            "description": definition.description,
            "progress": min(current, definition.target),
            "target": definition.target,
            "gold_reward": definition.gold_reward,
            "status": "claimed" if is_claimed else "ready" if completed else "locked",
        })
    return {
        "total": len(entries),
        "completed": sum(entry["status"] in {"ready", "claimed"} for entry in entries),
        "claimed": sum(entry["status"] == "claimed" for entry in entries),
        "ready": sum(entry["status"] == "ready" for entry in entries),
        "entries": entries,
    }


def claim_achievement(
    flags: dict, achievement_id: str, party,
    visited_locations: int, visited_villages: int,
) -> Achievement | None:
    definition = ACHIEVEMENTS.get(achievement_id)
    if definition is None:
        return None
    state = achievement_state(flags, visited_locations, visited_villages)
    entry = next(item for item in state["entries"] if item["id"] == achievement_id)
    if entry["status"] != "ready":
        return None
    _claimed(flags, repair=True)[achievement_id] = True
    party.gold += definition.gold_reward
    return definition
