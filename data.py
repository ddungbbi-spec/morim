"""
data.py
실제 게임 콘텐츠(직업, 스킬, 적, 아이템)를 정의하는 파일입니다.
새로운 스토리/던전/보스를 추가할 때는 주로 이 파일을 편집하면 됩니다.
"""

from models import Skill, SkillGrowth, Item, Equipment, PlayerCharacter, Enemy
import random


# ---------------------------------------------------------------------------
# 스킬 정의
# ---------------------------------------------------------------------------
FIRE = Skill(name="파이라", mp_cost=6, power=10, kind="attack", description="작은 화염구로 적을 공격한다. (화 속성)", element="fire")
BLIZZARD = Skill(name="블리자라", mp_cost=7, power=10, kind="attack", description="얼음 조각을 날려 적을 공격한다. (냉 속성)", element="ice")
THUNDER = Skill(name="선더라", mp_cost=8, power=11, kind="attack", description="번개를 내려 적을 공격한다. (뇌 속성)", element="thunder")
CURE = Skill(name="큐어", mp_cost=5, power=15, kind="heal", description="대상의 HP를 회복시킨다.")
LIGHT_ARROW = Skill(
    name="빛의 화살", mp_cost=0, power=3, kind="attack",
    description="응축한 빛을 날려 적을 공격한다. MP를 소모하지 않는다.",
)
SLASH = Skill(name="파워 슬래시", mp_cost=4, power=6, kind="attack", description="강한 베기로 큰 피해를 입힌다.")
DARK_BOLT = Skill(name="다크볼트", mp_cost=8, power=12, kind="attack", description="어둠의 힘으로 적을 공격한다.")
POISON_FANG = Skill(
    name="독니", mp_cost=0, power=3, kind="attack",
    description="작은 상처와 함께 독을 주입한다.",
    inflict_status="poison", status_name="중독", status_power=4, status_duration=3, status_chance=0.8,
)
PARALYZE_STRIKE = Skill(
    name="마비의 일격", mp_cost=6, power=4, kind="attack",
    description="강력한 일격으로 상대를 마비시키려 한다.",
    inflict_status="paralysis", status_name="마비", status_duration=1, status_chance=0.5,
)
SELF_MEND = Skill(
    name="자가 치유", mp_cost=5, power=12, kind="heal",
    description="상처를 스스로 치유한다.",
)
HEAVY_SMASH = Skill(
    name="강타", mp_cost=5, power=9, kind="attack",
    description="묵직한 무기로 강하게 내려친다.",
)
STEAL = Skill(
    name="훔치기", mp_cost=3, power=8, kind="steal",
    description="적을 공격하는 대신 골드를 훔친다 (최대 8G).",
)
PRECISE_SHOT = Skill(
    name="정밀 사격", mp_cost=3, power=7, kind="attack",
    description="급소를 노려 정확하게 명중시킨다.",
)
WAR_CRY = Skill(
    name="전투 함성", mp_cost=4, power=0, kind="buff",
    description="크게 함성을 질러 스스로의 공격력을 높인다.",
    buff_stat="attack", buff_amount=4, buff_duration=3, buff_name="공격력 강화",
)
WEAKEN = Skill(
    name="약화의 저주", mp_cost=4, power=0, kind="debuff",
    description="적에게 저주를 걸어 방어력을 낮춘다.",
    buff_stat="defense", buff_amount=3, buff_duration=3, buff_name="방어력 약화",
)
INTIMIDATING_ROAR = Skill(
    name="위협의 포효", mp_cost=5, power=0, kind="debuff",
    description="무시무시한 포효로 상대를 위축시켜 공격력을 낮춘다.",
    buff_stat="attack", buff_amount=3, buff_duration=2, buff_name="공격력 약화",
)
SUMMON_IFRIT = Skill(
    name="소환: 이프리트", mp_cost=12, power=20, kind="attack",
    description="불의 정령 이프리트를 불러내 하나의 적에게 큰 피해를 입힌다.",
)
SUMMON_RAMUH = Skill(
    name="소환: 라무", mp_cost=15, power=8, kind="attack", aoe=True,
    description="번개의 정령 라무를 불러내 모든 적에게 피해를 입힌다.",
)
JUDGMENT_LIGHT = Skill(
    name="심판의 빛", mp_cost=14, power=7, kind="attack", aoe=True,
    description="빛의 심판을 내려 모든 적에게 피해를 입힌다.",
)
RUSTY_STRIKE = Skill(
    name="녹슨 일격", mp_cost=0, power=4, kind="attack",
    description="녹슨 곡괭이로 내려찍어 상처를 감염시킨다.",
    inflict_status="poison", status_name="중독", status_power=3, status_duration=2, status_chance=0.6,
)
CURSE_WHISPER = Skill(
    name="저주의 속삭임", mp_cost=4, power=0, kind="debuff",
    description="섬뜩한 목소리로 속삭여 상대의 몸을 무겁게 만든다.",
    buff_stat="speed", buff_amount=3, buff_duration=3, buff_name="속도 약화",
)
FLAME_BREATH = Skill(
    name="화염 브레스", mp_cost=13, power=8, kind="attack", aoe=True,
    description="뜨거운 불길을 내뿜어 모든 적을 태운다.",
)
APOCALYPSE_STRIKE = Skill(
    name="종말의 일격", mp_cost=16, power=26, kind="attack",
    description="이 세상의 종말을 부르는 듯한 압도적인 일격을 가한다.",
)
CHAOS_WAVE = Skill(
    name="혼돈의 파동", mp_cost=13, power=6, kind="attack", aoe=True,
    description="혼돈의 힘이 파동처럼 퍼져나가 모든 적에게 피해를 준다.",
)

# ---------------------------------------------------------------------------
# 직업 성장용 스킬
# ---------------------------------------------------------------------------
GUARD_STANCE = Skill(
    name="수호 태세", mp_cost=4, power=0, kind="buff",
    description="방어 자세를 가다듬어 방어력을 높인다.",
    buff_stat="defense", buff_amount=5, buff_duration=2, buff_name="방어력 강화",
)
BRAVER_SLASH = Skill(
    name="브레이버 슬래시", mp_cost=5, power=9, kind="attack",
    description="파워 슬래시를 단련한 강력한 일격이다.",
)
SPINNING_SLASH = Skill(
    name="회전 베기", mp_cost=7, power=5, kind="attack", aoe=True,
    description="크게 회전하며 모든 적을 벤다.",
)
AERO = Skill(
    name="에어로라", mp_cost=7, power=10, kind="attack", element="wind",
    description="바람의 칼날로 적을 공격한다. (풍 속성)",
)
FIRAGA = Skill(
    name="파이가", mp_cost=9, power=14, kind="attack", element="fire",
    description="파이라를 강화한 고위 화염 마법이다. (화 속성)",
)
BLIZZAGA = Skill(
    name="블리자가", mp_cost=13, power=8, kind="attack", aoe=True, element="ice",
    description="얼음 폭풍으로 모든 적을 공격한다. (냉 속성)",
)
HEALING_WIND = Skill(
    name="치유의 바람", mp_cost=10, power=10, kind="heal", aoe=True,
    description="부드러운 바람으로 파티 전체의 HP를 회복한다.",
)
CURA = Skill(
    name="큐어라", mp_cost=8, power=24, kind="heal",
    description="큐어를 강화한 회복 마법이다.",
)
HOLY_LIGHT = Skill(
    name="성스러운 빛", mp_cost=10, power=7, kind="attack", aoe=True,
    description="성스러운 빛으로 모든 적을 공격한다.",
)
VENOM_KNIFE = Skill(
    name="독칼", mp_cost=3, power=4, kind="attack",
    description="독을 바른 칼날로 공격한다.",
    inflict_status="poison", status_name="중독", status_power=3,
    status_duration=2, status_chance=0.5,
)
MASTER_STEAL = Skill(
    name="대도둑의 손길", mp_cost=4, power=15, kind="steal",
    description="적에게서 더 많은 골드를 훔친다. (최대 15G)",
)
SHADOW_SLASH = Skill(
    name="그림자 베기", mp_cost=5, power=10, kind="attack",
    description="그림자처럼 파고들어 급소를 벤다.",
)
MULTI_SHOT = Skill(
    name="다중 사격", mp_cost=5, power=4, kind="attack", aoe=True,
    description="여러 화살을 쏘아 모든 적을 공격한다.",
)
PIERCING_SHOT = Skill(
    name="관통 사격", mp_cost=5, power=11, kind="attack",
    description="정밀 사격을 단련한 강력한 한 발이다.",
)
HAWKEYE = Skill(
    name="매의 눈", mp_cost=4, power=0, kind="buff",
    description="집중력을 높여 공격력을 강화한다.",
    buff_stat="attack", buff_amount=3, buff_duration=4, buff_name="매의 눈",
)
SUMMON_SHIVA = Skill(
    name="소환: 시바", mp_cost=11, power=18, kind="attack", element="ice",
    description="얼음의 정령 시바를 불러내 적을 공격한다. (냉 속성)",
)
SUMMON_IFRIT_EX = Skill(
    name="소환: 이프리트 EX", mp_cost=15, power=25, kind="attack", element="fire",
    description="성장한 이프리트의 힘으로 큰 피해를 준다. (화 속성)",
)
SUMMON_RAMUH_EX = Skill(
    name="소환: 라무 EX", mp_cost=18, power=11, kind="attack", aoe=True, element="thunder",
    description="성장한 라무의 번개로 모든 적을 공격한다. (뇌 속성)",
)
ROCK_COUNTER = Skill(
    name="암석 반격", mp_cost=0, power=5, kind="attack", aoe=True,
    description="몸의 균열에서 암석 파편을 폭발시켜 파티 전체에 반격한다.",
)


JOB_SKILL_GROWTH_BY_JOB = {
    "전사": {
        2: [SkillGrowth(GUARD_STANCE)],
        3: [SkillGrowth(BRAVER_SLASH, replaces="파워 슬래시")],
        4: [SkillGrowth(SPINNING_SLASH)],
    },
    "마법사": {
        2: [SkillGrowth(AERO)],
        3: [SkillGrowth(FIRAGA, replaces="파이라")],
        4: [SkillGrowth(BLIZZAGA)],
    },
    "힐러": {
        2: [SkillGrowth(HEALING_WIND)],
        3: [SkillGrowth(CURA, replaces="큐어")],
        4: [SkillGrowth(HOLY_LIGHT)],
    },
    "도적": {
        2: [SkillGrowth(VENOM_KNIFE)],
        3: [SkillGrowth(MASTER_STEAL, replaces="훔치기")],
        4: [SkillGrowth(SHADOW_SLASH)],
    },
    "궁수": {
        2: [SkillGrowth(MULTI_SHOT)],
        3: [SkillGrowth(PIERCING_SHOT, replaces="정밀 사격")],
        4: [SkillGrowth(HAWKEYE)],
    },
    "소환술사": {
        2: [SkillGrowth(SUMMON_SHIVA)],
        3: [SkillGrowth(SUMMON_IFRIT_EX, replaces="소환: 이프리트")],
        4: [SkillGrowth(SUMMON_RAMUH_EX, replaces="소환: 라무")],
    },
}


# ---------------------------------------------------------------------------
# 직업(잡) 템플릿 - 새 파티원을 만들 때 이 함수들을 사용하세요
# ---------------------------------------------------------------------------
def create_warrior(name: str) -> PlayerCharacter:
    return PlayerCharacter(
        name=name, job="전사", level=1,
        max_hp=45, max_mp=8, attack=12, defense=8, speed=6,
        skills=[SLASH, WAR_CRY],
        skill_progression=JOB_SKILL_GROWTH_BY_JOB["전사"],
    )


def create_mage(name: str) -> PlayerCharacter:
    return PlayerCharacter(
        name=name, job="마법사", level=1,
        max_hp=28, max_mp=25, attack=6, defense=3, speed=7,
        skills=[FIRE, BLIZZARD, THUNDER, WEAKEN],
        skill_progression=JOB_SKILL_GROWTH_BY_JOB["마법사"],
    )


def create_healer(name: str) -> PlayerCharacter:
    return PlayerCharacter(
        name=name, job="힐러", level=1,
        max_hp=32, max_mp=20, attack=6, defense=4, speed=5,
        skills=[CURE, LIGHT_ARROW],
        skill_progression=JOB_SKILL_GROWTH_BY_JOB["힐러"],
    )


def create_rogue(name: str) -> PlayerCharacter:
    return PlayerCharacter(
        name=name, job="도적", level=1,
        max_hp=34, max_mp=10, attack=9, defense=4, speed=10,
        skills=[STEAL],
        critical_rate=0.20, evasion_rate=0.15,
        skill_progression=JOB_SKILL_GROWTH_BY_JOB["도적"],
    )


def create_archer(name: str) -> PlayerCharacter:
    return PlayerCharacter(
        name=name, job="궁수", level=1,
        max_hp=36, max_mp=12, attack=10, defense=5, speed=8,
        skills=[PRECISE_SHOT],
        skill_progression=JOB_SKILL_GROWTH_BY_JOB["궁수"],
    )


def create_summoner(name: str) -> PlayerCharacter:
    return PlayerCharacter(
        name=name, job="소환술사", level=1,
        max_hp=26, max_mp=30, attack=5, defense=2, speed=6,
        skills=[SUMMON_IFRIT, SUMMON_RAMUH],
        skill_progression=JOB_SKILL_GROWTH_BY_JOB["소환술사"],
    )


# 직업 선택 메뉴(main.py)에서 사용하는 조회 테이블. 새 직업을 추가하면 여기에도 등록하세요.
JOB_CREATORS = {
    "warrior": create_warrior,
    "mage": create_mage,
    "healer": create_healer,
    "rogue": create_rogue,
    "archer": create_archer,
    "summoner": create_summoner,
}
JOB_LABELS = {
    "warrior": "전사 - 체력·방어력이 높은 근접 딜러 (파워 슬래시, 전투 함성)",
    "mage": "마법사 - MP가 많은 원거리 마법 공격형 (파이라/블리자라/선더라 3속성, 약화의 저주)",
    "healer": "힐러 - 파티를 회복시키는 지원형 (큐어)",
    "rogue": "도적 - 빠른 회피와 치명타, 추가 골드 획득에 특화 (훔치기)",
    "archer": "궁수 - 공수 균형이 좋은 딜러 (정밀 사격)",
    "summoner": "소환술사 - HP가 매우 낮은 대신 소환수로 강력한 단일/전체 공격 (소환: 이프리트/라무)",
}


# ---------------------------------------------------------------------------
# 적 템플릿
# ---------------------------------------------------------------------------
def create_slime() -> Enemy:
    return Enemy(
        name="슬라임", job="몬스터", level=1,
        max_hp=20, max_mp=0, attack=5, defense=2, speed=3,
        skills=[], exp_reward=8, gold_reward=4,
        loot_pool=[(POTION, 0.2)],
    )


def create_goblin() -> Enemy:
    return Enemy(
        name="고블린", job="몬스터", level=2,
        max_hp=30, max_mp=6, attack=8, defense=3, speed=5,
        skills=[SLASH], exp_reward=14, gold_reward=8,
        loot_pool=[(POTION, 0.15), (ETHER, 0.1)],
    )


def create_poison_spider() -> Enemy:
    return Enemy(
        name="독거미", job="몬스터", level=2,
        max_hp=22, max_mp=0, attack=6, defense=2, speed=6,
        skills=[POISON_FANG], exp_reward=12, gold_reward=6,
        loot_pool=[(ANTIDOTE, 0.25)],
    )


def create_wild_wolf() -> Enemy:
    """빠르고 공격적이지만 방어는 약한 타입"""
    return Enemy(
        name="야생 늑대", job="몬스터", level=1,
        max_hp=18, max_mp=0, attack=7, defense=2, speed=8,
        skills=[], exp_reward=10, gold_reward=5,
        loot_pool=[(POTION, 0.15)],
    )


def create_bat_swarm() -> Enemy:
    """체력은 낮지만 매우 빨라서 선공을 자주 가져가는 타입. 뇌 속성에 약함"""
    return Enemy(
        name="박쥐 무리", job="몬스터", level=1,
        max_hp=14, max_mp=0, attack=4, defense=1, speed=10,
        skills=[], exp_reward=7, gold_reward=3,
        weakness="thunder",
        loot_pool=[(ETHER, 0.1)],
    )


def create_orc_warrior() -> Enemy:
    """체력과 방어력이 높은 탱커형. 속도는 느림"""
    return Enemy(
        name="오크 전사", job="몬스터", level=3,
        max_hp=42, max_mp=6, attack=10, defense=6, speed=3,
        skills=[HEAVY_SMASH], exp_reward=20, gold_reward=11,
        loot_pool=[(POTION, 0.2), (ETHER, 0.1)],
    )


def create_forest_sprite() -> Enemy:
    """스스로를 회복시키며 오래 버티는 지원형. 화 속성에 약함 (식물 계열)"""
    return Enemy(
        name="숲의 정령", job="몬스터", level=2,
        max_hp=20, max_mp=15, attack=4, defense=3, speed=6,
        skills=[SELF_MEND], exp_reward=16, gold_reward=9,
        weakness="fire",
        loot_pool=[(ETHER, 0.2)],
    )


def create_dark_knight() -> Enemy:
    """보스급 적 예시"""
    return Enemy(
        name="다크 나이트", job="보스", level=5,
        max_hp=95, max_mp=28, attack=14, defense=8, speed=6,
        skills=[DARK_BOLT, PARALYZE_STRIKE, INTIMIDATING_ROAR], exp_reward=60, gold_reward=40,
        smart_ai=True,
        action_pattern=[INTIMIDATING_ROAR, DARK_BOLT, None, PARALYZE_STRIKE],
    )


def create_shadow_stalker() -> Enemy:
    """그림자 골짜기에 나오는 빠른 정예 몬스터. 마비를 노린다"""
    return Enemy(
        name="그림자 추적자", job="몬스터", level=4,
        max_hp=30, max_mp=8, attack=11, defense=4, speed=9,
        skills=[PARALYZE_STRIKE], exp_reward=22, gold_reward=13,
        loot_pool=[(POTION, 0.15), (ANTIDOTE, 0.1)],
    )


def create_cursed_wraith() -> Enemy:
    """그림자 골짜기의 원혼. 저주로 방어를 무너뜨린다"""
    return Enemy(
        name="저주받은 원혼", job="몬스터", level=4,
        max_hp=26, max_mp=14, attack=8, defense=4, speed=6,
        skills=[WEAKEN], exp_reward=21, gold_reward=12,
        loot_pool=[(ETHER, 0.15)],
    )


def create_cave_golem() -> Enemy:
    """동굴 보물방을 지키는 미니보스. 체력·방어력이 높은 탱커형"""
    return Enemy(
        name="동굴 골렘", job="미니보스", level=4,
        max_hp=70, max_mp=0, attack=11, defense=9, speed=3,
        skills=[HEAVY_SMASH], exp_reward=35, gold_reward=20,
        smart_ai=True, action_pattern=[None, HEAVY_SMASH],
        phase_skill=ROCK_COUNTER, phase_threshold=0.5,
    )


def create_tower_guardian() -> Enemy:
    """도전의 탑 정상을 지키는 최강급 보스. 자가강화, 강타, 전체공격을 모두 사용하는 복합형"""
    return Enemy(
        name="탑의 수호자", job="보스", level=8,
        max_hp=120, max_mp=40, attack=16, defense=10, speed=7,
        skills=[HEAVY_SMASH, JUDGMENT_LIGHT, WAR_CRY], exp_reward=90, gold_reward=60,
        smart_ai=True, action_pattern=[WAR_CRY, HEAVY_SMASH, JUDGMENT_LIGHT, None],
    )


def create_skeleton_miner() -> Enemy:
    """폐광에 나오는 언데드. 녹슨 곡괭이로 중독을 옮긴다"""
    return Enemy(
        name="스켈레톤 광부", job="몬스터", level=3,
        max_hp=32, max_mp=0, attack=9, defense=4, speed=4,
        skills=[RUSTY_STRIKE], exp_reward=17, gold_reward=9,
        loot_pool=[(POTION, 0.15)],
    )


def create_ghost_miner() -> Enemy:
    """폐광의 유령. 속도를 저주로 낮추는 방해형"""
    return Enemy(
        name="유령 광부", job="몬스터", level=3,
        max_hp=24, max_mp=12, attack=6, defense=3, speed=7,
        skills=[CURSE_WHISPER], exp_reward=18, gold_reward=10,
        loot_pool=[(ETHER, 0.15)],
    )


def create_mine_drake() -> Enemy:
    """폐광 가장 깊은 곳을 지키는 보스. 화염 브레스로 전체 공격을 가한다.
    불의 드레이크라 화 속성에는 강하지만 냉 속성에는 약하다"""
    return Enemy(
        name="탄광 드레이크", job="보스", level=6,
        max_hp=105, max_mp=35, attack=15, defense=9, speed=5,
        skills=[FLAME_BREATH, HEAVY_SMASH], exp_reward=70, gold_reward=45,
        smart_ai=True, weakness="ice", resistance="fire",
        action_pattern=[None, FLAME_BREATH, HEAVY_SMASH],
    )


def create_marsh_slime() -> Enemy:
    """안개 습지의 독성 점액 생물. 불에 약하고 냉기에 강하다."""
    return Enemy(
        name="늪지 슬라임", job="몬스터", level=3,
        max_hp=34, max_mp=0, attack=8, defense=5, speed=3,
        skills=[POISON_FANG], exp_reward=19, gold_reward=10,
        smart_ai=False, weakness="fire", resistance="ice",
        loot_pool=[(ANTIDOTE, 0.25)],
    )


def create_marsh_hunter() -> Enemy:
    """습지의 빠른 포식자. 마비 공격으로 약한 대상을 노린다."""
    return Enemy(
        name="습지 사냥꾼", job="몬스터", level=4,
        max_hp=38, max_mp=10, attack=12, defense=4, speed=9,
        skills=[PARALYZE_STRIKE], exp_reward=24, gold_reward=14,
        loot_pool=[(POTION, 0.15), (ANTIDOTE, 0.1)],
    )


def create_will_o_wisp() -> Enemy:
    """침수된 길을 떠도는 불빛. 저주와 냉기 마법을 사용한다."""
    return Enemy(
        name="도깨비불", job="몬스터", level=4,
        max_hp=28, max_mp=18, attack=8, defense=3, speed=8,
        skills=[CURSE_WHISPER, BLIZZARD], exp_reward=23, gold_reward=13,
        resistance="fire", loot_pool=[(ETHER, 0.2)],
    )


def create_mist_queen() -> Enemy:
    """잊힌 사당을 지배하는 습지 보스. 약화와 광역 공격을 교차 사용한다."""
    return Enemy(
        name="안개의 여왕", job="보스", level=7,
        max_hp=125, max_mp=44, attack=15, defense=8, speed=8,
        skills=[WEAKEN, CHAOS_WAVE, PARALYZE_STRIKE], exp_reward=95, gold_reward=65,
        smart_ai=True, weakness="thunder", resistance="ice",
        action_pattern=[WEAKEN, CHAOS_WAVE, PARALYZE_STRIKE, None],
    )


def create_sealed_demon_lord() -> Enemy:
    """메인 스토리의 진짜 최종 보스. 폐허 지하에 봉인되어 있던 존재.
    강력한 단일 공격과 전체 공격, 마비를 섞어 쓰는 진짜 최종전다운 복합형"""
    return Enemy(
        name="봉인된 마왕", job="최종보스", level=7,
        max_hp=115, max_mp=45, attack=15, defense=9, speed=6,
        skills=[APOCALYPSE_STRIKE, CHAOS_WAVE, PARALYZE_STRIKE], exp_reward=100, gold_reward=70,
        smart_ai=True,
        action_pattern=[CHAOS_WAVE, PARALYZE_STRIKE, APOCALYPSE_STRIKE, None],
    )


# ---------------------------------------------------------------------------
# 아이템
# ---------------------------------------------------------------------------
POTION = Item(name="포션", heal_hp=25, description="HP를 25 회복한다.", price=15)
ETHER = Item(name="에테르", heal_mp=15, description="MP를 15 회복한다.", price=20)
ANTIDOTE = Item(name="해독제", cures_status="poison", description="중독 상태를 치료한다.", price=12)
MOONLIGHT_TONIC = Item(
    name="달빛 영약", heal_hp=40, heal_mp=10,
    description="세아가 달빛 샘의 약초로 만든 영약. HP 40과 MP 10을 회복한다.", price=35,
)
RUSTY_KEY = Item(
    name="녹슨 열쇠",
    description="낡은 열쇠. 어딘가의 잠긴 문에 맞을 것 같다.",
    usable_in_combat=False,
    sellable=False,
    key_item=True,
)


# ---------------------------------------------------------------------------
# 장비 (무기 / 방어구 / 장신구)
# ---------------------------------------------------------------------------
IRON_SWORD = Equipment(
    name="철검", slot="weapon", attack_bonus=5,
    description="흔하지만 튼튼한 검. 공격력 +5", price=50, rarity="common",
)
OAK_STAFF = Equipment(
    name="참나무 지팡이", slot="weapon", attack_bonus=2, max_mp_bonus=8,
    description="마력을 담기 좋은 지팡이. 공격력 +2, 최대 MP +8", price=55, rarity="uncommon",
)
LEATHER_ARMOR = Equipment(
    name="가죽 갑옷", slot="armor", defense_bonus=4, max_hp_bonus=10,
    description="가볍고 움직이기 편한 갑옷. 방어력 +4, 최대 HP +10", price=45, rarity="common",
)
SWIFT_CHARM = Equipment(
    name="신속의 부적", slot="accessory", speed_bonus=3,
    description="몸을 가볍게 만들어주는 부적. 속도 +3, 회피율 +3%", price=40,
    rarity="uncommon", evasion_rate_bonus=0.03, special_effect="회피율 +3%",
)
MITHRIL_DAGGER = Equipment(
    name="미스릴 대거", slot="weapon", attack_bonus=7, speed_bonus=2,
    description="동굴 깊은 곳에서만 발견되는 희귀한 단검. 공격력 +7, 속도 +2",
    price=60, rarity="rare", critical_rate_bonus=0.10, special_effect="치명타율 +10%",
)
LEGENDARY_ARMOR = Equipment(
    name="전설의 갑옷", slot="armor", defense_bonus=8, max_hp_bonus=20,
    description="도전의 탑 정상에서만 얻을 수 있는 전설의 갑옷. 방어력 +8, 최대 HP +20",
    price=120, rarity="legendary", damage_reduction_bonus=0.10, special_effect="받는 피해 10% 감소",
)
DRAKE_SCALE_ARMOR = Equipment(
    name="드레이크 비늘 갑옷", slot="armor", defense_bonus=6, max_hp_bonus=15,
    description="탄광 드레이크의 비늘로 만든 갑옷. 방어력 +6, 최대 HP +15",
    price=85, rarity="rare", damage_reduction_bonus=0.05, special_effect="받는 피해 5% 감소",
)
SEALBREAKER_BLADE = Equipment(
    name="봉인 해방의 검", slot="weapon", attack_bonus=10, defense_bonus=2,
    description="봉인된 마왕을 쓰러뜨린 자만이 얻을 수 있는 전설의 검. 공격력 +10, 방어력 +2",
    price=100, rarity="legendary", critical_rate_bonus=0.15, special_effect="치명타율 +15%",
)
LUCKY_RING = Equipment(
    name="행운의 반지", slot="accessory", attack_bonus=2, speed_bonus=2,
    description="동굴 비밀 금고에서 발견한 반지. 공격력 +2, 속도 +2",
    price=45, rarity="rare", critical_rate_bonus=0.05, evasion_rate_bonus=0.05,
    special_effect="치명타율·회피율 +5%",
)


MIST_CLOAK = Equipment(
    name="안개의 망토", slot="armor", defense_bonus=5, speed_bonus=2, max_hp_bonus=8,
    description="안개의 여왕이 두르던 망토. 방어력 +5, 속도 +2, 최대 HP +8",
    price=95, rarity="rare", evasion_rate_bonus=0.05, special_effect="회피율 +5%",
)

ELDER_GUARDIAN_SIGIL = Equipment(
    name="장로의 수호 인장", slot="accessory", defense_bonus=2, max_hp_bonus=6,
    description="마을을 지키겠다고 맹세한 이에게 맡기는 인장. 방어력 +2, 최대 HP +6",
    price=55, rarity="uncommon", damage_reduction_bonus=0.03,
    special_effect="받는 피해 3% 감소",
)


RANDOM_EQUIPMENT_BASES = [
    ("강철검", "weapon"),
    ("여행자 지팡이", "weapon"),
    ("비늘 조끼", "armor"),
    ("모험가 부적", "accessory"),
]
RANDOM_AFFIXES = [
    ("예리함", {"attack_bonus": 2}),
    ("견고함", {"defense_bonus": 2}),
    ("활력", {"max_hp_bonus": 8}),
    ("신속", {"speed_bonus": 2, "evasion_rate_bonus": 0.03}),
    ("집중", {"critical_rate_bonus": 0.05}),
]
RARITY_WEIGHTS = [0.55, 0.30, 0.12, 0.03]
RARITY_AFFIX_COUNTS = {"common": 0, "uncommon": 1, "rare": 2, "legendary": 3}
RARITY_PRICE_MULTIPLIERS = {"common": 1.0, "uncommon": 1.4, "rare": 2.0, "legendary": 3.2}


def generate_random_equipment(level: int) -> Equipment:
    """몬스터가 떨어뜨릴 레벨 비례 장비와 무작위 등급·옵션을 생성한다."""
    level = max(1, level)
    rarity = random.choices(
        ["common", "uncommon", "rare", "legendary"], weights=RARITY_WEIGHTS, k=1,
    )[0]
    base_name, slot = random.choice(RANDOM_EQUIPMENT_BASES)
    bonuses = {
        "attack_bonus": 0, "defense_bonus": 0, "speed_bonus": 0,
        "max_hp_bonus": 0, "max_mp_bonus": 0,
        "critical_rate_bonus": 0.0, "evasion_rate_bonus": 0.0,
        "damage_reduction_bonus": 0.0,
    }
    if slot == "weapon":
        bonuses["attack_bonus"] = 2 + level
    elif slot == "armor":
        bonuses["defense_bonus"] = 1 + level
        bonuses["max_hp_bonus"] = 3 + level * 2
    else:
        bonuses["speed_bonus"] = 1 + level // 2

    affixes = random.sample(RANDOM_AFFIXES, k=RARITY_AFFIX_COUNTS[rarity])
    for _, values in affixes:
        for field, amount in values.items():
            bonuses[field] += amount

    affix_names = [name for name, _ in affixes]
    suffix = f" · {'/'.join(affix_names)}" if affix_names else ""
    stat_parts = []
    stat_labels = {
        "attack_bonus": "공격력", "defense_bonus": "방어력", "speed_bonus": "속도",
        "max_hp_bonus": "최대 HP", "max_mp_bonus": "최대 MP",
    }
    for field, label in stat_labels.items():
        if bonuses[field]:
            stat_parts.append(f"{label} +{bonuses[field]}")
    if bonuses["critical_rate_bonus"]:
        stat_parts.append(f"치명타율 +{bonuses['critical_rate_bonus']:.0%}")
    if bonuses["evasion_rate_bonus"]:
        stat_parts.append(f"회피율 +{bonuses['evasion_rate_bonus']:.0%}")

    return Equipment(
        name=f"Lv.{level} {base_name}{suffix}", slot=slot,
        description=", ".join(stat_parts),
        price=int((18 + level * 9) * RARITY_PRICE_MULTIPLIERS[rarity]),
        rarity=rarity, special_effect="/".join(affix_names), generated=True,
        **bonuses,
    )


# ---------------------------------------------------------------------------
# 이름 -> 객체 조회 테이블 (save.py에서 저장된 이름으로 원본 객체를 복원할 때 사용)
# 새 스킬/아이템/장비를 추가하면 이 딕셔너리에도 함께 등록하세요.
# ---------------------------------------------------------------------------
SKILLS_BY_NAME = {
    s.name: s for s in [
        FIRE, BLIZZARD, THUNDER, CURE, LIGHT_ARROW, SLASH, DARK_BOLT, POISON_FANG, PARALYZE_STRIKE,
        SELF_MEND, HEAVY_SMASH, STEAL, PRECISE_SHOT,
        WAR_CRY, WEAKEN, INTIMIDATING_ROAR,
        SUMMON_IFRIT, SUMMON_RAMUH, JUDGMENT_LIGHT,
        RUSTY_STRIKE, CURSE_WHISPER, FLAME_BREATH,
        APOCALYPSE_STRIKE, CHAOS_WAVE, ROCK_COUNTER,
        GUARD_STANCE, BRAVER_SLASH, SPINNING_SLASH,
        AERO, FIRAGA, BLIZZAGA,
        HEALING_WIND, CURA, HOLY_LIGHT,
        VENOM_KNIFE, MASTER_STEAL, SHADOW_SLASH,
        MULTI_SHOT, PIERCING_SHOT, HAWKEYE,
        SUMMON_SHIVA, SUMMON_IFRIT_EX, SUMMON_RAMUH_EX,
    ]
}
ITEMS_BY_NAME = {it.name: it for it in [POTION, ETHER, ANTIDOTE, MOONLIGHT_TONIC, RUSTY_KEY]}
EQUIPMENT_BY_NAME = {
    e.name: e for e in [
        IRON_SWORD, OAK_STAFF, LEATHER_ARMOR, SWIFT_CHARM,
        MITHRIL_DAGGER, LEGENDARY_ARMOR, DRAKE_SCALE_ARMOR, SEALBREAKER_BLADE, LUCKY_RING,
        MIST_CLOAK,
        ELDER_GUARDIAN_SIGIL,
    ]
}
