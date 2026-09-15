"""퀘스트 정의와 수락·진행·완료·보상 처리를 담당합니다."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple

from input_utils import prompt_index, prompt_yes_no


QUEST_STATUSES = {"available", "active", "ready", "completed"}


@dataclass(frozen=True)
class QuestDefinition:
    quest_id: str
    title: str
    description: str
    target_location_id: str
    objective: str
    gold_reward: int
    item_rewards: Tuple[Tuple[str, int], ...] = ()
    main_quest: bool = False
    bonus_flag: str = ""
    bonus_gold_reward: int = 0
    completion_flag: str = ""


QUESTS: Dict[str, QuestDefinition] = {
    "ruins_darkness": QuestDefinition(
        quest_id="ruins_darkness",
        title="폐허의 어둠",
        description="숲 너머 폐허의 이상한 기운을 조사한다.",
        target_location_id="ruins",
        objective="버려진 폐허의 다크 나이트 처치",
        gold_reward=50,
        item_rewards=(("포션", 2),),
        main_quest=True,
    ),
    "miners_rest": QuestDefinition(
        quest_id="miners_rest",
        title="광부들의 안식",
        description="폐광 깊은 곳의 위협을 제거해 원혼들을 쉬게 한다.",
        target_location_id="mine_depths",
        objective="폐광 가장 깊은 곳의 탄광 드레이크 처치",
        gold_reward=45,
        item_rewards=(("에테르", 1), ("해독제", 1)),
    ),
    "lost_herbalist": QuestDefinition(
        quest_id="lost_herbalist",
        title="안개 속 약초꾼",
        description="안개 습지에서 실종된 약초꾼 세아를 찾아 안전을 확인한다.",
        target_location_id="forgotten_shrine",
        objective="잊힌 사당의 안개의 여왕을 처치하고 달빛 샘에서 세아 찾기",
        gold_reward=60,
        item_rewards=(("해독제", 2), ("에테르", 1)),
        bonus_flag="escorted_herbalist",
        bonus_gold_reward=20,
        completion_flag="found_herbalist",
    ),
    "seals_echo": QuestDefinition(
        quest_id="seals_echo",
        title="봉인의 잔향",
        description="가라앉은 기록실에서 밝혀진 봉인의 균열을 따라 메아리를 잠재운다.",
        target_location_id="echo_vault",
        objective="메아리의 석실에서 봉인의 메아리 처치",
        gold_reward=65,
        item_rewards=(("달빛 영약", 1),),
        bonus_flag="archive_reported",
        bonus_gold_reward=25,
    ),
}


class QuestLog:
    """퀘스트별 상태를 보관하고 월드 진행과 보상을 연결한다."""

    def __init__(self, states: Dict[str, str] | None = None):
        self.states = {quest_id: "available" for quest_id in QUESTS}
        for quest_id, status in (states or {}).items():
            if quest_id in QUESTS and status in QUEST_STATUSES:
                self.states[quest_id] = status

    def status(self, quest_id: str) -> str:
        return self.states[quest_id]

    def accept(self, quest_id: str) -> bool:
        if self.states.get(quest_id) != "available":
            return False
        self.states[quest_id] = "active"
        return True

    def sync_story_flags(self, flags: dict) -> None:
        """대화에서 받은 부탁과 기록실에서 찾은 단서를 의뢰에 반영한다."""
        if flags.get("promised_elder") is True:
            self.accept("ruins_darkness")
        if flags.get("archive_discovered") is True:
            self.accept("seals_echo")

    def refresh_from_world(self, game_map, flags: dict | None = None) -> None:
        """활성 퀘스트의 보스와 대화 플래그 완료 조건을 확인한다."""
        for quest_id, definition in QUESTS.items():
            if self.states[quest_id] != "active":
                continue
            location = game_map.locations.get(definition.target_location_id)
            flag_ready = (
                not definition.completion_flag
                or bool((flags or {}).get(definition.completion_flag))
            )
            if location and location.boss_defeated and flag_ready:
                self.states[quest_id] = "ready"

    def claim(
        self, quest_id: str, party, inventory: list, flags: dict | None = None,
    ) -> bool:
        """완료 가능 퀘스트의 보상을 한 번만 지급한다."""
        if self.states.get(quest_id) != "ready":
            return False

        import data  # quests.py와 data.py의 불필요한 초기 순환 참조 방지

        definition = QUESTS[quest_id]
        bonus_gold = (
            definition.bonus_gold_reward
            if definition.bonus_flag and (flags or {}).get(definition.bonus_flag)
            else 0
        )
        party.gold += definition.gold_reward + bonus_gold
        for item_name, count in definition.item_rewards:
            inventory.extend([data.ITEMS_BY_NAME[item_name]] * count)
        self.states[quest_id] = "completed"
        return True

    def render_journal(self) -> str:
        labels = {
            "available": "미수락",
            "active": "진행 중",
            "ready": "보상 수령 가능",
            "completed": "완료",
        }
        lines = ["[퀘스트 일지]"]
        for quest_id, definition in QUESTS.items():
            status = self.states[quest_id]
            category = "메인" if definition.main_quest else "사이드"
            lines.append(f"- [{category}] {definition.title} · {labels[status]}")
            lines.append(f"  목표: {definition.objective}")
        return "\n".join(lines)


def run_quest_board(
    quest_log: QuestLog, party, inventory: list, game_map, flags: dict | None = None,
) -> None:
    """마을 의뢰 게시판에서 수락과 보상 수령을 처리한다."""
    quest_log.refresh_from_world(game_map, flags)
    status_labels = {
        "available": "수락 가능",
        "active": "진행 중",
        "ready": "보상 수령 가능",
        "completed": "완료",
    }
    definitions = list(QUESTS.values())

    while True:
        print("\n[마을 의뢰 게시판]")
        for index, definition in enumerate(definitions, 1):
            print(f"  {index}) {definition.title} ({status_labels[quest_log.status(definition.quest_id)]})")
        print(f"  {len(definitions) + 1}) 돌아가기")
        choice = prompt_index("> ", len(definitions) + 1)
        if choice == len(definitions):
            return

        definition = definitions[choice]
        quest_id = definition.quest_id
        status = quest_log.status(quest_id)
        print(f"\n[{definition.title}] {definition.description}")
        print(f"목표: {definition.objective}")
        rewards = [f"골드 {definition.gold_reward}G"]
        rewards.extend(f"{name}×{count}" for name, count in definition.item_rewards)
        print("보상: " + ", ".join(rewards))

        if status == "available":
            if prompt_yes_no("이 의뢰를 수락할까요? (y/n)> "):
                quest_log.accept(quest_id)
                quest_log.refresh_from_world(game_map, flags)
                print("의뢰를 수락했습니다.")
        elif status == "ready":
            quest_log.claim(quest_id, party, inventory, flags)
            if definition.bonus_flag and (flags or {}).get(definition.bonus_flag):
                rewards.append(f"선택 보너스 {definition.bonus_gold_reward}G")
            print("의뢰를 완료했습니다! " + ", ".join(rewards))
        elif status == "active":
            print("아직 목표를 달성하지 못했습니다.")
        else:
            print("이미 완료한 의뢰입니다.")
