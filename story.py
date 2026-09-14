"""
story.py
대사(내레이션/대화)와 선택지로 구성된 스토리 이벤트를 처리하는 엔진입니다.
실제 스토리 내용(대사, 선택지, 분기)은 dialogues.py 에 정의합니다.

핵심 개념
- DialogueNode: 한 번에 보여줄 대사 묶음 + (선택지가 있다면) 다음 노드로 가는 분기
- Dialogue: 노드들의 모음. start_id부터 시작해서 노드를 따라가며 진행
- flags: 대화 중 선택한 결과를 기억해두는 dict. 이후 다른 장소/엔딩에서 참조 가능
         (예: flags["promised_elder"] = True)
"""

from __future__ import annotations
from typing import Callable, Dict, List, Optional, Tuple, Union
from input_utils import prompt_index

LinesType = Union[str, List[str], Callable[[dict], Union[str, List[str]]]]


class DialogueNode:
    def __init__(
        self,
        node_id: str,
        lines: LinesType,
        choices: Optional[List[Tuple[str, Optional[str]]]] = None,
        effect: Optional[Callable[[dict], None]] = None,
    ):
        """
        lines   : 출력할 대사. 문자열 / 문자열 리스트 / flags를 받아 문자열(리스트)을
                   반환하는 함수(분기 텍스트를 만들 때 사용) 모두 가능.
        choices : [(선택지 문구, 다음 노드 id), ...]. 없으면 여기서 대화가 끝남.
                  다음 노드 id로 None을 주면 그 선택지를 고른 즉시 대화 종료.
        effect  : 이 노드가 보여질 때 실행할 함수. flags를 변경할 때 사용.
                  예: effect=lambda flags: flags.update(promised_elder=True)
        """
        self.id = node_id
        self.lines = lines
        self.choices = choices or []
        self.effect = effect

    def resolve_lines(self, flags: dict) -> List[str]:
        lines = self.lines(flags) if callable(self.lines) else self.lines
        return lines if isinstance(lines, list) else [lines]


class Dialogue:
    def __init__(self, nodes: List[DialogueNode], start_id: str):
        self.nodes: Dict[str, DialogueNode] = {n.id: n for n in nodes}
        self.start_id = start_id

    def run(self, flags: dict):
        """대화를 처음부터 끝까지 진행합니다. flags는 선택 결과를 누적 저장합니다."""
        current_id: Optional[str] = self.start_id
        print()
        while current_id is not None:
            node = self.nodes[current_id]
            for line in node.resolve_lines(flags):
                print(line)
            if node.effect:
                node.effect(flags)

            if not node.choices:
                break

            for i, (label, _) in enumerate(node.choices, 1):
                print(f"  {i}) {label}")
            idx = prompt_index("> ", len(node.choices))
            _, next_id = node.choices[idx]
            current_id = next_id
