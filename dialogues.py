"""
dialogues.py
실제 스토리 대사와 선택지 분기를 정의합니다.
새로운 대화 이벤트를 추가할 때는 이 파일에 함수를 하나 만들고
world.py 에서 해당 Location의 dialogue= 인자로 연결하세요.
"""

from story import DialogueNode, Dialogue


def village_intro_dialogue() -> Dialogue:
    """마을 노인이 부탁을 하는 오프닝 대화. 선택에 따라 flags["promised_elder"]가 갈린다."""

    def promise_help(flags: dict):
        flags["promised_elder"] = True

    def refuse_help(flags: dict):
        flags["promised_elder"] = False

    end_help = DialogueNode(
        "end_help",
        [
            "레온: \"걱정 마세요. 저희가 반드시 해결하겠습니다.\"",
            "마을 노인은 안도한 표정을 지었다.",
            "노인: \"고맙네... 부디 조심하게나.\"",
        ],
        effect=promise_help,
    )

    end_refuse = DialogueNode(
        "end_refuse",
        [
            "레온: \"죄송하지만... 지금은 다른 사정이 있어서요.\"",
            "마을 노인은 실망한 기색을 감추지 못했다.",
            "노인: \"...그런가. 그래도 혹시 마음이 바뀌면 들러주게.\"",
        ],
        effect=refuse_help,
    )

    ask = DialogueNode(
        "ask",
        [
            "마을 노인: \"자네들, 여행자로군. 마침 잘 됐네.\"",
            "마을 노인: \"숲 너머 폐허에서 이상한 기운이 느껴진다네. 마을 사람들이 불안해하고 있어.\"",
            "마을 노인: \"자네들이 좀 살펴봐 줄 수 있겠나?\"",
        ],
        choices=[
            ("돕겠다고 약속한다", "end_help"),
            ("지금은 어렵다고 말한다", "end_refuse"),
        ],
    )

    return Dialogue(nodes=[ask, end_help, end_refuse], start_id="ask")


def shadow_valley_dialogue() -> Dialogue:
    """그림자 골짜기 진입 시의 짧은 분위기 연출용 대화 (선택지 없음)."""
    node = DialogueNode(
        "shadow_valley",
        [
            "숲이 끝나고 황량한 골짜기가 나타난다. 하늘마저 어두워 보인다.",
            "레온: \"...분위기가 심상치 않아. 다들 정신 바짝 차려.\"",
            "저 멀리, 폐허의 그림자가 어렴풋이 보인다.",
        ],
    )
    return Dialogue(nodes=[node], start_id="shadow_valley")


def ruins_approach_dialogue() -> Dialogue:
    """폐허 입구에서의 짧은 분위기 연출용 대화 (선택지 없음)."""
    node = DialogueNode(
        "ruins_approach",
        [
            "무너진 돌기둥 사이로 서늘한 바람이 불어온다.",
            "리제: \"...느껴져? 이 안에 뭔가 있어.\"",
            "레온: \"조심해서 들어가자.\"",
        ],
    )
    return Dialogue(nodes=[node], start_id="ruins_approach")


def tower_summit_dialogue() -> Dialogue:
    """도전의 탑 정상에서의 짧은 분위기 연출용 대화 (선택지 없음)."""
    node = DialogueNode(
        "tower_summit",
        [
            "탑의 가장 높은 곳. 거대한 그림자가 앞을 가로막는다.",
            "셀린: \"...여기까지 올라온 자는 몇 없다고 했는데.\"",
            "레온: \"돌아갈 곳은 없다. 가자.\"",
        ],
    )
    return Dialogue(nodes=[node], start_id="tower_summit")


def mine_depths_dialogue() -> Dialogue:
    """폐광 가장 깊은 곳에서의 짧은 분위기 연출용 대화 (선택지 없음)."""
    node = DialogueNode(
        "mine_depths",
        [
            "갱도 끝에서 뜨거운 열기가 느껴진다.",
            "리제: \"이 안쪽에... 뭔가 커다란 게 있어.\"",
            "셀린: \"다들 조심해.\"",
        ],
    )
    return Dialogue(nodes=[node], start_id="mine_depths")


def seal_gate_dialogue() -> Dialogue:
    """다크 나이트를 처치한 뒤 발견하는 진실. 선택에 따라 flags["embraced_power"]가 갈린다."""

    def embrace_power(flags: dict):
        flags["embraced_power"] = True

    def reject_power(flags: dict):
        flags["embraced_power"] = False

    end_embrace = DialogueNode(
        "end_embrace",
        [
            "레온: \"...이 힘, 거절할 이유가 없다.\"",
            "봉인의 문에서 흘러나온 기운이 파티를 스치고 지나간다.",
            "리제: \"돌이킬 수 없을지도 몰라. 그래도... 가자.\"",
        ],
        effect=embrace_power,
    )
    end_reject = DialogueNode(
        "end_reject",
        [
            "셀린: \"안 돼. 이런 힘에 손대면 안 돼.\"",
            "레온: \"...그래. 우리 힘만으로 끝내자.\"",
            "파티는 흘러나오는 기운을 애써 외면하고 안으로 향했다.",
        ],
        effect=reject_power,
    )
    reveal = DialogueNode(
        "reveal",
        [
            "다크 나이트가 쓰러진 자리, 바닥 아래로 이어지는 봉인의 문이 드러난다.",
            "문 틈새로 흘러나오는 기운이 심상치 않다. 다크 나이트는 이것을 지키고 있었던 것이다.",
            "셀린: \"...이 안에, 훨씬 위험한 무언가가 있어.\"",
        ],
        choices=[
            ("흘러나오는 힘을 받아들인다", "end_embrace"),
            ("위험하니 거부한다", "end_reject"),
        ],
    )
    return Dialogue(nodes=[reveal, end_embrace, end_reject], start_id="reveal")


def final_confrontation_dialogue() -> Dialogue:
    """진짜 최종 보스를 마주하기 직전의 분위기 연출용 대화 (선택지 없음)."""
    node = DialogueNode(
        "final_confrontation",
        [
            "봉인의 문 너머, 오랫동안 잠들어 있던 존재가 서서히 일어난다.",
            "봉인된 마왕: \"...누가 나의 잠을 깨우는가.\"",
            "레온: \"여기서 끝내자!\"",
        ],
    )
    return Dialogue(nodes=[node], start_id="final_confrontation")


def ending_dialogue() -> Dialogue:
    """
    엔딩 지점. 두 가지 선택의 결과로 대사가 갈린다.
    - flags["promised_elder"]: 마을 노인과의 약속을 지켰는가
    - flags["embraced_power"]: 봉인의 힘을 받아들였는가
    """

    def text_fn(flags: dict) -> list:
        promised = flags.get("promised_elder")
        embraced = flags.get("embraced_power")

        if promised and not embraced:
            return [
                "빛 속에서 마을 노인의 말이 떠오른다.",
                "\"자네들 덕분에 마을이 평화를 되찾았네. 고맙네.\"",
                "파티는 약속을 지켰다는 뿌듯함을 안고, 스스로의 힘만으로 빛 속으로 걸어 들어갔다.",
            ]
        elif promised and embraced:
            return [
                "마을은 구했지만, 파티의 몸속에는 낯선 힘이 여전히 꿈틀거리고 있다.",
                "셀린: \"...이걸로 정말 괜찮은 걸까.\"",
                "레온: \"그건, 앞으로 알아가야겠지.\"",
            ]
        elif not promised and embraced:
            return [
                "누구와의 약속도 없었지만, 파티는 스스로 위험 속으로 걸어 들어갔었다.",
                "그리고 지금, 손에 넣은 낯선 힘이 온몸을 타고 흐른다.",
                "레온: \"...이제부터가 진짜 시작일지도 모르겠군.\"",
            ]
        else:
            return [
                "빛 속에서 파티는 조용히 생각에 잠긴다.",
                "약속하지 않았던 일이었지만, 스스로 나서서 위험을 해결했다.",
                "그것으로 충분했다... 라고 레온은 생각했다.",
            ]

    node = DialogueNode("end", text_fn)
    return Dialogue(nodes=[node], start_id="end")
