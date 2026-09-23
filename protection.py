"""Battle-local one-hit ally protection links."""

from models import PlayerCharacter, Skill


class AllyProtection:
    def __init__(self):
        self._links = {}

    def reset(self):
        self._links.clear()

    def protect(self, protector: PlayerCharacter, target: PlayerCharacter):
        if protector is target:
            raise ValueError("자기 자신은 엄호 대상으로 선택할 수 없습니다.")
        if not protector.is_alive or not target.is_alive:
            raise ValueError("전투 가능한 파티원만 엄호할 수 있습니다.")
        self.clear_protector(protector)
        self._links[target] = protector

    def clear_protector(self, protector: PlayerCharacter):
        self._links = {
            target: guard for target, guard in self._links.items()
            if guard is not protector
        }

    def protector_for(self, target: PlayerCharacter):
        protector = self._links.get(target)
        if protector is not None and protector.is_alive and target.is_alive:
            return protector
        self._links.pop(target, None)
        return None

    def redirect(self, target: PlayerCharacter, skill: Skill = None):
        if skill is not None and (skill.kind != "attack" or skill.aoe):
            return target, ""
        protector = self.protector_for(target)
        if protector is None:
            return target, ""
        self._links.pop(target, None)
        return protector, f"{protector.name}이(가) {target.name}을(를) 엄호해 공격을 대신 받는다!"
