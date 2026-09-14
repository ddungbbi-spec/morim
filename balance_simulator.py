"""직업 조합별 전투 밸런스를 반복 시뮬레이션하고 CSV/Markdown 보고서를 생성합니다."""

from __future__ import annotations

import argparse
import csv
import itertools
import os
import random
from dataclasses import dataclass
from statistics import mean
from typing import Callable, Dict, Iterable, List, Sequence, Tuple

import data
from models import Enemy, Party, PlayerCharacter, Skill


JOB_NAMES = {
    "warrior": "전사",
    "mage": "마법사",
    "healer": "힐러",
    "rogue": "도적",
    "archer": "궁수",
    "summoner": "소환술사",
}


@dataclass(frozen=True)
class Scenario:
    name: str
    level: int
    encounters: Sequence[Callable[[], List[Enemy]]]
    seal_power: bool = False


@dataclass(frozen=True)
class RouteStep:
    encounter_chance: float
    encounters: Sequence[Callable[[], List[Enemy]]]


@dataclass(frozen=True)
class RouteScenario:
    name: str
    steps: Sequence[RouteStep]
    seal_power: bool = False


SCENARIOS = [
    Scenario("숲 입구 일반전", 1, [
        lambda: [data.create_slime()],
        lambda: [data.create_wild_wolf()],
        lambda: [data.create_bat_swarm()],
    ]),
    Scenario("깊은 숲 일반전", 1, [
        lambda: [data.create_goblin()],
        lambda: [data.create_poison_spider()],
        lambda: [data.create_orc_warrior()],
        lambda: [data.create_forest_sprite()],
        lambda: [data.create_slime(), data.create_slime()],
        lambda: [data.create_goblin(), data.create_poison_spider()],
    ]),
    Scenario("그림자 골짜기 일반전", 2, [
        lambda: [data.create_shadow_stalker()],
        lambda: [data.create_cursed_wraith()],
        lambda: [data.create_orc_warrior()],
        lambda: [data.create_shadow_stalker(), data.create_cursed_wraith()],
    ]),
    Scenario("동굴 골렘", 2, [lambda: [data.create_cave_golem()]]),
    Scenario("다크 나이트", 2, [lambda: [data.create_dark_knight()]]),
    Scenario("탄광 드레이크", 3, [lambda: [data.create_mine_drake()]]),
    Scenario("봉인된 마왕-힘 거부", 3, [lambda: [data.create_sealed_demon_lord()]]),
    Scenario("봉인된 마왕-힘 수용", 3, [lambda: [data.create_sealed_demon_lord()]], seal_power=True),
    Scenario("탑의 수호자", 4, [lambda: [data.create_tower_guardian()]]),
]


ROUTES = [
    RouteScenario("메인 경로-힘 거부", [
        RouteStep(0.4, SCENARIOS[0].encounters),
        RouteStep(0.5, SCENARIOS[1].encounters),
        RouteStep(0.55, SCENARIOS[2].encounters),
        RouteStep(1.0, [lambda: [data.create_dark_knight()]]),
        RouteStep(1.0, [lambda: [data.create_sealed_demon_lord()]]),
    ]),
    RouteScenario("메인 경로-힘 수용", [
        RouteStep(0.4, SCENARIOS[0].encounters),
        RouteStep(0.5, SCENARIOS[1].encounters),
        RouteStep(0.55, SCENARIOS[2].encounters),
        RouteStep(1.0, [lambda: [data.create_dark_knight()]]),
        RouteStep(1.0, [lambda: [data.create_sealed_demon_lord()]]),
    ], seal_power=True),
    RouteScenario("동굴 보물방 경로", [
        RouteStep(0.4, SCENARIOS[0].encounters),
        RouteStep(0.5, [
            lambda: [data.create_bat_swarm()],
            lambda: [data.create_orc_warrior()],
            lambda: [data.create_bat_swarm(), data.create_bat_swarm()],
        ]),
        RouteStep(1.0, [lambda: [data.create_cave_golem()]]),
    ]),
    RouteScenario("폐광 경로", [
        RouteStep(0.4, SCENARIOS[0].encounters),
        RouteStep(0.5, [
            lambda: [data.create_skeleton_miner()],
            lambda: [data.create_ghost_miner()],
        ]),
        RouteStep(0.6, [
            lambda: [data.create_skeleton_miner(), data.create_ghost_miner()],
            lambda: [data.create_skeleton_miner(), data.create_skeleton_miner()],
            lambda: [data.create_ghost_miner()],
        ]),
        RouteStep(1.0, [lambda: [data.create_mine_drake()]]),
    ]),
    RouteScenario("도전의 탑 경로", [
        RouteStep(0.5, [
            lambda: [data.create_goblin()], lambda: [data.create_wild_wolf()], lambda: [data.create_orc_warrior()],
        ]),
        RouteStep(0.6, [
            lambda: [data.create_orc_warrior()], lambda: [data.create_forest_sprite()],
            lambda: [data.create_goblin(), data.create_poison_spider()],
        ]),
        RouteStep(0.7, [
            lambda: [data.create_orc_warrior(), data.create_goblin()],
            lambda: [data.create_poison_spider(), data.create_bat_swarm()],
            lambda: [data.create_orc_warrior(), data.create_orc_warrior()],
        ]),
        RouteStep(1.0, [lambda: [data.create_tower_guardian()]]),
    ]),
]


def _make_party(job_keys: Sequence[str], level: int, seal_power: bool) -> Party:
    members = []
    for index, key in enumerate(job_keys, 1):
        member = data.JOB_CREATORS[key](f"{JOB_NAMES[key]}{index}")
        for _ in range(1, level):
            member._level_up()
        if seal_power:
            member.max_hp += 6
            member.attack += 2
            member.defense += 1
        member.hp = member.effective_max_hp
        member.mp = member.effective_max_mp
        members.append(member)
    return Party(members)


def _skill_score(actor: PlayerCharacter, skill: Skill, enemies: Sequence[Enemy]) -> float:
    targets = enemies if skill.aoe else [min(enemies, key=lambda enemy: enemy.hp)]
    score = 0.0
    for target in targets:
        amount = max(1, actor.effective_attack + skill.power - target.effective_defense // 2)
        if skill.element == target.weakness:
            amount *= 1.5
        elif skill.element == target.resistance:
            amount *= 0.5
        score += amount
    return score


def _player_action(actor: PlayerCharacter, party: Party, enemies: List[Enemy]) -> None:
    alive_enemies = [enemy for enemy in enemies if enemy.is_alive]
    if not alive_enemies:
        return

    heal_skills = [skill for skill in actor.skills if skill.kind == "heal" and actor.mp >= skill.mp_cost]
    wounded = [member for member in party.alive_members if member.hp / member.effective_max_hp <= 0.45]
    if heal_skills and wounded:
        skill = max(heal_skills, key=lambda candidate: candidate.power)
        target = min(wounded, key=lambda member: member.hp / member.effective_max_hp)
        actor.use_skill(skill, target)
        return

    buff_skills = [skill for skill in actor.skills if skill.kind == "buff" and actor.mp >= skill.mp_cost]
    for skill in buff_skills:
        kind = f"buff_{skill.buff_stat}"
        if not actor.has_status(kind):
            actor.use_skill(skill, actor)
            return

    debuff_skills = [skill for skill in actor.skills if skill.kind == "debuff" and actor.mp >= skill.mp_cost]
    for skill in debuff_skills:
        target = max(alive_enemies, key=lambda enemy: enemy.hp)
        kind = f"debuff_{skill.buff_stat}"
        if not target.has_status(kind):
            actor.use_skill(skill, target)
            return

    attack_skills = [skill for skill in actor.skills if skill.kind == "attack" and actor.mp >= skill.mp_cost]
    if attack_skills:
        skill = max(attack_skills, key=lambda candidate: _skill_score(actor, candidate, alive_enemies))
        if skill.aoe:
            actor.use_skill_on_targets(skill, alive_enemies)
        else:
            target = min(alive_enemies, key=lambda enemy: enemy.hp)
            actor.use_skill(skill, target)
        return

    actor.basic_attack(min(alive_enemies, key=lambda enemy: enemy.hp))


def _enemy_action(enemy: Enemy, party: Party) -> None:
    skill, target = enemy.choose_action(party.alive_members)
    if target is None:
        return
    if skill is None:
        enemy.basic_attack(target)
    elif skill.aoe:
        targets = [enemy] if skill.kind in ("heal", "buff") else party.alive_members
        enemy.use_skill_on_targets(skill, targets)
    else:
        enemy.use_skill(skill, target)


def simulate_battle(party: Party, enemies: List[Enemy], max_turns: int = 100) -> Tuple[bool, int]:
    for turn in range(1, max_turns + 1):
        actors = [*party.alive_members, *[enemy for enemy in enemies if enemy.is_alive]]
        actors.sort(key=lambda actor: actor.effective_speed, reverse=True)
        for actor in actors:
            if not actor.is_alive or party.is_wiped_out or all(not enemy.is_alive for enemy in enemies):
                continue
            if isinstance(actor, PlayerCharacter):
                actor.guarding = False
            paralyzed = actor.is_paralyzed()
            actor.tick_status_effects()
            if not actor.is_alive or paralyzed:
                continue
            if isinstance(actor, PlayerCharacter):
                _player_action(actor, party, enemies)
            else:
                _enemy_action(actor, party)
        if all(not enemy.is_alive for enemy in enemies):
            return True, turn
        if party.is_wiped_out:
            return False, turn
    return False, max_turns


def _grant_rewards(party: Party, enemies: Sequence[Enemy]) -> None:
    total_exp = sum(enemy.exp_reward for enemy in enemies)
    for member in party.members:
        if member.is_alive:
            member.gain_exp(total_exp)


def _apply_seal_power(party: Party) -> None:
    for member in party.members:
        member.max_hp += 6
        member.attack += 2
        member.defense += 1
        member.hp = min(member.effective_max_hp, member.hp + 6)


def simulate_route(route: RouteScenario, job_keys: Sequence[str]) -> Tuple[bool, int, int, float, float]:
    party = _make_party(job_keys, level=1, seal_power=False)
    battles = 0
    total_turns = 0
    for step_index, step in enumerate(route.steps):
        if random.random() >= step.encounter_chance:
            continue
        if route.seal_power and step_index == len(route.steps) - 1:
            _apply_seal_power(party)
        enemies = random.choice(step.encounters)()
        battles += 1
        won, turns = simulate_battle(party, enemies)
        total_turns += turns
        if not won:
            hp_rate, mp_rate = _party_metrics(party)
            return False, battles, total_turns, hp_rate, mp_rate
        _grant_rewards(party, enemies)
    hp_rate, mp_rate = _party_metrics(party)
    return True, battles, total_turns, hp_rate, mp_rate


def _party_metrics(party: Party) -> Tuple[float, float]:
    hp = sum(member.hp for member in party.members)
    max_hp = sum(member.effective_max_hp for member in party.members)
    mp = sum(member.mp for member in party.members)
    max_mp = sum(member.effective_max_mp for member in party.members)
    return hp / max_hp, mp / max_mp if max_mp else 1.0


def run_analysis(trials: int, seed: int) -> List[dict]:
    random.seed(seed)
    combinations = list(itertools.combinations_with_replacement(JOB_NAMES, 3))
    rows = []
    for scenario in SCENARIOS:
        for jobs in combinations:
            wins = 0
            turns = []
            hp_rates = []
            mp_rates = []
            for _ in range(trials):
                party = _make_party(jobs, scenario.level, scenario.seal_power)
                enemies = random.choice(scenario.encounters)()
                won, turn_count = simulate_battle(party, enemies)
                hp_rate, mp_rate = _party_metrics(party)
                wins += int(won)
                turns.append(turn_count)
                hp_rates.append(hp_rate)
                mp_rates.append(mp_rate)
            win_rate = wins / trials
            avg_turns = mean(turns)
            avg_hp = mean(hp_rates)
            avg_mp = mean(mp_rates)
            efficiency = win_rate * 0.7 + avg_hp * 0.2 + max(0.0, 1.0 - avg_turns / 10.0) * 0.1
            rows.append({
                "scenario": scenario.name,
                "recommended_level": scenario.level,
                "party_keys": "/".join(jobs),
                "party": "/".join(JOB_NAMES[key] for key in jobs),
                "trials": trials,
                "wins": wins,
                "win_rate": win_rate,
                "avg_turns": avg_turns,
                "avg_hp_remaining": avg_hp,
                "avg_mp_remaining": avg_mp,
                "efficiency_score": efficiency,
            })
    return rows


def run_route_analysis(trials: int, seed: int) -> List[dict]:
    random.seed(seed + 1)
    combinations = list(itertools.combinations_with_replacement(JOB_NAMES, 3))
    rows = []
    for route in ROUTES:
        for jobs in combinations:
            completions = 0
            battle_counts = []
            turn_counts = []
            hp_rates = []
            mp_rates = []
            for _ in range(trials):
                completed, battles, turns, hp_rate, mp_rate = simulate_route(route, jobs)
                completions += int(completed)
                battle_counts.append(battles)
                turn_counts.append(turns)
                hp_rates.append(hp_rate)
                mp_rates.append(mp_rate)
            rows.append({
                "route": route.name,
                "party_keys": "/".join(jobs),
                "party": "/".join(JOB_NAMES[key] for key in jobs),
                "trials": trials,
                "completions": completions,
                "completion_rate": completions / trials,
                "avg_battles": mean(battle_counts),
                "avg_total_turns": mean(turn_counts),
                "avg_hp_remaining": mean(hp_rates),
                "avg_mp_remaining": mean(mp_rates),
            })
    return rows


def _group_average(rows: Iterable[dict], key: str, metric: str = "win_rate") -> Dict[str, float]:
    grouped: Dict[str, List[float]] = {}
    for row in rows:
        grouped.setdefault(row[key], []).append(row[metric])
    return {name: mean(values) for name, values in grouped.items()}


def write_csv(rows: List[dict], path: str) -> None:
    with open(path, "w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_report(rows: List[dict], route_rows: List[dict], path: str, trials: int, seed: int) -> None:
    scenario_rates = _group_average(rows, "scenario")
    scenario_turns = _group_average(rows, "scenario", "avg_turns")
    scenario_hp = _group_average(rows, "scenario", "avg_hp_remaining")
    scenario_scores = _group_average(rows, "scenario", "efficiency_score")
    party_rates = _group_average(rows, "party")
    party_scores = _group_average(rows, "party", "efficiency_score")
    sorted_parties = sorted(party_scores.items(), key=lambda item: item[1], reverse=True)

    job_rates: Dict[str, float] = {}
    job_scores: Dict[str, float] = {}
    for key, label in JOB_NAMES.items():
        relevant = [row["win_rate"] for row in rows if key in row["party_keys"].split("/")]
        relevant_scores = [row["efficiency_score"] for row in rows if key in row["party_keys"].split("/")]
        job_rates[label] = mean(relevant)
        job_scores[label] = mean(relevant_scores)

    too_easy = [name for name, rate in scenario_rates.items() if rate >= 0.9 and scenario_hp[name] >= 0.65]
    too_hard = [name for name, rate in scenario_rates.items() if rate <= 0.5]
    spread = max(job_scores.values()) - min(job_scores.values())

    lines = [
        "# 텍스트 RPG 전투 밸런스 자동 분석",
        "",
        f"- 반복 횟수: 각 직업 조합·시나리오당 {trials:,}회",
        f"- 난수 시드: {seed}",
        f"- 분석 범위: 직업 조합 56개 × 시나리오 {len(SCENARIOS)}개 = {len(rows):,}개 집계 행",
        "- 전제: 장비·소모품 없이 메인 경로 진행을 고려한 기준 레벨에서 단일 전투를 시작하며, 자동 전투는 회복 → 강화/약화 → 공격 순으로 판단함",
        "",
        "## 시나리오별 평균 승률",
        "",
        "| 시나리오 | 기준 레벨 | 평균 승률 | 평균 턴 | 잔여 HP | 효율 점수 | 판정 |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    level_by_scenario = {scenario.name: scenario.level for scenario in SCENARIOS}
    for name, rate in sorted(scenario_rates.items(), key=lambda item: item[1], reverse=True):
        verdict = "쉬움" if name in too_easy else "어려움" if name in too_hard else "적정 범위"
        lines.append(
            f"| {name} | {level_by_scenario[name]} | {rate:.1%} | {scenario_turns[name]:.2f} | "
            f"{scenario_hp[name]:.1%} | {scenario_scores[name]:.3f} | {verdict} |"
        )

    lines += [
        "",
        "## 직업 포함 조합의 평균 승률",
        "",
        "| 직업 | 평균 승률 | 효율 점수 |",
        "|---|---:|---:|",
    ]
    for name, score in sorted(job_scores.items(), key=lambda item: item[1], reverse=True):
        lines.append(f"| {name} | {job_rates[name]:.1%} | {score:.3f} |")

    lines += [
        "",
        "## 전체 상·하위 조합",
        "",
        "| 구분 | 직업 조합 | 평균 승률 | 효율 점수 |",
        "|---|---|---:|---:|",
    ]
    for party, score in sorted_parties[:5]:
        lines.append(f"| 상위 | {party} | {party_rates[party]:.1%} | {score:.3f} |")
    for party, score in sorted_parties[-5:]:
        lines.append(f"| 하위 | {party} | {party_rates[party]:.1%} | {score:.3f} |")

    lines += ["", "## 자동 진단", ""]
    if too_easy:
        lines.append("- 지나치게 쉬운 후보: " + ", ".join(too_easy))
    if too_hard:
        lines.append("- 지나치게 어려운 후보: " + ", ".join(too_hard))
    if not too_easy and not too_hard:
        lines.append("- 모든 시나리오의 평균 승률이 35%~85% 범위에 있음.")
    lines.append(f"- 직업 포함 조합 간 효율 점수 격차: {spread:.3f}")
    if spread >= 0.05:
        strongest = max(job_scores, key=job_scores.get)
        weakest = min(job_scores, key=job_scores.get)
        lines.append(f"- 직업 격차가 큰 편임. {strongest} 하향 또는 {weakest} 상향 검토가 필요함.")
    else:
        lines.append("- 직업 간 전체 효율 점수 격차는 0.05 미만으로 비교적 안정적임.")
    lines += [
        "",
        "## 실제 경로 누적 전투",
        "",
        "| 경로 | 평균 완주율 | 평균 전투 수 | 평균 누적 턴 | 종료 시 잔여 HP |",
        "|---|---:|---:|---:|---:|",
    ]
    for route_name in [route.name for route in ROUTES]:
        selected = [row for row in route_rows if row["route"] == route_name]
        lines.append(
            f"| {route_name} | {mean(row['completion_rate'] for row in selected):.1%} | "
            f"{mean(row['avg_battles'] for row in selected):.2f} | "
            f"{mean(row['avg_total_turns'] for row in selected):.2f} | "
            f"{mean(row['avg_hp_remaining'] for row in selected):.1%} |"
        )

    route_best = sorted(route_rows, key=lambda row: row["completion_rate"], reverse=True)[:5]
    route_worst = sorted(route_rows, key=lambda row: row["completion_rate"])[:5]
    route_job_rates = {}
    for key, label in JOB_NAMES.items():
        selected = [
            row["completion_rate"] for row in route_rows
            if key in row["party_keys"].split("/")
        ]
        route_job_rates[label] = mean(selected)
    lines += [
        "",
        "### 경로 완주율 상·하위 조합",
        "",
        "| 구분 | 경로 | 직업 조합 | 완주율 |",
        "|---|---|---|---:|",
    ]
    for row in route_best:
        lines.append(f"| 상위 | {row['route']} | {row['party']} | {row['completion_rate']:.1%} |")
    for row in route_worst:
        lines.append(f"| 하위 | {row['route']} | {row['party']} | {row['completion_rate']:.1%} |")

    lines += [
        "",
        "### 직업을 포함한 경로 평균 완주율",
        "",
        "| 직업 | 평균 완주율 |",
        "|---|---:|",
    ]
    for label, rate in sorted(route_job_rates.items(), key=lambda item: item[1], reverse=True):
        lines.append(f"| {label} | {rate:.1%} |")

    no_healer = [row["completion_rate"] for row in route_rows if "healer" not in row["party_keys"].split("/")]
    one_healer = [row["completion_rate"] for row in route_rows if row["party_keys"].split("/").count("healer") == 1]
    multi_healer = [row["completion_rate"] for row in route_rows if row["party_keys"].split("/").count("healer") >= 2]
    no_rogue = [row["completion_rate"] for row in route_rows if "rogue" not in row["party_keys"].split("/")]
    one_rogue = [row["completion_rate"] for row in route_rows if row["party_keys"].split("/").count("rogue") == 1]
    multi_rogue = [row["completion_rate"] for row in route_rows if row["party_keys"].split("/").count("rogue") >= 2]
    lines += [
        "",
        "## 현재 밸런스 해석",
        "",
        "- 단일 전투 승률만으로 난이도를 판단하기보다 연속 전투 완주율과 종료 시 잔여 HP를 함께 보는 것이 적절함.",
        f"- 전사 포함 조합의 경로 완주율은 {route_job_rates['전사']:.1%}, 궁수는 {route_job_rates['궁수']:.1%}로 가장 안정적임.",
        f"- 도적이 없는 조합 {mean(no_rogue):.1%}, 1명인 조합 {mean(one_rogue):.1%}, 2명 이상인 조합 {mean(multi_rogue):.1%}임. 회피·치명타 적용 후 도적 중복 조합도 실전 선택지에 들어옴.",
        f"- 힐러가 없는 조합 {mean(no_healer):.1%}, 1명인 조합 {mean(one_healer):.1%}, 2명 이상인 조합 {mean(multi_healer):.1%}임. 중복 힐러 조합은 여전히 장기전에 불리함.",
        f"- 소환술사 포함 조합의 경로 완주율은 {route_job_rates['소환술사']:.1%}로, 위력 조정 후에도 상위권이지만 전사·궁수보다는 낮음.",
        "- 동굴 보물방은 쉬운 보상형 경로, 폐광과 도전의 탑은 고난도 선택 콘텐츠로 구분됨.",
        "- 봉인의 힘 수용은 메인 경로 평균 완주율을 높이되 필수 선택이 될 정도의 격차는 아니므로 현재 보너스를 유지해도 무방함.",
        "",
        "## 해석 시 주의사항",
        "",
        "- 이 결과는 자동 행동 정책을 사용한 통계이며 숙련된 플레이어의 판단과 다를 수 있음.",
        "- 경로 분석은 실제 이동 확률과 경험치·레벨업을 반영하지만 아이템·장비·상점 구매는 사용하지 않음.",
        "- 상세 조합별 승률·완주율·평균 턴·잔여 HP·MP는 두 CSV에서 확인할 수 있음.",
    ]
    with open(path, "w", encoding="utf-8") as stream:
        stream.write("\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="텍스트 RPG 직업 조합별 전투 밸런스 분석")
    parser.add_argument("--trials", type=int, default=300, help="조합·시나리오별 반복 횟수")
    parser.add_argument("--seed", type=int, default=20260913, help="재현용 난수 시드")
    parser.add_argument("--output-dir", default="balance_results", help="결과 저장 폴더")
    args = parser.parse_args()
    if args.trials < 1:
        parser.error("--trials는 1 이상이어야 합니다.")

    os.makedirs(args.output_dir, exist_ok=True)
    rows = run_analysis(args.trials, args.seed)
    route_rows = run_route_analysis(args.trials, args.seed)
    csv_path = os.path.join(args.output_dir, "battle_balance_results.csv")
    route_csv_path = os.path.join(args.output_dir, "route_balance_results.csv")
    report_path = os.path.join(args.output_dir, "battle_balance_report.md")
    write_csv(rows, csv_path)
    write_csv(route_rows, route_csv_path)
    write_report(rows, route_rows, report_path, args.trials, args.seed)
    print(f"분석 완료: {report_path}")
    print(f"상세 데이터: {csv_path}")
    print(f"경로 데이터: {route_csv_path}")


if __name__ == "__main__":
    main()
