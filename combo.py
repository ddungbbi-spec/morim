"""Battle-local chained physical attacks by different party members."""

from models import PlayerCharacter, Skill


COMBO_BONUS = {
    "sword": 2, "dagger": 2, "spear": 3,
    "bow": 2, "axe": 3, "fist": 2,
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

    def record(self, actor: PlayerCharacter, target, landed: bool, skill: Skill = None):
        if not landed or not can_chain(actor, skill) or not target.is_alive:
            self.reset()
        elif self.target is target and self.actor is not actor:
            self.streak = min(self.streak + 1, 3)
            self.actor = actor
        else:
            self.target, self.actor, self.streak = target, actor, 1
