"""
combat.py
파이널 판타지 스타일의 턴제 전투를 처리합니다.
속도(speed)가 높을수록 먼저 행동합니다 (아주 단순화된 ATB 방식).
"""

from typing import List
from dataclasses import replace
import random
from combo import ComboChain, can_chain
from models import Party, Enemy, PlayerCharacter, Item, Skill
from input_utils import prompt_index

STAT_NAMES_KR = {"attack": "공격력", "defense": "방어력", "speed": "속도"}


def _describe_skill_result(
    actor_name: str, target_name: str, skill: Skill, amount: int,
    status_applied: bool, effectiveness: str = None,
    critical: bool = False, evaded: bool = False,
) -> List[str]:
    """스킬 사용 결과를 화면에 출력할 메시지 목록으로 만듭니다. (플레이어/적 공용)"""
    messages = []

    if skill.kind == "steal":
        if amount > 0:
            messages.append(f"{actor_name}의 [{skill.name}]! {target_name}에게서 골드 {amount}G를 훔쳤다!")
        else:
            messages.append(f"{actor_name}의 [{skill.name}]! 하지만 훔칠 골드가 없었다...")

    elif skill.kind in ("buff", "debuff"):
        stat_kr = STAT_NAMES_KR.get(skill.buff_stat, skill.buff_stat or "")
        verb = "상승했다" if skill.kind == "buff" else "하락했다"
        messages.append(f"{actor_name}의 [{skill.name}]! {target_name}의 {stat_kr}이(가) {verb}!")

    elif skill.kind == "attack" and evaded:
        messages.append(f"{actor_name}의 [{skill.name}]! {target_name}은(는) 공격을 회피했다!")

    else:
        verb = "회복" if skill.kind == "heal" else "피해"
        messages.append(f"{actor_name}의 [{skill.name}]! {target_name}에게 {amount} {verb}!")
        if critical:
            messages.append("치명타!")
        if effectiveness == "weak":
            messages.append("약점을 찔렀다!")
        elif effectiveness == "resist":
            messages.append("효과가 별로인 듯하다...")
        if status_applied:
            messages.append(f"{target_name}은(는) [{skill.status_name or skill.inflict_status}] 상태가 되었다!")

    return messages


class Battle:
    def __init__(
        self, party: Party, enemies: List[Enemy], inventory: List[Item],
        equipment_inventory=None,
    ):
        self.party = party
        self.enemies = enemies
        self.inventory = inventory  # 파티 공용 아이템 목록
        self.equipment_inventory = equipment_inventory if equipment_inventory is not None else []
        self.fled = False
        self.combo = ComboChain()

    # -----------------------------------------------------------------
    def run(self) -> bool:
        """전투를 실행한다. 승리 또는 도주면 True, 전멸이면 False를 반환한다."""
        print("\n=== 전투 시작! ===")
        self._print_enemies()

        turn = 1
        while True:
            self.combo.reset()
            print(f"\n--- 턴 {turn} ---")
            self._print_battle_status()
            order = self._turn_order()

            for actor in order:
                if not actor.is_alive:
                    continue
                if self.party.is_wiped_out or self._enemies_defeated():
                    break

                if isinstance(actor, PlayerCharacter):
                    actor.guarding = False

                if actor.status_effects:
                    paralyzed = actor.is_paralyzed()
                    for msg in actor.tick_status_effects():
                        print(msg)
                    if not actor.is_alive:
                        continue  # 상태이상 피해로 쓰러진 경우 행동하지 않음
                    if paralyzed:
                        if isinstance(actor, PlayerCharacter):
                            self.combo.reset()
                        print(f"{actor.name}은(는) 마비되어 움직일 수 없었다!")
                        continue

                if isinstance(actor, PlayerCharacter):
                    self._player_turn(actor)
                    if self.fled:
                        return True
                else:
                    self._enemy_turn(actor)

            if self._enemies_defeated():
                self._victory()
                return True
            if self.party.is_wiped_out:
                print("\n파티가 전멸했습니다... 게임 오버.")
                return False

            turn += 1

    # -----------------------------------------------------------------
    def _turn_order(self):
        combatants = [*self.party.alive_members, *[e for e in self.enemies if e.is_alive]]
        return sorted(combatants, key=lambda c: c.effective_speed, reverse=True)

    def _enemies_defeated(self) -> bool:
        return all(not e.is_alive for e in self.enemies)

    def _print_enemies(self):
        for e in self.enemies:
            print(" -", e.status_line())

    def _print_battle_status(self):
        print("[파티]")
        for member in self.party.members:
            print(" -", member.status_line())
        print("[적]")
        self._print_enemies()

    # -----------------------------------------------------------------
    def _player_turn(self, actor: PlayerCharacter):
        while True:
            print(f"\n{actor.status_line()}")
            print("행동: 1) 공격  2) 스킬  3) 아이템  4) 방어  5) 적 정보  6) 도망가기")
            choice = prompt_index("> ", 6) + 1

            alive_enemies = [e for e in self.enemies if e.is_alive]
            if not alive_enemies:
                return

            if choice == 1:
                target = self._choose_target(alive_enemies, allow_cancel=True)
                if target is None:
                    continue
                bonus = self.combo.bonus(actor, target)
                dmg = actor.basic_attack(target, bonus_power=bonus)
                landed = not target.last_damage_evaded
                self.combo.record(actor, target, landed)
                if target.last_damage_evaded:
                    print(f"{actor.name}의 공격! {target.name}은(는) 공격을 회피했다!")
                else:
                    critical = " 치명타!" if actor.last_attack_was_critical else ""
                    print(f"{actor.name}의 공격! {target.name}에게 {dmg}의 피해!{critical}")
                    if bonus:
                        print(f"연계 공격! 추가 위력 +{bonus}")
                return

            if choice == 2:
                if not actor.skills:
                    print("사용할 스킬이 없습니다.")
                    continue
                for i, skill in enumerate(actor.skills, 1):
                    print(f"  {i}) {skill.name} (MP {skill.mp_cost}) - {skill.description}")
                cancel = len(actor.skills) + 1
                print(f"  {cancel}) 이전 메뉴")
                skill_index = prompt_index("스킬 선택> ", cancel)
                if skill_index == cancel - 1:
                    continue
                skill = actor.skills[skill_index]

                if skill.aoe:
                    targets = self.party.alive_members if skill.kind in ("heal", "buff") else alive_enemies
                    try:
                        results = actor.use_skill_on_targets(skill, targets)
                    except ValueError as error:
                        print(error)
                        continue
                    print(f"{actor.name}의 [{skill.name}]!")
                    for target, amount, status_applied, effectiveness in results:
                        for msg in _describe_skill_result(
                            actor.name, target.name, skill, amount, status_applied, effectiveness,
                            actor.last_attack_was_critical, target.last_damage_evaded,
                        ):
                            print(msg)
                    self.combo.reset()
                    return

                candidates = self.party.alive_members if skill.kind in ("heal", "buff") else alive_enemies
                target = self._choose_target(candidates, allow_cancel=True)
                if target is None:
                    continue
                bonus = self.combo.bonus(actor, target, skill)
                try:
                    attack_skill = replace(skill, power=skill.power + bonus) if bonus else skill
                    amount, status_applied, effectiveness = actor.use_skill(attack_skill, target)
                except ValueError as error:
                    print(error)
                    continue

                if skill.kind == "steal":
                    self.party.gold += amount
                for msg in _describe_skill_result(
                    actor.name, target.name, skill, amount, status_applied, effectiveness,
                    actor.last_attack_was_critical, target.last_damage_evaded,
                ):
                    print(msg)
                self.combo.record(actor, target, not target.last_damage_evaded, skill)
                if bonus:
                    print(f"연계 공격! 추가 위력 +{bonus}")
                return

            if choice == 3:
                usable_items = [item for item in self.inventory if item.usable_in_combat]
                if not usable_items:
                    print("전투에서 사용할 수 있는 아이템이 없습니다.")
                    continue
                for i, item in enumerate(usable_items, 1):
                    print(f"  {i}) {item.name} - {item.description}")
                cancel = len(usable_items) + 1
                print(f"  {cancel}) 이전 메뉴")
                item_index = prompt_index("아이템 선택> ", cancel)
                if item_index == cancel - 1:
                    continue
                item = usable_items[item_index]
                target = self._choose_target(self.party.alive_members, allow_cancel=True)
                if target is None:
                    continue
                target.take_item(item)
                self.inventory.remove(item)
                print(f"{target.name}이(가) {item.name}을 사용했다!")
                self.combo.reset()
                return

            if choice == 4:
                actor.guarding = True
                print(f"{actor.name}은 방어 태세를 취했다.")
                self.combo.reset()
                return

            if choice == 5:
                self._print_enemy_info()
                continue

            self._attempt_flee()
            self.combo.reset()
            return

    def _choose_target(self, candidates, allow_cancel=False):
        if len(candidates) == 1 and not allow_cancel:
            return candidates[0]
        for i, c in enumerate(candidates, 1):
            print(f"  {i}) {c.name} (HP {c.hp}/{c.effective_max_hp})")
        option_count = len(candidates)
        if allow_cancel:
            option_count += 1
            print(f"  {option_count}) 이전 메뉴")
        index = prompt_index("대상 선택> ", option_count)
        if allow_cancel and index == option_count - 1:
            return None
        return candidates[index]

    def _print_enemy_info(self):
        element_names = {"fire": "화", "ice": "냉", "thunder": "뇌", "wind": "풍"}
        print("\n[적 정보]")
        for enemy in [enemy for enemy in self.enemies if enemy.is_alive]:
            weakness = element_names.get(enemy.weakness, enemy.weakness or "없음")
            resistance = element_names.get(enemy.resistance, enemy.resistance or "없음")
            statuses = ", ".join(
                f"{effect.name} {effect.remaining_turns}턴" for effect in enemy.status_effects
            ) or "없음"
            print(f"- {enemy.name}: HP {enemy.hp}/{enemy.effective_max_hp}, 약점 {weakness}, 저항 {resistance}")
            print(f"  상태 효과: {statuses}")

    def _attempt_flee(self) -> bool:
        if any(enemy.job in {"미니보스", "보스", "최종보스"} for enemy in self.enemies):
            print("이 전투에서는 도망칠 수 없다!")
            return False
        party_speed = sum(member.effective_speed for member in self.party.alive_members) / len(self.party.alive_members)
        alive_enemies = [enemy for enemy in self.enemies if enemy.is_alive]
        enemy_speed = sum(enemy.effective_speed for enemy in alive_enemies) / len(alive_enemies)
        chance = max(0.25, min(0.90, 0.60 + (party_speed - enemy_speed) * 0.05))
        if random.random() < chance:
            self.fled = True
            print(f"도주에 성공했다! (성공률 {chance:.0%})")
            return True
        print(f"도주에 실패했다! (성공률 {chance:.0%})")
        return False

    # -----------------------------------------------------------------
    def _enemy_turn(self, enemy: Enemy):
        skill, target = enemy.choose_action(self.party.alive_members)
        if enemy.last_phase_message:
            print(f"\n★ {enemy.last_phase_message}")
        if target is None:
            return
        if skill is None:
            dmg = enemy.basic_attack(target)
            if target.last_damage_evaded:
                print(f"{enemy.name}의 공격! {target.name}은(는) 재빠르게 회피했다!")
            else:
                print(f"{enemy.name}의 공격! {target.name}에게 {dmg}의 피해!")
        elif skill.aoe:
            targets = [enemy] if skill.kind in ("heal", "buff") else self.party.alive_members
            try:
                results = enemy.use_skill_on_targets(skill, targets)
            except ValueError:
                return
            print(f"{enemy.name}의 [{skill.name}]!")
            for t, amount, status_applied, effectiveness in results:
                for msg in _describe_skill_result(
                    enemy.name, t.name, skill, amount, status_applied, effectiveness,
                    enemy.last_attack_was_critical, t.last_damage_evaded,
                ):
                    print(msg)
        else:
            amount, status_applied, effectiveness = enemy.use_skill(skill, target)
            for msg in _describe_skill_result(
                enemy.name, target.name, skill, amount, status_applied, effectiveness,
                enemy.last_attack_was_critical, target.last_damage_evaded,
            ):
                print(msg)

    # -----------------------------------------------------------------
    def _victory(self):
        total_exp = sum(e.exp_reward for e in self.enemies)
        total_gold = sum(e.gold_reward for e in self.enemies)
        self.party.gold += total_gold
        print(f"\n=== 전투 승리! === (경험치 +{total_exp}, 골드 +{total_gold})")
        for member in self.party.members:
            if member.is_alive:
                leveled_up = member.gain_exp(total_exp)
                if leveled_up:
                    print(f"★ {member.name}의 레벨이 올랐다! -> Lv.{member.level}")
                    for message in member.last_growth_messages:
                        print(f"  ★ {message}")

        for enemy in self.enemies:
            for item, chance in enemy.loot_pool:
                if random.random() < chance:
                    self.inventory.append(item)
                    print(f"{enemy.name}이(가) [{item.name}]을(를) 떨어뜨렸다!")
            if random.random() < enemy.equipment_drop_chance:
                from data import generate_random_equipment
                equipment = generate_random_equipment(enemy.level)
                self.equipment_inventory.append(equipment)
                print(f"{enemy.name}이(가) 장비 {equipment.display_name}을(를) 떨어뜨렸다!")
