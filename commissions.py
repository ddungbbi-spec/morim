"""마을별 지역 의뢰 게시판과 NPC 무작위 반복 의뢰를 관리한다."""

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
    "twilight_bandit_patrol": CommissionTemplate(
        "twilight_bandit_patrol", "twilight_village", "황혼길 순찰",
        "교역 수레를 노리는 산적을 몰아낸다.", "교역로 산적 2명 처치",
        "defeat", "교역로 산적", 2, 62, (("포션", 2),),
    ),
    "twilight_hawk_watch": CommissionTemplate(
        "twilight_hawk_watch", "twilight_village", "하늘길 호위",
        "상단의 전서구를 습격하는 황혼 매를 쫓는다.", "황혼 매 2마리 처치",
        "defeat", "황혼 매", 2, 58, (("에테르", 1),),
    ),
    "twilight_square_delivery": CommissionTemplate(
        "twilight_square_delivery", "twilight_village", "광장 물자 확인",
        "교역 광장의 수레와 보급품 상태를 확인한다.", "황혼 상단 광장 방문",
        "visit", "twilight_caravan_square", 1, 55, (("해독제", 1),),
    ),
    "twilight_jackal_hunt": CommissionTemplate(
        "twilight_jackal_hunt", "twilight_village", "붉은 갈대의 울음",
        "상단의 짐말을 습격하는 승냥이 무리를 줄인다.", "붉은갈기 승냥이 3마리 처치",
        "defeat", "붉은갈기 승냥이", 3, 78, (("포션", 2),),
    ),
    "twilight_hexer_hunt": CommissionTemplate(
        "twilight_hexer_hunt", "twilight_village", "협곡의 검은 주문",
        "바람흔적 협곡에서 상단을 저주하는 도적술사를 제압한다.", "협곡 도적술사 2명 처치",
        "defeat", "협곡 도적술사", 2, 92, (("에테르", 2),),
    ),
    "twilight_den_scout": CommissionTemplate(
        "twilight_den_scout", "twilight_village", "황혼송곳니 추적",
        "협곡 최심부에 있다는 우두머리의 소굴을 찾아낸다.", "황혼송곳니 소굴 방문",
        "visit", "duskfang_den", 1, 86, (("달빛 영약", 1),),
    ),
}


def templates_for(village_id: str) -> list[CommissionTemplate]:
    return [
        template for template in COMMISSION_TEMPLATES.values()
        if template.village_id == village_id
    ]


# 게시판 목록을 고정해 반복 의뢰 추가 시에도 저장된 게시판 구성을 유지한다.
REGIONAL_BOARD_IDS = {
    "village": ("forest_slime_cleanup", "forest_wolf_watch", "cave_patrol"),
    "iron_village": ("miner_remains", "ghost_shift", "mine_depth_survey"),
    "mist_village": ("marsh_slime_sample", "wisp_lantern", "archive_delivery"),
    "star_village": ("fallen_wraiths", "rift_observation", "shadow_stalker_hunt"),
    "twilight_village": ("twilight_bandit_patrol", "twilight_hawk_watch", "twilight_square_delivery"),
}


def _regional_record(flags: dict, commission_id: str) -> dict:
    records = flags.get("regional_commissions", {})
    record = records.get(commission_id) if isinstance(records, dict) else None
    if (not isinstance(record, dict) or not isinstance(record.get("status"), str)
            or record["status"] not in {"active", "ready", "completed"}):
        return {"status": "available", "progress": 0}
    template = COMMISSION_TEMPLATES[commission_id]
    try:
        progress = max(0, min(int(record.get("progress", 0)), template.required))
    except (TypeError, ValueError, OverflowError):
        progress = 0
    status = record["status"]
    if status == "completed":
        progress = template.required
    else:
        status = "ready" if progress == template.required else "active"
    record.update(status=status, progress=progress)
    return record


def regional_board_state(flags: dict, village_id: str | None = None) -> list[dict]:
    ids = (REGIONAL_BOARD_IDS.get(village_id, ()) if village_id is not None else
           tuple(cid for group in REGIONAL_BOARD_IDS.values() for cid in group))
    return [dict(_commission_view(COMMISSION_TEMPLATES[cid], _regional_record(flags, cid)),
                 village_id=COMMISSION_TEMPLATES[cid].village_id) for cid in ids]


def accept_regional_commission(flags: dict, village_id: str, commission_id: str) -> bool:
    if commission_id not in REGIONAL_BOARD_IDS.get(village_id, ()):
        return False
    if _regional_record(flags, commission_id)["status"] != "available":
        return False
    if not isinstance(flags.get("regional_commissions"), dict):
        flags["regional_commissions"] = {}
    flags["regional_commissions"][commission_id] = {"status": "active", "progress": 0}
    return True


def claim_regional_commission(flags: dict, village_id: str, commission_id: str,
                              party, inventory: list):
    if commission_id not in REGIONAL_BOARD_IDS.get(village_id, ()):
        return None
    record = _regional_record(flags, commission_id)
    if record["status"] != "ready":
        return None
    template = COMMISSION_TEMPLATES[commission_id]
    _grant_rewards(flags, template, party, inventory)
    record["status"] = "completed"
    return template


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
    template_id = record.get("template_id")
    template = COMMISSION_TEMPLATES.get(template_id) if isinstance(template_id, str) else None
    if template is None or template.village_id != village_id:
        return None
    if not isinstance(record.get("status"), str) or record["status"] not in COMMISSION_STATUSES:
        return None
    try:
        progress = max(0, min(int(record.get("progress", 0)), template.required))
    except (TypeError, ValueError, OverflowError):
        progress = 0
    if record["status"] == "offered":
        progress = 0
    else:
        record["status"] = "ready" if progress == template.required else "active"
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
    completed = []
    pending = []
    for village_id in list(records) if isinstance(records, dict) else []:
        current = commission_record(flags, village_id)
        if current is not None:
            pending.append(current)
    for ids in REGIONAL_BOARD_IDS.values():
        for commission_id in ids:
            pending.append((_regional_record(flags, commission_id),
                            COMMISSION_TEMPLATES[commission_id]))
    for record, template in pending:
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
    _grant_rewards(flags, template, party, inventory)
    _history(flags)[village_id] = template.commission_id
    del _records(flags)[village_id]
    return template


def _grant_rewards(flags: dict, template: CommissionTemplate, party, inventory: list):
    import data

    items = [data.ITEMS_BY_NAME[name] for name, count in template.item_rewards
             for _ in range(count)]
    party.gold += template.gold_reward
    inventory.extend(items)
    from reputation import add_reputation
    add_reputation(flags, template.village_id, 1)


def commission_state(flags: dict, village_id: str) -> dict | None:
    current = commission_record(flags, village_id)
    if current is None:
        return None
    record, template = current
    return _commission_view(template, record)


def tracked_commission_state(flags: dict) -> list[dict]:
    """두 종류의 의뢰를 구분해 추적하고 보고 가능한 의뢰를 먼저 보여 준다."""
    entries = [dict(entry, source="regional") for entry in regional_board_state(flags)
               if entry["status"] in {"active", "ready"}]
    for village_id in REGIONAL_BOARD_IDS:
        entry = commission_state(flags, village_id)
        if entry is not None and entry["status"] in {"active", "ready"}:
            entries.append(dict(entry, village_id=village_id, source="random"))
    return sorted(entries, key=lambda entry: entry["status"] != "ready")


def _commission_view(template: CommissionTemplate, record: dict) -> dict:
    return {
        "id": template.commission_id,
        "title": template.title,
        "description": template.description,
        "objective": template.objective,
        "status": record["status"],
        "progress": record["progress"],
        "required": template.required,
        "gold_reward": template.gold_reward,
        "reputation_reward": 1,
        "item_rewards": [
            {"name": item_name, "count": count}
            for item_name, count in template.item_rewards
        ],
    }


def run_regional_board(flags: dict, village_id: str, party, inventory: list) -> None:
    from input_utils import prompt_index, prompt_yes_no

    labels = {"available": "수락 가능", "active": "진행 중",
              "ready": "보상 가능", "completed": "보상 수령 완료"}
    while True:
        entries = regional_board_state(flags, village_id)
        print("\n[지역 의뢰 게시판 · 진행 후 저장하세요]")
        for index, entry in enumerate(entries, 1):
            print(f"  {index}) {entry['title']} · {labels[entry['status']]} · "
                  f"{entry['progress']}/{entry['required']}")
        print(f"  {len(entries) + 1}) 돌아가기")
        choice = prompt_index("> ", len(entries) + 1)
        if choice == len(entries):
            return
        entry = entries[choice]
        print(f"{entry['description']} · 목표: {entry['objective']}")
        rewards = [f"{entry['gold_reward']}G", "지역 평판 +1"]
        rewards.extend(f"{item['name']}×{item['count']}" for item in entry["item_rewards"])
        print("보상: " + " · ".join(rewards))
        if entry["status"] == "available" and prompt_yes_no("수락할까요? (y/n)> "):
            accept_regional_commission(flags, village_id, entry["id"])
        elif entry["status"] == "ready" and prompt_yes_no("보상을 받을까요? (y/n)> "):
            claim_regional_commission(flags, village_id, entry["id"], party, inventory)
            print("의뢰 보상을 받았습니다.")
