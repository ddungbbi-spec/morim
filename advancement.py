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
        AdvancedJob("berserker", "전사", "광전사", "공격과 생존력을 함께 끌어올리는 돌격 계열", Skill("핏빛 격노", 9, 21, description="상처를 힘으로 바꾸어 적 하나를 강하게 벤다."), hp=10, attack=5),
        AdvancedJob("stormcaller", "마법사", "폭풍술사", "바람 속성 광역 제압 계열", Skill("천공 폭풍", 15, 10, aoe=True, element="wind", description="거대한 폭풍으로 적 전체를 공격한다."), mp=9, speed=3),
        AdvancedJob("paladin", "힐러", "성기사", "방어 강화와 전열 유지 계열", Skill("성광의 방패", 10, 0, kind="buff", description="성스러운 방패로 방어력을 높인다.", buff_stat="defense", buff_amount=7, buff_duration=4, buff_name="성광의 방패"), hp=14, defense=4),
        AdvancedJob("shadowdancer", "도적", "그림자무희", "빠른 광역 공격과 회피 계열", Skill("월영난무", 11, 8, aoe=True, description="그림자를 오가며 적 전체를 연속 공격한다."), speed=4, evasion_rate=0.06),
        AdvancedJob("falconer", "궁수", "매사냥꾼", "속도 약화와 전장 통제 계열", Skill("매의 급강하", 8, 0, kind="debuff", description="매가 급강하해 적의 움직임을 봉쇄한다.", buff_stat="speed", buff_amount=5, buff_duration=3, buff_name="속도 약화"), attack=2, speed=3),
        AdvancedJob("necromancer", "소환술사", "사령술사", "중독을 누적하는 사령 광역 계열", Skill("망자의 숨결", 16, 8, aoe=True, description="사령의 독기로 적 전체를 공격한다.", inflict_status="poison", status_name="중독", status_power=5, status_duration=3, status_chance=0.7), mp=10, attack=3),
        AdvancedJob("crusader", "기사", "성전기사", "수호력과 단일 공격의 균형 계열", Skill("성전의 일격", 10, 19, element="light", description="성스러운 힘을 실어 적 하나를 공격한다."), hp=12, attack=4, defense=2),
        AdvancedJob("fortress", "기사", "철벽기사", "최대 체력과 방어에 집중한 요새 계열", Skill("불퇴의 성벽", 9, 0, kind="buff", description="절대 물러서지 않는 태세로 방어력을 크게 높인다.", buff_stat="defense", buff_amount=10, buff_duration=4, buff_name="불퇴의 성벽"), hp=22, defense=6, speed=-1),
        AdvancedJob("dragoon", "기사", "용기사", "기동력과 광역 창격 계열", Skill("용아천격", 12, 9, aoe=True, description="도약 후 내려찍어 적 전체를 공격한다."), attack=4, speed=3),
        AdvancedJob("fistking", "무도가", "권왕", "압도적인 단일 연타 계열", Skill("백열신권", 9, 22, description="보이지 않을 만큼 빠른 연타를 퍼붓는다."), hp=8, attack=5, critical_rate=0.06),
        AdvancedJob("qigongmaster", "무도가", "기공사", "원거리 기공과 광역 공격 계열", Skill("뇌명기공", 12, 10, aoe=True, element="thunder", description="번개의 기를 방출해 적 전체를 공격한다."), mp=10, attack=3),
        AdvancedJob("ascetic", "무도가", "수행승", "파티 회복과 생존 지원 계열", Skill("금강의 호흡", 12, 14, kind="heal", aoe=True, description="깊은 호흡으로 파티 전체의 HP를 회복한다."), hp=12, mp=7, defense=3),
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
