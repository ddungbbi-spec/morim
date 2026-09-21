"""반복 가능한 고위험 랜덤 던전의 적 조합과 위험 변이를 정의한다."""

from __future__ import annotations

import random

import data


DUNGEON_LOCATION_ID = "abyss_dungeon"
DUNGEON_ENTRY_FEE = 50
DUNGEON_MAX_DEPTH = 4

DUNGEON_MODIFIERS = (
    {"id": "frenzy", "name": "광폭화", "description": "적 공격력과 속도 증가", "reward": 1.35},
    {"id": "ironwall", "name": "철벽", "description": "적 체력과 방어력 증가", "reward": 1.30},
    {"id": "elite", "name": "정예 군단", "description": "적의 모든 능력치 대폭 증가", "reward": 1.50},
)


def dungeon_clear_count(flags: dict) -> int:
    try:
        return max(0, int(flags.get("dungeon_clear_count", 0)))
    except (TypeError, ValueError):
        return 0


def _enemy_groups(depth: int):
    groups = {
        1: (
            (data.create_shadow_stalker, data.create_cursed_wraith),
            (data.create_orc_warrior, data.create_shadow_stalker),
        ),
        2: (
            (data.create_nebula_devourer,),
            (data.create_void_sentinel, data.create_cursed_wraith),
        ),
        3: (
            (data.create_void_sentinel, data.create_nebula_devourer),
            (data.create_cave_golem, data.create_void_sentinel),
        ),
        4: ((data.create_void_observer,),),
    }
    return groups[max(1, min(depth, DUNGEON_MAX_DEPTH))]


def create_dungeon_floor(flags: dict, rng=random):
    """현재 층에 맞는 적 조합과 위험 변이를 생성한다."""
    depth = max(1, min(int(flags.get("dungeon_depth", 1)), DUNGEON_MAX_DEPTH))
    modifier = rng.choice(DUNGEON_MODIFIERS)
    factories = rng.choice(_enemy_groups(depth))
    enemies = [factory() for factory in factories]
    clear_step = dungeon_clear_count(flags)
    base_scale = 1 + 0.16 * (depth - 1) + 0.10 * clear_step
    for enemy in enemies:
        enemy.level += depth - 1 + clear_step
        enemy.max_hp = round(enemy.max_hp * base_scale)
        enemy.attack = round(enemy.attack * base_scale)
        enemy.defense = round(enemy.defense * base_scale)
        enemy.speed += min(depth - 1 + clear_step, 6)
        if modifier["id"] == "frenzy":
            enemy.attack = round(enemy.attack * 1.30)
            enemy.speed += 2
        elif modifier["id"] == "ironwall":
            enemy.max_hp = round(enemy.max_hp * 1.25)
            enemy.defense = round(enemy.defense * 1.35)
        else:
            enemy.max_hp = round(enemy.max_hp * 1.35)
            enemy.attack = round(enemy.attack * 1.18)
            enemy.defense = round(enemy.defense * 1.18)
        enemy.hp = enemy.max_hp
        enemy.exp_reward = round(enemy.exp_reward * (1 + 0.20 * depth))
        enemy.gold_reward = round(enemy.gold_reward * (1 + 0.15 * depth))
    return enemies, modifier


def floor_bank_reward(depth: int, modifier: dict, clear_count: int) -> int:
    base = 30 + 20 * depth + 10 * clear_count
    return round(base * float(modifier["reward"]))
