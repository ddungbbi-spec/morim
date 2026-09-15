"""5레벨 이후 마을에서 선택하는 2차 직업과 일회성 전직 보상."""

from dataclasses import dataclass
from typing import Dict, Tuple

from models import PlayerCharacter, Skill


ADVANCEMENT_LEVEL = 5


@dataclass(frozen=True)
class AdvancedJob:
    id: str
    base_job: str
    name: str
    description: str
    skill: Skill
    hp: int = 0
    mp: int = 0
    attack: int = 0
    defense: int = 0
    speed: int = 0
    critical_rate: float = 0.0
    evasion_rate: float = 0.0


ADVANCED_JOBS: Dict[str, AdvancedJob] = {
    job.id: job for job in (
        AdvancedJob("swordmaster", "전사", "검성", "강력한 단일 참격", Skill("무영참", 10, 18, description="검기로 적 하나를 벤다."), attack=4, speed=2),
        AdvancedJob("guardian", "전사", "수호기사", "아군을 지키는 전열", Skill("철벽의 맹세", 8, 0, kind="buff", description="방어력을 크게 높인다.", buff_stat="defense", buff_amount=8, buff_duration=3, buff_name="철벽"), hp=16, defense=4),
        AdvancedJob("pyromancer", "마법사", "화염술사", "화염 광역 공격", Skill("홍련폭풍", 14, 9, aoe=True, element="fire", description="적 전체에 화염 피해를 준다."), mp=10, attack=3),
        AdvancedJob("frostmage", "마법사", "빙결술사", "냉기 단일 공격", Skill("빙결창", 11, 19, element="ice", description="적 하나에 냉기 피해를 준다."), mp=10, defense=3),
        AdvancedJob("priest", "힐러", "성직자", "파티 전체 치유", Skill("성역의 기도", 14, 16, kind="heal", aoe=True, description="파티 전체의 HP를 회복한다."), hp=8, mp=8),
        AdvancedJob("sage", "힐러", "현자", "회복과 공격의 균형", Skill("심판의 빛", 10, 16, element="thunder", description="빛의 마력으로 적을 공격한다."), mp=8, attack=3),
        AdvancedJob("assassin", "도적", "암살자", "치명타와 빠른 참격", Skill("급소 기습", 9, 17, description="급소를 노리는 강력한 일격이다."), speed=3, critical_rate=0.08),
        AdvancedJob("thiefmaster", "도적", "대도", "높은 회피와 골드 획득", Skill("금고 털기", 7, 25, kind="steal", description="적에게서 최대 25G를 훔친다."), speed=2, evasion_rate=0.08),
        AdvancedJob("sniper", "궁수", "저격수", "고위력 단일 사격", Skill("일점 저격", 11, 20, description="적 하나를 정밀하게 저격한다."), attack=3, critical_rate=0.06),
        AdvancedJob("ranger", "궁수", "유격수", "다중 화살과 기동", Skill("화살비", 10, 7, aoe=True, description="적 전체에 화살비를 퍼붓는다."), speed=3, evasion_rate=0.05),
        AdvancedJob("spiritmaster", "소환술사", "정령사", "정령과 함께하는 치유", Skill("정령의 축복", 13, 12, kind="heal", aoe=True, description="정령의 힘으로 파티 전체를 회복한다."), hp=8, mp=8),
        AdvancedJob("summonlord", "소환술사", "소환군주", "강력한 광역 소환", Skill("소환: 봉황", 18, 11, aoe=True, element="fire", description="봉황의 불길로 적 전체를 공격한다."), mp=12, attack=3),
    )
}


def options_for(member: PlayerCharacter) -> Tuple[AdvancedJob, ...]:
    return tuple(job for job in ADVANCED_JOBS.values() if job.base_job == member.base_job)


def advance(member: PlayerCharacter, job_id: str) -> AdvancedJob:
    if member.level < ADVANCEMENT_LEVEL:
        raise ValueError(f"Lv.{ADVANCEMENT_LEVEL}부터 전직할 수 있습니다.")
    if member.advanced_job_id:
        raise ValueError("이미 2차 직업으로 전직했습니다.")
    job = ADVANCED_JOBS.get(job_id) if isinstance(job_id, str) else None
    if job is None or job.base_job != member.base_job:
        raise ValueError("이 파티원이 선택할 수 없는 2차 직업입니다.")
    member.job = job.name
    member.advanced_job_id = job.id
    member.max_hp += job.hp
    member.max_mp += job.mp
    member.attack += job.attack
    member.defense += job.defense
    member.speed += job.speed
    member.critical_rate = min(1.0, member.critical_rate + job.critical_rate)
    member.evasion_rate = min(0.75, member.evasion_rate + job.evasion_rate)
    member.hp = min(member.effective_max_hp, member.hp + job.hp)
    member.mp = min(member.effective_max_mp, member.mp + job.mp)
    if not any(skill.name == job.skill.name for skill in member.skills):
        member.skills.append(job.skill)
    return job
