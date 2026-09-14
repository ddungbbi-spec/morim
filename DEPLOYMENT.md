# 배포 안내

## Render 웹 서비스

이 프로젝트는 외부 라이브러리 없이 파이썬 표준 라이브러리로 실행됩니다.

- 런타임: Python 3.12
- 빌드 명령: `python -m compileall -q .`
- 시작 명령: `python web_app.py`
- 상태 확인: `/api/health`
- 권장 지역: Singapore
- 필수 환경 변수: `HOST=0.0.0.0`, `RPG_MULTI_SESSION=1`, `PYTHONUNBUFFERED=1`
- 포트: Render가 제공하는 `PORT` 환경 변수를 자동 사용

## Docker

```bash
docker compose up --build
```

브라우저에서 `http://127.0.0.1:8000`에 접속합니다. Compose의 `game-saves` 볼륨이 저장 슬롯을 보존합니다.

## 저장 데이터

다중 세션 저장은 `saves/web/{세션 식별자}/slot{번호}.json`에 기록됩니다. 무료 Render 웹 서비스의 로컬 파일은 영구 저장이 아니므로 재시작이나 재배포 후 저장이 사라질 수 있습니다. 장기 운영 시 `/app/saves` 영구 디스크 또는 외부 데이터 저장소가 필요합니다.

브라우저 쿠키를 삭제하면 새 세션이 발급되어 이전 세션의 저장 슬롯에 접근할 수 없습니다.
