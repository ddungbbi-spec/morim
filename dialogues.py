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


def star_observatory_dialogue() -> Dialogue:
    """후일담의 첫 갈림길. 기록 공개 선택과 별도로 장로에게 알릴 수 있다."""
    def report(flags):
        flags["star_signal_found"] = True
        flags["star_signal_reported"] = True

    def investigate(flags):
        flags["star_signal_found"] = True
        flags["star_signal_reported"] = False

    return Dialogue(nodes=[
        DialogueNode("signal", [
            "관측 장치의 바늘이 밤하늘의 검은 별을 따라 흔들린다.",
            "셀린: \"마왕을 쓰러뜨렸는데도 봉인의 파편이 하늘에서 떨어지고 있어.\"",
            "리제: \"낙하지를 살펴봐야 해. 장로에게 먼저 알릴까?\"",
        ], choices=[("장로에게 신호를 알리고 함께 대비한다", "report"),
                    ("소동을 피하려 먼저 직접 조사한다", "investigate")]),
        DialogueNode("report", ["장로는 마을의 등불을 밝히고 파티에게 낙하지 조사를 부탁한다."], effect=report),
        DialogueNode("investigate", ["파티는 밤이 깊기 전에 조용히 낙하지로 향한다."], effect=investigate),
    ], start_id="signal")


def fallen_star_dialogue() -> Dialogue:
    return Dialogue(nodes=[DialogueNode("fall", [
        "검은 유성은 돌이 아니라 봉인의 잔해였다.",
        "레온: \"끝난 줄 알았던 이야기가 여기까지 이어졌군. 균열을 닫자.\"",
    ])], start_id="fall")


def star_rift_dialogue() -> Dialogue:
    return Dialogue(nodes=[DialogueNode("rift", lambda flags: [
        "별의 균열에서 마왕의 그림자가 아니라 봉인을 지탱하던 잔재가 깨어난다.",
        ("셀린: \"장로가 마을을 지키는 동안 우리가 균열을 막아야 해.\""
         if flags.get("star_signal_reported") else
         "셀린: \"마을에 닿기 전에 우리가 먼저 균열을 막아야 해.\""),
    ])], start_id="rift")


def astral_passage_dialogue() -> Dialogue:
    """검은 별의 발신지를 발견하고 귀환 표식을 남길지 선택한다."""
    def light_beacon(flags: dict):
        flags["astral_route_found"] = True
        flags["astral_beacon_lit"] = True

    def press_forward(flags: dict):
        flags["astral_route_found"] = True
        flags["astral_beacon_lit"] = False

    return Dialogue(nodes=[
        DialogueNode("arrival", [
            "닫힌 균열 너머에서 한 줄기 별빛 길이 다시 열린다.",
            "리제: \"검은 별은 우연히 떨어진 게 아니야. 누군가 이 길 건너에서 보냈어.\"",
            "셀린: \"마을로 돌아갈 표식을 남길까? 적이 눈치챌 수도 있어.\"",
        ], choices=[
            ("별빛 봉화를 밝혀 귀환로를 확보한다", "beacon"),
            ("발각되기 전에 봉화 없이 전진한다", "advance"),
        ]),
        DialogueNode("beacon", [
            "성운석 조각이 푸른 봉화로 타오르며 마을과 별길을 잇는다.",
            "레온: \"돌아갈 길을 지켰다. 이제 근원을 끊으러 가자.\"",
        ], effect=light_beacon),
        DialogueNode("advance", [
            "파티는 흔적을 남기지 않고 무너진 별길 안쪽으로 발걸음을 재촉한다.",
            "레온: \"한 번에 끝낸다. 돌아갈 길은 우리가 만들면 돼.\"",
        ], effect=press_forward),
    ], start_id="arrival")


def shattered_sanctum_dialogue() -> Dialogue:
    return Dialogue(nodes=[DialogueNode("sanctum", [
        "부서진 천문판마다 마을과 봉인의 방이 같은 별자리 위에 새겨져 있다.",
        "리제: \"공허의 관측자가 마왕의 봉인을 실험하고 있었어. 검은 별은 다음 관측 신호였고.\"",
        "셀린: \"왕좌에서 이 통로를 닫지 않으면 다른 균열이 계속 열릴 거야.\"",
    ])], start_id="sanctum")


def void_throne_dialogue() -> Dialogue:
    return Dialogue(nodes=[DialogueNode("throne", lambda flags: [
        "별이 없는 왕좌에서 거대한 눈동자가 파티를 내려다본다.",
        "공허의 관측자: \"봉인을 부순 세계의 생존 가능성을 직접 확인하겠다.\"",
        ("레온: \"봉화가 우리 세계를 비추고 있다. 이 문은 여기서 닫는다!\""
         if flags.get("astral_beacon_lit") else
         "레온: \"퇴로는 없다. 네가 만든 문과 함께 여기서 끝낸다!\""),
    ])], start_id="throne")


def moonlit_spring_dialogue() -> Dialogue:
    """달빛 샘에서 약초꾼 세아를 발견하고 호위 여부를 정한다."""

    def escort_herbalist(flags: dict):
        flags["found_herbalist"] = True
        flags["escorted_herbalist"] = True

    def let_her_rest(flags: dict):
        flags["found_herbalist"] = True
        flags["escorted_herbalist"] = False

    escort = DialogueNode(
        "escort",
        [
            "세아: \"정말 고마워요. 여러분과 함께라면 마을까지 갈 수 있겠어요.\"",
            "세아가 약초 바구니를 챙겨 파티에 합류했다.",
            "마을 의뢰인은 안전한 호위에 보답할 것이다.",
        ],
        effect=escort_herbalist,
    )
    rest = DialogueNode(
        "rest",
        [
            "세아: \"조금만 더 쉬면 혼자 돌아갈 수 있어요. 먼저 가세요.\"",
            "파티는 세아에게 귀환 길을 알려주고 샘을 떠날 준비를 했다.",
        ],
        effect=let_her_rest,
    )
    found = DialogueNode(
        "found",
        [
            "달빛 샘가에서 젖은 망토를 두른 약초꾼이 손을 흔든다.",
            "약초꾼 세아: \"안개의 여왕 때문에 꼼짝없이 갇혀 있었어요. 구해주셔서 감사합니다.\"",
            "세아는 지친 기색이지만 크게 다친 곳은 없어 보인다.",
        ],
        choices=[
            ("세아를 마을까지 호위한다", "escort"),
            ("샘에서 쉬었다가 돌아오게 한다", "rest"),
        ],
    )
    return Dialogue(nodes=[found, escort, rest], start_id="found")


def drowned_archive_dialogue() -> Dialogue:
    """세아가 발견한 기록실에서 봉인의 진실을 읽고 공개 여부를 정한다."""

    def discover(flags: dict):
        flags["archive_discovered"] = True

    def share_records(flags: dict):
        flags["archive_reported"] = True

    def keep_records(flags: dict):
        flags["archive_reported"] = False

    read = DialogueNode(
        "read",
        [
            "세아가 알려준 수로 끝에서 물에 잠긴 기록실이 나타난다.",
            "리제: \"이 문양은 폐허의 봉인의 문과 같아. 안개도 봉인의 균열에서 새어 나왔던 거야.\"",
            "낡은 기록에는 균열의 메아리가 아래층에 남아 있다고 적혀 있다.",
            "셀린: \"마을에 진실을 알릴까, 아니면 먼저 우리가 책임지고 처리할까?\"",
        ],
        choices=[
            ("기록을 장로에게 전하기로 한다", "share"),
            ("혼란을 막기 위해 기록을 간직한다", "keep"),
        ],
        effect=discover,
    )
    share = DialogueNode(
        "share",
        [
            "레온: \"장로가 알아야 마을도 대비할 수 있어. 메아리를 잠재운 뒤 함께 돌아가자.\"",
            "파티는 읽을 수 있는 기록을 조심스럽게 챙겼다.",
        ],
        effect=share_records,
    )
    keep = DialogueNode(
        "keep",
        [
            "레온: \"지금 알리면 사람들이 겁부터 먹을 거야. 우선 메아리를 잠재우자.\"",
            "파티는 기록의 위치만 기억한 채 아래층으로 향했다.",
        ],
        effect=keep_records,
    )
    return Dialogue(nodes=[read, share, keep], start_id="read")


def echo_vault_dialogue() -> Dialogue:
    node = DialogueNode(
        "echo",
        [
            "기록실 아래의 빈 석실에서 마왕의 목소리가 메아리처럼 울린다.",
            "셀린: \"본체가 아니야. 봉인의 틈에 남은 기억이 안개를 움직인 거야.\"",
            "레온: \"이 잔향을 멈춰야 샘도 마을도 안전해져.\"",
        ],
    )
    return Dialogue(nodes=[node], start_id="echo")


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
            lines = [
                "빛 속에서 마을 노인의 말이 떠오른다.",
                "\"자네들 덕분에 마을이 평화를 되찾았네. 고맙네.\"",
                "파티는 약속을 지켰다는 뿌듯함을 안고, 스스로의 힘만으로 빛 속으로 걸어 들어갔다.",
            ]
        elif promised and embraced:
            lines = [
                "마을은 구했지만, 파티의 몸속에는 낯선 힘이 여전히 꿈틀거리고 있다.",
                "셀린: \"...이걸로 정말 괜찮은 걸까.\"",
                "레온: \"그건, 앞으로 알아가야겠지.\"",
            ]
        elif not promised and embraced:
            lines = [
                "누구와의 약속도 없었지만, 파티는 스스로 위험 속으로 걸어 들어갔었다.",
                "그리고 지금, 손에 넣은 낯선 힘이 온몸을 타고 흐른다.",
                "레온: \"...이제부터가 진짜 시작일지도 모르겠군.\"",
            ]
        else:
            lines = [
                "빛 속에서 파티는 조용히 생각에 잠긴다.",
                "약속하지 않았던 일이었지만, 스스로 나서서 위험을 해결했다.",
                "그것으로 충분했다... 라고 레온은 생각했다.",
            ]

        if flags.get("echo_purified"):
            if flags.get("archive_reported"):
                lines.append("장로에게 전하기로 한 기록은 마을이 봉인의 균열에 대비할 단서가 될 것이다.")
            else:
                lines.append("가라앉은 기록실의 진실은 파티만 간직했지만, 봉인의 잔향은 잠잠해졌다.")
        return lines

    node = DialogueNode("end", text_fn)
    return Dialogue(nodes=[node], start_id="end")
