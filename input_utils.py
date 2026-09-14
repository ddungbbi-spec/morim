"""콘솔 메뉴에서 사용하는 공통 입력 검증 함수."""


def prompt_index(prompt: str, option_count: int) -> int:
    """1부터 option_count까지 입력받아 0 기반 인덱스로 반환합니다."""
    if option_count < 1:
        raise ValueError("선택지는 하나 이상이어야 합니다.")

    while True:
        raw = input(prompt).strip()
        try:
            number = int(raw)
        except ValueError:
            print("숫자로 입력해 주세요.")
            continue
        if 1 <= number <= option_count:
            return number - 1
        print(f"1부터 {option_count} 사이의 번호를 입력해 주세요.")


def prompt_yes_no(prompt: str) -> bool:
    """예/아니오를 안전하게 입력받습니다."""
    while True:
        answer = input(prompt).strip().lower()
        if answer in {"y", "yes", "예", "네"}:
            return True
        if answer in {"n", "no", "아니요", "아니오"}:
            return False
        print("예(y) 또는 아니요(n)로 입력해 주세요.")
