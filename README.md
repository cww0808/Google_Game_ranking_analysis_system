# Google Play 게임 데이터 수집기

한국 Google Play 게임 공개 페이지에서 게임 패키지 목록을 찾고, 상세 데이터를 수집해 SQLite 일별 스냅샷과 Markdown 보고서로 저장합니다. OpenAI API나 `llama.cpp`는 필요하지 않습니다.

## 수집 항목

- 순위, 게임명, 패키지명, 장르
- 평점, 평가 수, 리뷰 수
- 설치 수 표기 및 수치
- 업데이트 날짜, 아이콘, 개발사
- 인앱 결제 여부, 가격

## 설치

Python 3.11 이상을 설치한 뒤:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

## 실행

```powershell
googleplay-games
```

결과:

- `data/google_play_games.db`
- `reports/YYYY-MM-DD.md`

옵션 예시:

```powershell
googleplay-games --limit 20 --delay 0.5
googleplay-games --package-file ranking.csv
```

`ranking.csv`는 `app_id` 열을 가져야 합니다. 별도 순위 제공자를 붙이거나 수동 검증한 목록을 사용할 때 유용합니다.

## 중요한 데이터 해석 주의사항

Google Play Developer API는 공개 인기 차트를 제공하지 않습니다. 기본 발견기는 공개 `GAME` 페이지에 노출된 앱 링크 순서를 사용하므로 Google이 화면 구성이나 개인화를 변경하면 정확한 “무료 인기 Top 100”과 차이가 날 수 있습니다. 코드에서 이 부분은 `discover_game_ids()` 하나로 격리되어 있어 향후 더 정확한 차트 공급자나 API로 교체할 수 있습니다.

또한 Google Play의 `reviews`는 작성 리뷰 수이고 `ratings`는 별점 평가 수입니다. 보고서에서는 둘을 구분해 저장합니다.

## 작성 리뷰와 사용자 관계 수집

Google Play는 공개 리뷰 응답에 공식 Google 계정 사용자 ID를 제공하지 않습니다. 따라서 닉네임은 식별자로 사용하지 않고, 공개 프로필 이미지 URL에 포함된 토큰을 SHA-256으로 해시한 `reviewer_key`를 사용합니다.

- 리뷰 기본키: Google의 `reviewId`
- 게임 기본키: 변경되지 않는 패키지명 `app_id`
- 게임 표시·분석 기준: `game_title`
- 사용자 관계키: `reviewer_key`

동일 닉네임이어도 프로필 토큰이 다르면 다른 사용자로 저장됩니다. 같은 공개 프로필 토큰이 여러 게임에서 발견되면 같은 사용자 관계로 연결됩니다. 단, Google은 이를 공식 사용자 ID로 보장하지 않으므로 프로필 이미지 변경 시 동일인 연결이 끊길 수 있습니다.

현재 Top 100에서 게임별 최신 리뷰 200개를 수집하는 예:

```powershell
node scripts/collect_reviews.mjs `
  --ranking data/ranking_2026-06-25.csv `
  --output data/reviews_2026-06-25.jsonl `
  --reviews-per-game 200

.\.venv\Scripts\python.exe scripts/import_reviews.py data/reviews_2026-06-25.jsonl
```

별점 평가 수에는 글을 작성하지 않은 사용자도 포함되므로, 모든 평가자의 사용자 정보를 가져오는 것은 불가능합니다. 수집 가능한 범위는 Google Play가 공개하는 작성 리뷰입니다.

## 테스트

```powershell
pytest
```

## 자동 실행

`.github/workflows/daily-collect.yml`은 2026년 6월 26일부터 30일까지 한국 시간 오전 6시와 오후 6시에 실행됩니다.

각 실행은 다음 파일을 저장소에 커밋합니다.

- `data/ranking_YYYY-MM-DD_HHMM.csv`
- `data/google_play_games.db`
- `reports/YYYY-MM-DD_HHMM.md`
- `reports/구글플레이_게임리뷰_사용자관계_YYYY-MM-DD_HHMM.xlsx`

100위 밖으로 밀린 게임도 기존 SQLite 리뷰·사용자 관계 데이터에는 남습니다. 현재 순위 목록에서만 빠집니다.

GitHub 호스팅 러너는 개인 PC의 로컬 폴더에 직접 파일을 쓸 수 없습니다. 로컬 `reports` 폴더는 저장소를 pull하여 동기화합니다. Windows 자동 동기화 작업 설치:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install_local_sync_task.ps1
```

작업은 오전 6시 30분과 오후 6시 30분에 `git pull --ff-only`를 실행합니다.
