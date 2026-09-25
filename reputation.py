"""마을별 평판, 등급, 상점 할인 계산을 관리한다."""

from __future__ import annotations


VILLAGE_NAMES = {
    "village": "시작 마을",
    "iron_village": "철광촌",
    "mist_village": "안개나루",
    "star_village": "별바람 역참",
    "twilight_village": "황혼장터",
}

# (필요 평판, 등급명, 상점 할인율)
REPUTATION_TIERS = (
    (0, "낯선 방문객", 0.00),
    (3, "마을의 조력자", 0.05),
    (6, "신뢰받는 해결사", 0.10),
    (10, "마을의 영웅", 0.15),
)


def _scores(flags: dict) -> dict:
    scores = flags.get("village_reputation")
    if not isinstance(scores, dict):
        scores = {}
        flags["village_reputation"] = scores
    return scores


def reputation_score(flags: dict, village_id: str) -> int:
    """손상되거나 구버전인 평판 값을 안전하게 0 이상의 정수로 읽는다."""
    scores = flags.get("village_reputation")
    if not isinstance(scores, dict):
        return 0
    try:
        return max(0, int(scores.get(village_id, 0)))
    except (TypeError, ValueError):
        return 0


def add_reputation(flags: dict, village_id: str, amount: int) -> int:
    """등록된 마을의 평판을 올리고 변경 후 점수를 반환한다."""
    if village_id not in VILLAGE_NAMES:
        raise ValueError("평판을 올릴 수 없는 지역입니다.")
    if amount <= 0:
        return reputation_score(flags, village_id)
    score = reputation_score(flags, village_id) + int(amount)
    _scores(flags)[village_id] = score
    return score


def reputation_tier(flags: dict, village_id: str) -> tuple[int, str, float]:
    score = reputation_score(flags, village_id)
    return max(
        (tier for tier in REPUTATION_TIERS if score >= tier[0]),
        key=lambda tier: tier[0],
    )


def reputation_discount(flags: dict, village_id: str) -> float:
    if village_id not in VILLAGE_NAMES:
        return 0.0
    return reputation_tier(flags, village_id)[2]


def reputation_state(flags: dict, village_id: str) -> dict:
    """웹과 콘솔 표시에서 함께 사용하는 현재 등급 진행 상태."""
    score = reputation_score(flags, village_id)
    threshold, title, discount = reputation_tier(flags, village_id)
    next_tier = next((tier for tier in REPUTATION_TIERS if tier[0] > score), None)
    return {
        "village_id": village_id,
        "village_name": VILLAGE_NAMES.get(village_id, village_id),
        "score": score,
        "tier": title,
        "tier_threshold": threshold,
        "discount_rate": discount,
        "next_threshold": next_tier[0] if next_tier else None,
        "next_tier": next_tier[1] if next_tier else None,
    }
