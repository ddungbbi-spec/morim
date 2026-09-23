"""Battle-local chained physical attacks by different party members."""

from models import PlayerCharacter, Skill, StatusEffect


COMBO_BONUS = {
    "sword": 2, "dagger": 2, "spear": 3,
    "bow": 2, "axe": 3, "fist": 2,
}

COMBO_FINISHERS = {
    "sword": ("균형 붕괴", "debuff_defense", 3, -2, 0),
    "dagger": ("독혈 찌르기", "poison", 3, 0, 3),
    "spear": ("파갑 관통", "debuff_defense", 2, -4, 0),
    "bow": ("족쇄 표식", "debuff_speed", 2, -3, 0),
    "axe": ("기세 분쇄", "debuff_attack", 2, -3, 0),
    "fist": ("경맥 봉쇄", "paralysis", 1, 0, 0),
}


def can_chain(actor: PlayerCharacter, skill: Skill = None) -> bool:
    weapon = actor.equipment.get("weapon")
    return (
        weapon is not None and weapon.weapon_family in COMBO_BONUS
        and (skill is None or actor.base_job not in {"마법사", "힐러", "소환술사", "마도사"})
        and (skill is None or (skill.kind == "attack" and not skill.aoe and not skill.element))
    )


class ComboChain:
    def __init__(self):
        self.reset()

    def reset(self):
        self.target = None
        self.actor = None
        self.streak = 0

    def bonus(self, actor: PlayerCharacter, target, skill: Skill = None) -> int:
        if (not can_chain(actor, skill) or self.target is not target
                or self.actor is actor or not target.is_alive):
            return 0
        return min(self.streak, 2) * COMBO_BONUS[actor.equipment["weapon"].weapon_family]

    def finisher_name(self, actor: PlayerCharacter, target, skill: Skill = None) -> str:
        if self.streak != 2 or self.bonus(actor, target, skill) <= 0:
            return ""
        return COMBO_FINISHERS[actor.equipment["weapon"].weapon_family][0]

    def apply_finisher(
        self, actor: PlayerCharacter, target, landed: bool, skill: Skill = None,
    ) -> str:
        name = self.finisher_name(actor, target, skill)
        if not landed or not name or not target.is_alive:
            return ""
        _, kind, duration, modifier, poison_power = COMBO_FINISHERS[
            actor.equipment["weapon"].weapon_family
        ]
        mods = {"attack_mod": 0, "defense_mod": 0, "speed_mod": 0}
        if kind == "debuff_attack":
            mods["attack_mod"] = modifier
        elif kind == "debuff_defense":
            mods["defense_mod"] = modifier
        elif kind == "debuff_speed":
            mods["speed_mod"] = modifier
        target.apply_status(StatusEffect(
            kind=kind, name=name, remaining_turns=duration,
            power=poison_power, **mods,
        ))
        return f"3타 연계 마무리 [{name}]! {target.name}에게 특수 효과를 부여했다."

    def record(self, actor: PlayerCharacter, target, landed: bool, skill: Skill = None):
        if not landed or not can_chain(actor, skill) or not target.is_alive:
            self.reset()
        elif self.target is target and self.actor is not actor:
            self.streak = min(self.streak + 1, 3)
            self.actor = actor
        else:
            self.target, self.actor, self.streak = target, actor, 1
