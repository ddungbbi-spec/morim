"""마을 NPC가 반복해서 제공하는 무작위 지역 의뢰를 관리한다."""

from __future__ import annotations

from dataclasses import dataclass
import random
from typing import Dict, Tuple


COMMISSION_STATUSES = {"offered", "active", "ready"}


@dataclass(frozen=True)
class CommissionTemplate:
    commission_id: str
    village_id: str
    title: str
    description: str
    objective: str
    target_type: str
    target_id: str
    required: int
    gold_reward: int
    item_rewards: Tuple[Tuple[str, int], ...] = ()


COMMISSION_TEMPLATES: Dict[str, CommissionTemplate] = {
    "forest_slime_cleanup": CommissionTemplate(
        "forest_slime_cleanup", "village", "숲길 점액 청소",
        "숲 입구를 막는 슬라임을 정리한다.", "슬라임 2마리 처치",
        "defeat", "슬라임", 2, 28, (("포션", 1),),
    ),
    "forest_wolf_watch": CommissionTemplate(
        "forest_wolf_watch", "village", "울음소리의 근원",
        "마을 주변을 배회하는 야생 늑대를 추적한다.", "야생 늑대 2마리 처치",
        "defeat", "야생 늑대", 2, 34, (("포션", 1),),
    ),
    "cave_patrol": CommissionTemplate(
        "cave_patrol", "village", "동굴 입구 확인",
        "마을 상단에 보고할 수 있도록 동굴의 상태를 확인한다.", "동굴 방문",
        "visit", "cave", 1, 25, (("해독제", 1),),
    ),
    "miner_remains": CommissionTemplate(
        "miner_remains", "iron_village", "갱도의 잔해",
        "철광촌의 작업로에 나타난 스켈레톤 광부를 정리한다.", "스켈레톤 광부 2마리 처치",
        "defeat", "스켈레톤 광부", 2, 48, (("포션", 1),),
    ),
    "ghost_shift": CommissionTemplate(
        "ghost_shift", "iron_village", "끝나지 않은 교대",
        "폐광에 남은 유령 광부를 쉬게 한다.", "유령 광부 2마리 처치",
        "defeat", "유령 광부", 2, 52, (("에테르", 1),),
    ),
    "mine_depth_survey": CommissionTemplate(
        "mine_depth_survey", "iron_village", "심층 갱도 측량",
        "붕괴 위험을 확인하기 위해 폐광 가장 깊은 곳까지 다녀온다.", "폐광 가장 깊은 곳 방문",
        "visit", "mine_depths", 1, 46, (("해독제", 1),),
    ),
    "marsh_slime_sample": CommissionTemplate(
        "marsh_slime_sample", "mist_village", "늪지 표본 확보",
        "약재 연구를 방해하는 늪지 슬라임을 처치한다.", "늪지 슬라임 2마리 처치",
        "defeat", "늪지 슬라임", 2, 50, (("해독제", 2),),
    ),
    "wisp_lantern": CommissionTemplate(
        "wisp_lantern", "mist_village", "길 잃은 불빛",
        "침수된 나무길의 도깨비불을 잠재운다.", "도깨비불 2마리 처치",
        "defeat", "도깨비불", 2, 56, (("에테르", 1),),
    ),
    "archive_delivery": CommissionTemplate(
        "archive_delivery", "mist_village", "기록실 답사",
        "가라앉은 기록실의 수로가 안전한지 확인한다.", "가라앉은 기록실 방문",
        "visit", "drowned_archive", 1, 54, (("달빛 영약", 1),),
    ),
    "fallen_wraiths": CommissionTemplate(
        "fallen_wraiths", "star_village", "낙하지의 원혼",
        "유성 낙하지 주변의 저주받은 원혼을 정리한다.", "저주받은 원혼 2마리 처치",
        "defeat", "저주받은 원혼", 2, 72, (("에테르", 1),),
    ),
    "rift_observation": CommissionTemplate(
        "rift_observation", "star_village", "균열 관측 기록",
        "별의 균열에 도달해 현재 상태를 확인한다.", "별의 균열 방문",
        "visit", "star_rift", 1, 68, (("달빛 영약", 1),),
    ),
    "shadow_stalker_hunt": CommissionTemplate(
        "shadow_stalker_hunt", "star_village", "별빛을 쫓는 그림자",
        "관측로까지 따라온 그림자 추적자를 제거한다.", "그림자 추적자 2마리 처치",
        "defeat", "그림자 추적자", 2, 76, (("포션", 2),),
    ),
}


def templates_for(village_id: str) -> list[CommissionTemplate]:
    return [
        template for template in COMMISSION_TEMPLATES.values()
        if template.village_id == village_id
    ]


def _records(flags: dict) -> dict:
    records = flags.get("random_commissions")
    if not isinstance(records, dict):
        records = {}
        flags["random_commissions"] = records
    return records


def _history(flags: dict) -> dict:
    history = flags.get("commission_history")
    if not isinstance(history, dict):
        history = {}
        flags["commission_history"] = history
    return history


def commission_record(flags: dict, village_id: str):
    records = flags.get("random_commissions")
    if not isinstance(records, dict):
        return None
    record = records.get(village_id)
    if not isinstance(record, dict):
        return None
    template = COMMISSION_TEMPLATES.get(record.get("template_id"))
    if template is None or template.village_id != village_id:
        return None
    if record.get("status") not in COMMISSION_STATUSES:
        return None
    try:
        progress = max(0, min(int(record.get("progress", 0)), template.required))
    except (TypeError, ValueError):
        progress = 0
    record["progress"] = progress
    return record, template


def offer_commission(flags: dict, village_id: str, rng=random):
    current = commission_record(flags, village_id)
    if current is not None:
        return current
    choices = templates_for(village_id)
    if not choices:
        raise ValueError("이 마을에는 의뢰를 주는 NPC가 없습니다.")
    previous = _history(flags).get(village_id)
    fresh = [template for template in choices if template.commission_id != previous]
    template = rng.choice(fresh or choices)
    record = {"template_id": template.commission_id, "status": "offered", "progress": 0}
    _records(flags)[village_id] = record
    return record, template


def accept_commission(flags: dict, village_id: str) -> bool:
    current = commission_record(flags, village_id)
    if current is None or current[0]["status"] != "offered":
        return False
    current[0]["status"] = "active"
    current[0]["progress"] = 0
    return True


def _advance(flags: dict, target_type: str, target_id: str, amount: int = 1) -> list[str]:
    records = flags.get("random_commissions")
    if not isinstance(records, dict):
        return []
    completed = []
    for village_id in list(records):
        current = commission_record(flags, village_id)
        if current is None:
            continue
        record, template = current
        if record["status"] != "active":
            continue
        if template.target_type != target_type or template.target_id != target_id:
            continue
        record["progress"] = min(template.required, record["progress"] + amount)
        if record["progress"] >= template.required:
            record["status"] = "ready"
            completed.append(template.title)
    return completed


def record_visit(flags: dict, location_id: str) -> list[str]:
    return _advance(flags, "visit", location_id)


def record_defeats(flags: dict, enemy_names: list[str]) -> list[str]:
    completed = []
    for enemy_name in set(enemy_names):
        completed.extend(_advance(flags, "defeat", enemy_name, enemy_names.count(enemy_name)))
    return completed


def claim_commission(flags: dict, village_id: str, party, inventory: list):
    current = commission_record(flags, village_id)
    if current is None or current[0]["status"] != "ready":
        return None
    _, template = current
    import data

    party.gold += template.gold_reward
    for item_name, count in template.item_rewards:
        inventory.extend([data.ITEMS_BY_NAME[item_name]] * count)
    _history(flags)[village_id] = template.commission_id
    del _records(flags)[village_id]
    return template


def commission_state(flags: dict, village_id: str) -> dict | None:
    current = commission_record(flags, village_id)
    if current is None:
        return None
    record, template = current
    return {
        "id": template.commission_id,
        "title": template.title,
        "description": template.description,
        "objective": template.objective,
        "status": record["status"],
        "progress": record["progress"],
        "required": template.required,
        "gold_reward": template.gold_reward,
        "item_rewards": [
            {"name": item_name, "count": count}
            for item_name, count in template.item_rewards
        ],
    }
