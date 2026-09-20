"""
models.py
게임의 핵심 데이터 구조(캐릭터, 스킬, 아이템)를 정의합니다.
새로운 직업/스킬/아이템을 추가할 때는 이 파일의 클래스를 사용하고,
실제 데이터는 data.py 에 채워 넣으세요.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import random
import time


@dataclass
class Skill:
    """전투/필드에서 사용하는 스킬(마법, 필살기 등)"""
    name: str
    mp_cost: int
    power: int              # 데미지 or 회복량 계산에 쓰이는 기준값
    kind: str = "attack"    # "attack", "heal", "steal", "buff", "debuff"
    description: str = ""
    # ---- 상태이상 부여 (kind == "attack"인 스킬에만 적용됨) ----
    inflict_status: Optional[str] = None   # "poison", "paralysis" 등 (STATUS_KINDS)
    status_name: str = ""                  # 화면에 보여줄 한글 이름 (예: "중독")
    status_power: int = 0                  # poison 등 매턴 피해량
    status_duration: int = 0               # 지속 턴 수
    status_chance: float = 1.0             # 부여 확률 (0.0 ~ 1.0)
    # ---- 버프/디버프 (kind == "buff" 또는 "debuff"인 스킬에만 적용됨) ----
    buff_stat: Optional[str] = None        # "attack", "defense", "speed" 중 하나
    buff_amount: int = 0                   # 오르내리는 수치 (항상 양수로 적고, debuff면 자동으로 빼줌)
    buff_duration: int = 0                 # 지속 턴 수
    buff_name: str = ""                    # 화면에 보여줄 한글 이름 (예: "공격력 강화")
    # ---- 전체 대상 스킬 ----
    aoe: bool = False                      # True면 (kind에 따라) 살아있는 적 전체 또는 아군 전체에게 사용
    # ---- 속성 (kind == "attack"인 스킬에만 적용됨) ----
    element: Optional[str] = None          # "fire", "ice", "thunder" 등. 대상의 weakness/resistance와 비교됨

    def use_message(self, user: "Character", target: "Character") -> str:
        return f"{user.name}의 [{self.name}]! {target.name}에게 사용!"


@dataclass(frozen=True)
class SkillGrowth:
    """특정 레벨에 배우는 스킬. replaces가 있으면 기존 스킬을 강화판으로 교체한다."""
    skill: Skill
    replaces: Optional[str] = None


@dataclass(frozen=True)
class BossPhase:
    """보스가 지정 체력 이하에서 전투당 한 번 발동하는 전용 행동."""

    threshold: float
    skill: Skill
    message: str


@dataclass
class Item:
    """소지품(포션, 회복 아이템 등)"""
    name: str
    heal_hp: int = 0
    heal_mp: int = 0
    description: str = ""
    price: int = 0
    cures_status: Optional[str] = None  # 이 아이템으로 치료되는 상태이상 종류 (예: "poison")
    usable_in_combat: bool = True
    sellable: bool = True
    key_item: bool = False


EQUIPMENT_SLOTS = ["weapon", "armor", "accessory"]
EQUIPMENT_RARITIES = ["common", "uncommon", "rare", "legendary"]
RARITY_NAMES_KR = {
    "common": "일반", "uncommon": "고급", "rare": "희귀", "legendary": "전설",
}

STATUS_KINDS = [
    "poison", "paralysis",
    "buff_attack", "debuff_attack",
    "buff_defense", "debuff_defense",
    "buff_speed", "debuff_speed",
]  # 새 상태이상을 추가하면 여기에도 등록


@dataclass
class StatusEffect:
    """캐릭터에게 걸린 상태이상/버프/디버프 한 건."""
    kind: str            # STATUS_KINDS 중 하나
    name: str            # 화면에 보여줄 한글 이름 (예: "중독", "공격력 강화")
    remaining_turns: int
    power: int = 0        # poison처럼 매턴 피해를 주는 효과의 피해량
    attack_mod: int = 0   # 버프/디버프로 인한 공격력 증감 (음수면 감소)
    defense_mod: int = 0  # 버프/디버프로 인한 방어력 증감
    speed_mod: int = 0    # 버프/디버프로 인한 속도 증감
    description: str = ""


@dataclass
class Equipment:
    """장비 아이템 (무기/방어구/장신구). 착용하면 스탯 보너스를 준다."""
    name: str
    slot: str  # "weapon", "armor", "accessory" 중 하나 (EQUIPMENT_SLOTS)
    attack_bonus: int = 0
    defense_bonus: int = 0
    speed_bonus: int = 0
    max_hp_bonus: int = 0
    max_mp_bonus: int = 0
    description: str = ""
    price: int = 0
    rarity: str = "common"
    critical_rate_bonus: float = 0.0
    evasion_rate_bonus: float = 0.0
    damage_reduction_bonus: float = 0.0
    special_effect: str = ""
    generated: bool = False
    enhancement_level: int = 0

    @property
    def stat_text(self) -> str:
        labels = {"attack_bonus": "공격력", "defense_bonus": "방어력",
                  "speed_bonus": "속도", "max_hp_bonus": "최대 HP",
                  "max_mp_bonus": "최대 MP"}
        parts = [f"{label} {getattr(self, field):+d}"
                 for field, label in labels.items() if getattr(self, field)]
        for field, label in (("critical_rate_bonus", "치명타율"),
                             ("evasion_rate_bonus", "회피율"),
                             ("damage_reduction_bonus", "피해 감소")):
            value = getattr(self, field)
            if value:
                parts.append(f"{label} {value * 100:+g}%")
        return " / ".join(parts) or "능력치 보너스 없음"

    @property
    def display_description(self) -> str:
        # Old saves may contain pre-enhancement numbers in description.
        # Keep that flavor text stored, but derive displayed stats from fields.
        return self.stat_text

    @property
    def display_name(self) -> str:
        enhancement = f" +{self.enhancement_level}" if self.enhancement_level else ""
        return f"[{RARITY_NAMES_KR.get(self.rarity, self.rarity)}] {self.name}{enhancement}"


class Character:
    """플레이어 캐릭터와 적(Enemy)의 공통 베이스 클래스"""

    def __init__(
        self,
        name: str,
        job: str,
        level: int,
        max_hp: int,
        max_mp: int,
        attack: int,
        defense: int,
        speed: int,
        skills: Optional[List[Skill]] = None,
        critical_rate: float = 0.0,
        evasion_rate: float = 0.0,
    ):
        self.name = name
        self.job = job
        self.level = level
        self.max_hp = max_hp
        self.hp = max_hp
        self.max_mp = max_mp
        self.mp = max_mp
        self.attack = attack
        self.defense = defense
        self.speed = speed
        self.skills = skills or []
        self.critical_rate = max(0.0, min(1.0, critical_rate))
        self.evasion_rate = max(0.0, min(1.0, evasion_rate))
        self.exp = 0
        self.equipment = {slot: None for slot in EQUIPMENT_SLOTS}  # type: dict
        self.status_effects: List[StatusEffect] = []
        self.guarding = False
        self.last_attack_was_critical = False
        self.last_damage_evaded = False

    # ---- 장비 ----
    def equip(self, item: Equipment) -> Optional[Equipment]:
        """장비를 착용합니다. 같은 슬롯에 이미 있던 장비가 있으면 반환합니다(교체됨)."""
        previous = self.equipment.get(item.slot)
        self.equipment[item.slot] = item
        self.hp = min(self.effective_max_hp, self.hp)
        self.mp = min(self.effective_max_mp, self.mp)
        return previous

    def unequip(self, slot: str) -> Optional[Equipment]:
        previous = self.equipment.get(slot)
        self.equipment[slot] = None
        self.hp = min(self.hp, self.effective_max_hp)
        self.mp = min(self.mp, self.effective_max_mp)
        return previous

    # ---- 장비 + 버프/디버프가 반영된 실제 스탯 ----
    @property
    def effective_attack(self) -> int:
        equip_bonus = sum(e.attack_bonus for e in self.equipment.values() if e)
        status_bonus = sum(s.attack_mod for s in self.status_effects)
        return max(0, self.attack + equip_bonus + status_bonus)

    @property
    def effective_defense(self) -> int:
        equip_bonus = sum(e.defense_bonus for e in self.equipment.values() if e)
        status_bonus = sum(s.defense_mod for s in self.status_effects)
        return max(0, self.defense + equip_bonus + status_bonus)

    @property
    def effective_speed(self) -> int:
        equip_bonus = sum(e.speed_bonus for e in self.equipment.values() if e)
        status_bonus = sum(s.speed_mod for s in self.status_effects)
        return max(1, self.speed + equip_bonus + status_bonus)

    @property
    def effective_max_hp(self) -> int:
        return self.max_hp + sum(e.max_hp_bonus for e in self.equipment.values() if e)

    @property
    def effective_max_mp(self) -> int:
        return self.max_mp + sum(e.max_mp_bonus for e in self.equipment.values() if e)

    @property
    def effective_critical_rate(self) -> float:
        bonus = sum(e.critical_rate_bonus for e in self.equipment.values() if e)
        return max(0.0, min(1.0, self.critical_rate + bonus))

    @property
    def effective_evasion_rate(self) -> float:
        bonus = sum(e.evasion_rate_bonus for e in self.equipment.values() if e)
        return max(0.0, min(0.75, self.evasion_rate + bonus))

    @property
    def effective_damage_reduction(self) -> float:
        bonus = sum(e.damage_reduction_bonus for e in self.equipment.values() if e)
        return max(0.0, min(0.5, bonus))

    # ---- 상태이상 ----
    def apply_status(self, effect: StatusEffect) -> None:
        """상태이상을 겁니다. 같은 종류가 이미 있다면 새 지속시간으로 갱신합니다."""
        self.remove_status(effect.kind)
        self.status_effects.append(effect)

    def remove_status(self, kind: str) -> None:
        self.status_effects = [e for e in self.status_effects if e.kind != kind]

    def has_status(self, kind: str) -> bool:
        return any(e.kind == kind for e in self.status_effects)

    def is_paralyzed(self) -> bool:
        return self.has_status("paralysis")

    def tick_status_effects(self) -> List[str]:
        """
        턴이 시작될 때 호출합니다. 중독 등 매턴 효과를 적용하고 지속시간을 1 줄입니다.
        화면에 출력할 메시지 목록을 반환합니다.
        """
        messages: List[str] = []
        still_active: List[StatusEffect] = []
        for effect in self.status_effects:
            if effect.kind == "poison" and self.is_alive:
                self.hp = max(0, self.hp - effect.power)
                messages.append(f"{self.name}은(는) 중독 피해를 입었다! (-{effect.power})")

            effect.remaining_turns -= 1
            if effect.remaining_turns > 0:
                still_active.append(effect)
            else:
                messages.append(f"{self.name}의 [{effect.name}] 효과가 사라졌다.")
        self.status_effects = still_active
        return messages

    # ---- 상태 확인 ----
    @property
    def is_alive(self) -> bool:
        return self.hp > 0

    # ---- 행동 ----
    def basic_attack(self, target: "Character") -> int:
        """기본 공격. 데미지를 반환합니다."""
        rate = self.effective_critical_rate
        self.last_attack_was_critical = rate > 0 and random.random() < rate
        raw = self.effective_attack - target.effective_defense // 2
        variance = random.randint(-2, 2)
        damage = max(1, raw + variance)
        if self.last_attack_was_critical:
            damage = max(1, int(damage * 1.5))
        damage = target.receive_damage(damage)
        return damage

    def receive_damage(self, amount: int) -> int:
        """방어 상태를 반영해 피해를 적용하고 실제 피해량을 반환합니다."""
        evade_rate = self.effective_evasion_rate
        self.last_damage_evaded = evade_rate > 0 and random.random() < evade_rate
        if self.last_damage_evaded:
            return 0
        actual = max(1, (amount + 1) // 2) if self.guarding else max(1, amount)
        if self.effective_damage_reduction > 0:
            actual = max(1, int(actual * (1.0 - self.effective_damage_reduction)))
        self.hp = max(0, self.hp - actual)
        return actual

    def use_skill(self, skill: Skill, target: "Character"):
        """
        스킬 사용 (단일 대상). MP를 소모하고 효과를 적용합니다.
        (데미지 또는 회복량, 상태이상이 새로 걸렸는지 여부, 속성 효과: "weak"/"resist"/None) 튜플을 반환합니다.
        """
        if self.mp < skill.mp_cost:
            raise ValueError("MP가 부족합니다.")
        self.mp -= skill.mp_cost
        return self._apply_skill_effect(skill, target)

    def use_skill_on_targets(self, skill: Skill, targets: List["Character"]):
        """
        스킬 사용 (여러 대상, 전체공격/전체회복용). MP는 한 번만 소모합니다.
        [(대상, 데미지/회복량, 상태이상 부여 여부, 속성 효과), ...] 리스트를 반환합니다.
        """
        if self.mp < skill.mp_cost:
            raise ValueError("MP가 부족합니다.")
        self.mp -= skill.mp_cost
        results = []
        for t in targets:
            if not t.is_alive:
                continue
            amount, status_applied, effectiveness = self._apply_skill_effect(skill, t)
            results.append((t, amount, status_applied, effectiveness))
        return results

    def _apply_skill_effect(self, skill: Skill, target: "Character"):
        """MP 소모 없이 스킬 효과만 대상 하나에게 적용합니다. use_skill/use_skill_on_targets 내부용."""
        self.last_attack_was_critical = False
        if skill.kind == "attack":
            raw = self.effective_attack + skill.power - target.effective_defense // 2
            amount = max(1, raw)

            effectiveness = None
            if skill.element:
                target_weakness = getattr(target, "weakness", None)
                target_resistance = getattr(target, "resistance", None)
                if skill.element == target_weakness:
                    amount = int(amount * 1.5)
                    effectiveness = "weak"
                elif skill.element == target_resistance:
                    amount = max(1, int(amount * 0.5))
                    effectiveness = "resist"

            rate = self.effective_critical_rate
            self.last_attack_was_critical = rate > 0 and random.random() < rate
            if self.last_attack_was_critical:
                amount = max(1, int(amount * 1.5))

            amount = target.receive_damage(amount)

            status_applied = False
            if (
                skill.inflict_status and target.is_alive and not target.last_damage_evaded
                and random.random() < skill.status_chance
            ):
                target.apply_status(StatusEffect(
                    kind=skill.inflict_status,
                    name=skill.status_name or skill.inflict_status,
                    remaining_turns=skill.status_duration,
                    power=skill.status_power,
                ))
                status_applied = True
            return amount, status_applied, effectiveness
        elif skill.kind == "heal":
            amount = skill.power
            target.hp = min(target.effective_max_hp, target.hp + amount)
            return amount, False, None
        elif skill.kind == "steal":
            # 적에게서 골드를 훔친다 (Enemy가 아니면 훔칠 게 없음)
            stolen = 0
            if isinstance(target, Enemy) and not target.has_been_stolen_from:
                stolen = min(getattr(target, "gold_reward", 0), skill.power)
                target.has_been_stolen_from = True
            return stolen, False, None
        elif skill.kind in ("buff", "debuff"):
            sign = 1 if skill.kind == "buff" else -1
            mods = {"attack_mod": 0, "defense_mod": 0, "speed_mod": 0}
            if skill.buff_stat in ("attack", "defense", "speed"):
                mods[f"{skill.buff_stat}_mod"] = sign * skill.buff_amount
            status_kind = f"{skill.kind}_{skill.buff_stat}"
            default_name = f"{skill.buff_stat} " + ("강화" if skill.kind == "buff" else "약화")
            target.apply_status(StatusEffect(
                kind=status_kind,
                name=skill.buff_name or default_name,
                remaining_turns=skill.buff_duration,
                **mods,
            ))
            return 0, True, None
        else:
            # 향후 확장 지점
            return 0, False, None

    def take_item(self, item: Item):
        self.hp = min(self.effective_max_hp, self.hp + item.heal_hp)
        self.mp = min(self.effective_max_mp, self.mp + item.heal_mp)
        if item.cures_status:
            self.remove_status(item.cures_status)

    def status_line(self) -> str:
        base = f"{self.name} (Lv.{self.level})  HP {self.hp}/{self.effective_max_hp}  MP {self.mp}/{self.effective_max_mp}"
        if self.status_effects:
            tags = ", ".join(f"{e.name}({e.remaining_turns})" for e in self.status_effects)
            base += f"  [{tags}]"
        return base


class PlayerCharacter(Character):
    """플레이어가 조작하는 파티원. 경험치/레벨업 로직을 가짐."""

    def __init__(
        self, *args, skill_progression: Optional[Dict[int, List[SkillGrowth]]] = None, **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.skill_progression = skill_progression or {}
        self.base_job = self.job
        self.advanced_job_id = ""
        self.last_growth_messages: List[str] = []

    def sync_skills_for_level(self) -> List[str]:
        """현재 레벨까지의 습득·강화 스킬을 중복 없이 반영한다."""
        messages = []
        for level in sorted(self.skill_progression):
            if level > self.level:
                continue
            for growth in self.skill_progression[level]:
                if growth.replaces:
                    self.skills = [skill for skill in self.skills if skill.name != growth.replaces]
                if any(skill.name == growth.skill.name for skill in self.skills):
                    continue
                self.skills.append(growth.skill)
                if growth.replaces:
                    messages.append(f"[{growth.replaces}]이(가) [{growth.skill.name}](으)로 강화되었다!")
                else:
                    messages.append(f"새 스킬 [{growth.skill.name}]을(를) 습득했다!")
        return messages

    def gain_exp(self, amount: int) -> bool:
        """경험치 획득. 레벨업이 발생하면 True를 반환."""
        self.last_growth_messages = []
        self.exp += amount
        leveled_up = False
        exp_to_next = self.level * 20  # 간단한 레벨업 공식 (추후 조정 가능)
        while self.exp >= exp_to_next:
            self.exp -= exp_to_next
            self._level_up()
            leveled_up = True
            exp_to_next = self.level * 20
        return leveled_up

    def _level_up(self):
        self.level += 1
        self.max_hp += 8
        self.max_mp += 4
        self.attack += 2
        self.defense += 1
        self.speed += 1
        # 레벨업 시 완전 회복
        self.hp = self.effective_max_hp
        self.mp = self.effective_max_mp
        self.last_growth_messages.extend(self.sync_skills_for_level())


class Enemy(Character):
    """적 캐릭터. 처치 시 지급하는 경험치/골드를 가짐."""

    def __init__(
        self, *args, exp_reward: int = 10, gold_reward: int = 5, smart_ai: bool = False,
        weakness: Optional[str] = None, resistance: Optional[str] = None,
        loot_pool: Optional[List[Tuple[Item, float]]] = None,
        equipment_drop_chance: Optional[float] = None,
        action_pattern: Optional[List[Optional[Skill]]] = None,
        phase_skill: Optional[Skill] = None, phase_threshold: float = 0.5,
        boss_phases: Optional[List[BossPhase]] = None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.exp_reward = exp_reward
        self.gold_reward = gold_reward
        self.smart_ai = smart_ai  # True면 보스처럼 상황을 판단해서 대상을 고름 (일반 몹은 무작위가 기본)
        self.weakness = weakness      # 이 속성으로 공격받으면 피해 1.5배 (예: "fire")
        self.resistance = resistance  # 이 속성으로 공격받으면 피해 0.5배
        self.loot_pool = loot_pool or []  # [(Item, 드랍 확률 0.0~1.0), ...] - 처치 시 각각 독립적으로 판정
        self.equipment_drop_chance = (
            0.05 if equipment_drop_chance is None and self.job == "몬스터"
            else (equipment_drop_chance or 0.0)
        )
        self.has_been_stolen_from = False
        self.action_pattern = action_pattern or []
        self.action_count = 0
        self.phase_skill = phase_skill
        self.phase_threshold = phase_threshold
        self.boss_phases = sorted(
            list(boss_phases or []) + (
                [BossPhase(phase_threshold, phase_skill, f"{self.name}이(가) 새로운 힘을 드러낸다!")]
                if phase_skill is not None else []
            ),
            key=lambda phase: phase.threshold,
            reverse=True,
        )
        self.triggered_phase_indices = set()
        self.last_phase_message = ""
        self.phase_triggered = False

    def _pick_target(self, alive_targets: List[Character], prefer: str) -> Character:
        """
        smart_ai가 켜진 적이 상황에 맞춰 대상을 고를 때 사용.
        prefer="finish": 가장 HP가 낮은(먼저 쓰러뜨릴 수 있는) 대상 집중 공격
        prefer="threat": 공격력이 가장 높은(가장 위협적인) 대상을 노려 디버프
        """
        if not self.smart_ai:
            return random.choice(alive_targets)
        if prefer == "finish":
            return min(alive_targets, key=lambda t: t.hp)
        if prefer == "threat":
            return max(alive_targets, key=lambda t: t.effective_attack)
        return random.choice(alive_targets)

    def choose_action(self, targets: List[Character]):
        """
        일반 몬스터는 무작위로 행동/대상을 고르는 단순한 AI.
        smart_ai=True인 보스급은 회복/버프는 자신에게, 디버프는 가장 위협적인 상대에게,
        공격은 가장 약해진(HP가 낮은) 상대를 집중 공격하도록 판단한다.
        """
        alive_targets = [t for t in targets if t.is_alive]
        if not alive_targets:
            return None, None
        default_target = random.choice(alive_targets)
        self.last_phase_message = ""

        # 높은 체력 구간부터 순서대로 확인해 급격히 체력이 줄어도 페이즈를 건너뛰지 않는다.
        hp_ratio = self.hp / self.effective_max_hp
        for index, phase in enumerate(self.boss_phases):
            if (
                index not in self.triggered_phase_indices
                and hp_ratio <= phase.threshold
                and self.mp >= phase.skill.mp_cost
            ):
                self.triggered_phase_indices.add(index)
                self.phase_triggered = True  # 단일 phase_skill을 쓰는 기존 코드와 호환
                self.last_phase_message = phase.message
                return self._skill_and_target(phase.skill, alive_targets, default_target)

        # action_pattern이 있으면 지정된 순서대로 행동한다. None은 기본 공격이다.
        # MP가 모자란 스킬 차례에는 기본 공격으로 자연스럽게 대체한다.
        if self.action_pattern:
            skill = self.action_pattern[self.action_count % len(self.action_pattern)]
            self.action_count += 1
            if skill is not None and self.mp >= skill.mp_cost:
                return self._skill_and_target(skill, alive_targets, default_target)
            return None, self._pick_target(alive_targets, prefer="finish")

        usable_skills = [s for s in self.skills if self.mp >= s.mp_cost]
        if usable_skills and random.random() < 0.4:
            skill = random.choice(usable_skills)
            if skill.kind == "heal":
                if self.hp < self.effective_max_hp:
                    return skill, self  # 자기 자신을 회복
                return None, default_target  # 이미 만피면 그냥 공격
            if skill.kind == "buff":
                return skill, self       # 자기 자신을 강화
            if skill.kind == "debuff":
                return skill, self._pick_target(alive_targets, prefer="threat")
            return skill, self._pick_target(alive_targets, prefer="finish")  # attack, steal

        return None, self._pick_target(alive_targets, prefer="finish")  # None이면 기본 공격을 의미

    def _skill_and_target(
        self, skill: Skill, alive_targets: List[Character], default_target: Character,
    ):
        """보스 패턴 스킬의 종류에 맞춰 사용할 대상을 결정한다."""
        if skill.kind in ("heal", "buff"):
            return skill, self
        if skill.kind == "debuff":
            return skill, self._pick_target(alive_targets, prefer="threat")
        if skill.aoe:
            return skill, default_target  # 실제 광역 대상은 전투 엔진이 다시 구성함
        return skill, self._pick_target(alive_targets, prefer="finish")


class Party:
    """플레이어 파티 전체를 관리"""

    def __init__(
        self, members: List[PlayerCharacter], gold: int = 0,
        play_time_seconds: float = 0.0,
    ):
        self.members = members
        self.gold = gold
        self.play_time_seconds = max(0.0, float(play_time_seconds))
        self._session_started_at = time.monotonic()

    @property
    def total_play_time_seconds(self) -> int:
        """이전 세션과 현재 실행 시간을 합친 누적 플레이 시간."""
        elapsed = max(0.0, time.monotonic() - self._session_started_at)
        return int(self.play_time_seconds + elapsed)

    @property
    def alive_members(self) -> List[PlayerCharacter]:
        return [m for m in self.members if m.is_alive]

    @property
    def is_wiped_out(self) -> bool:
        return len(self.alive_members) == 0

    def full_restore(self) -> None:
        """전투 불능을 포함해 모든 파티원의 HP·MP와 상태이상을 회복한다."""
        for member in self.members:
            member.hp = member.effective_max_hp
            member.mp = member.effective_max_mp
            member.status_effects.clear()
            member.guarding = False

    def print_status(self):
        print(f"보유 골드: {self.gold} G")
        for m in self.members:
            print(" -", m.status_line())
