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

다중 세션 저장은 `saves/web/{세션 식별자}/slot{번호}.json`에 기록됩니다. 웹판은 저장할 때 같은 데이터를 브라우저 `localStorage`에도 백업하고, 재시작이나 재배포 뒤 서버 슬롯이 비어 있으면 자동 복원합니다. 따라서 같은 브라우저에서는 무료 Render 인스턴스가 초기화되어도 저장 슬롯을 이어갈 수 있습니다.

브라우저 사이트 데이터를 삭제하거나 다른 기기로 옮기면 브라우저 백업도 사라집니다. 여러 기기 공유나 장기 운영에는 `/app/saves` 영구 디스크 또는 외부 데이터 저장소가 필요합니다.
