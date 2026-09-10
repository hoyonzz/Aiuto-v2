# Aiuto

자연어로 입력한 일정과 할 일을 LLM이 분류하고, Celery 워커가 비동기로
처리해 저장하는 백엔드 API.

"내일 3시 팀 회의" 같은 문장을 받아 의도(일정·할 일·메모·조사)를 판별하고,
해당하는 테이블에 구조화해 저장한다. LLM 호출은 요청/응답 사이클 밖에서
처리하며, 클라이언트는 202 응답으로 받은 작업 ID로 상태를 조회한다.

**현재 구현 범위**: 인증 · LLM 추상화(구조화 출력·폴백 체인) ·
비동기 분류 파이프라인(`/ai/ingest` → 폴링)
**다음 단계**: 저장된 레코드 조회 API

---

## 기술 스택

| 역할 | 기술 | 선택 이유 |
|---|---|---|
| 웹 프레임워크 | FastAPI (async) | async 네이티브, 자동 OpenAPI 문서화 |
| 비동기 작업 | Celery + Redis | LLM 호출을 요청/응답 사이클에서 분리 |
| ORM / 마이그레이션 | SQLAlchemy 2.0 + Alembic | 비동기 세션 지원, 명시적 2.0 스타일 매핑 |
| DB | PostgreSQL | 멀티유저 환경에 필요한 서버형 DB, 동시 접속과 제약 조건 관리 |
| 인증 | PyJWT + argon2 | stateless API 인증, argon2는 현행 비밀번호 해싱 권장 표준 |
| LLM | Gemini 3.5 Flash-Lite (`google-genai`) | 분류·추출 작업에 부합하는 경량 모델, 구조화 출력 네이티브 지원 |
| PK 전략 | UUID | 순차 정수 PK의 열거(enumeration) 공격 노출 방지 |
| 설정 관리 | pydantic-settings | 환경변수를 타입 검증된 객체로 로드 |
| 로컬 인프라 | Docker Compose | PostgreSQL · Redis · Celery 워커를 함께 기동 |

---

## 아키텍처 결정

### 요청 접수와 처리를 분리

자연어 분류는 LLM 호출이 필요해 응답까지 수 초가 걸린다. 이를 요청/응답
사이클 안에서 처리하면 그동안 워커 스레드가 묶이고, 클라이언트 연결이
끊기면 작업도 함께 사라진다. 재시도할 방법도 없다.

그래서 접수와 처리를 나눴다. `/ai/ingest`는 작업 레코드만 만들고 202와
작업 ID를 즉시 반환하며, 실제 분류는 Celery 워커가 큐에서 가져가 처리한다.
클라이언트는 받은 ID로 상태를 조회한다.

FastAPI의 `BackgroundTasks`로도 응답을 먼저 보낼 수 있지만, 그 경우 작업이
API 프로세스 안에서 실행된다. 프로세스가 재시작되면 진행 중이던 작업이
사라지고, 실패한 작업을 다시 시도할 방법도 없다. 별도 프로세스와 큐가
필요한 이유다.

### 작업 상태를 자체 테이블로 관리

Celery는 결과 백엔드로 작업 상태를 조회할 수 있지만, 폴링 API의 근거로는
쓰지 않고 `ai_jobs` 테이블을 단일 기준으로 뒀다.

이유는 세 가지다. 결과 백엔드는 존재하지 않는 작업 ID를 조회해도 `PENDING`을
반환해 "그런 작업 없음"과 "처리 중"을 구분할 수 없다. 결과에 만료 시간이 있어
완료된 작업이 시간이 지나면 다시 미확인 상태로 보인다. 그리고 작업 ID만 알면
조회되므로 소유자를 확인할 수 없다.

`ai_jobs`에는 `user_id`가 있어 조회 시 소유자를 함께 확인하고, 상태 전이
(`PENDING → PROCESSING → SUCCESS/FAILED`)와 실패 사유를 워커가 직접 기록한다.

### 중복 실행을 원자적 선점으로 방어

`task_acks_late=True`를 켜뒀기 때문에 워커가 중단되면 태스크가 재배달된다.
작업이 유실되는 것보다 중복 실행되는 편이 낫다는 판단인데, 대신 같은 작업이
두 번 실행돼도 레코드가 중복 생성되지 않아야 한다.

그래서 작업을 집는 동작을
`UPDATE ai_jobs SET status = 'PROCESSING' WHERE id = ? AND status = 'PENDING'
RETURNING raw_text`로 처리한다. 조건 검사와 상태 변경이 한 문장 안에서
일어나므로 두 프로세스가 동시에 실행해도 한쪽만 선점한다.

LLM 호출은 이 트랜잭션 밖에서 수행한다. 응답까지 수 초가 걸리는 작업을
트랜잭션 안에 두면 그동안 다른 프로세스가 커밋 전 상태를 보게 되기 때문이다.
결과적으로 태스크 하나가 선점 · LLM 호출 · 결과 기록 세 구간으로 나뉘고,
트랜잭션은 첫 번째와 세 번째에만 존재한다.

### API/워커 드라이버 이원화

FastAPI와 Celery 워커가 같은 PostgreSQL을 쓰지만 접근 경로를 분리했다.
API는 `asyncpg` 드라이버로 비동기 접속하고, 워커와 마이그레이션 도구는
`psycopg` 동기 드라이버로 접속한다.

워커는 API와 메모리를 공유하지 않는 별개의 프로세스이고, Celery는 동기
실행 모델이다. 여기에 비동기 세션을 끌어오면 이벤트 루프를 별도로 관리해야
해서 얻는 것보다 복잡도가 커진다. 세션 팩토리 이름도 다르게 두어
(`SyncSessionLocal`) import 한 줄로 비동기 세션이 워커에 섞여 들어가는 것을
막았다.

### PK를 UUID로 설계

멀티유저 환경에서 순차 정수 PK(`/tasks/1`, `/tasks/2`)는 다른 사용자의
레코드를 추측·열거하기 쉽다. 모든 테이블의 PK를 UUID로 설계해 이 문제를
원천 차단했다.

### 조회 실패를 한 가지 응답으로 통일

작업 상태 조회는 `WHERE id = ? AND user_id = ?`로 한 번에 조회한다. 해당
ID가 없는 경우와 다른 사용자의 작업인 경우가 쿼리 단계에서 같은 결과가
되므로, 응답도 동일한 404가 된다.

권한 없음을 403으로 돌려주면 "그 ID는 존재한다"는 사실이 노출된다. UUID를
PK로 쓴 이유가 식별자 추측을 막는 것인데, 응답 코드로 존재 여부를 알려주면
그 방어가 무의미해진다. 응답을 나중에 맞추는 대신 조회 단계에서 구분이
불가능하게 만들었다.

### JWT 설계 — UUID 기반 subject, type 클레임 분리

JWT의 `sub`에는 사용자 이메일이 아니라 UUID를 담는다. 이메일은 변경
가능하고 개인정보이므로 토큰에 실을 이유가 없다. 또한 `type` 클레임을
고정값(`access`)으로 명시해, 이후 토큰 종류가 늘어나도(예: refresh) 서로
다른 용도의 토큰이 잘못된 자리에 쓰이는 것을 코드 레벨에서 차단할 수 있게
설계했다.

### LLM 프로바이더 추상화 — Protocol + 팩토리 + 폴백 체인

LLM 호출을 `LLMClient` Protocol로 추상화하고, 구현체를 팩토리가 선택하도록
설계했다. 프로바이더 구성은 `LLM_CHAIN` 환경변수로 하며, 항목이 둘 이상이면
`FallbackLLMClient`로 감싼다. 이 래퍼 자체도 같은 Protocol을 만족하기 때문에
호출부는 단일 클라이언트인지 체인인지 알 필요가 없다. 상속이 아니라 조합으로
기능을 확장한 구조다.

### 오류를 일시적/영구적으로 나누고, 폴백은 전자에만 적용

429·5xx·타임아웃·네트워크 오류·응답 파싱 실패는 다음 프로바이더로 넘기고,
400·401·콘텐츠 필터 차단은 폴백 없이 즉시 실패시킨다. 후자는 설정 오류나
코드 버그이므로, 폴백이 이를 "모든 프로바이더 실패"로 위장하면 진짜 원인을
찾기 어려워지기 때문이다.

같은 이유로 네트워크 예외도 선별해서 잡는다. 연결 실패·타임아웃·프록시
오류는 일시적 오류로 분류하지만, 잘못된 URL 스킴처럼 설정 실수에서 비롯되는
예외는 의도적으로 잡지 않고 그대로 드러나게 둔다.

### 정상 종료 화이트리스트로 재시도 가능 여부를 판정

응답의 `finish_reason`을 볼 때, 차단 사유(SAFETY, PROHIBITED_CONTENT 등)를
나열해 걸러내는 대신 **정상 종료(Gemini 기준 STOP, MAX_TOKENS)일 때만 재시도
가능**으로 보고 나머지는 전부 영구 실패로 처리한다. 차단 사유는 프로바이더마다
표현이 다르고 새 사유가 언제든 추가되므로, 실패 목록을 나열하는 방식은
필연적으로 빠지는 케이스가 생긴다.

### 시각 처리 — LLM은 자연어 해석, 산술은 코드

초기에는 모델에게 현재 UTC 시각을 주고 "KST를 UTC로 변환해 넣으라"고
지시했다. 그 결과 모델의 계산 과정이 출력 필드로 새어 들어가는 문제가
발생했고, 재현이 일정하지 않아 더 위험했다. 시각 계산이 필요한 `schedule`
의도에서만 발생한 것이 단서였다.

현재는 역할을 나눈다. 파이썬이 "오늘/내일/모레" 날짜를 미리 계산해 프롬프트에
표로 주입하고, 모델은 시간대 변환 없이 로컬 시각만 출력한다. UTC 변환은
`ZoneInfo`를 써서 파이썬이 처리한다.

할 일의 마감(`due_date`)은 시각 없이 날짜만 다루는 `DATE` 타입으로 뒀다.
"금요일까지"에 시각을 붙이려면 모델이 몇 시인지 지어내야 하고, 시각이 명확한
입력은 애초에 `schedule`로 분류되는 것이 도메인 정의에 맞기 때문이다.

비동기 파이프라인을 붙인 뒤에는 같은 시각이 두 번 변환되는 문제가 있었다.
LLM 클라이언트가 UTC로 변환한 값을 워커가 다시 변환한 것이다. 변환 자체가
틀린 게 아니라 누가 변환을 책임지는지 정해두지 않은 것이 원인이었다.
지금은 계층 간 계약을 명시하고 있다. LLM 클라이언트는 항상 UTC로 변환한
시각을 반환하고, 워커는 시간대 변환을 하지 않는다. 프로바이더가 늘어나도
지켜야 할 기준이라 코드가 아니라 규칙 문서에 남겼다.

### 프로바이더 평가 결과 — 현재는 단일 프로바이더 운영

폴백 체인의 두 번째 프로바이더로 NVIDIA NIM을 구현하고 체인까지
동작시켰다. 그러나 대상 모델에서 구조화 출력 옵션이 실제로 출력 구조를
강제하지 못하고 한국어 출력도 손상되는 것을 확인했다. 스키마의 `$ref`가
원인인지 확인하기 위해 완전히 평탄화한 스키마로도 테스트했으나 동일하게
실패해, 모델 자체의 문제로 판단했다.

구현체와 폴백 구조는 지우지 않고 `LLM_CHAIN`에서만 제외했다. 조건을
만족하는 프로바이더가 확보되면 환경변수만 수정하면 되고, 이번에 빼는
방향으로도 추상화가 성립하는 것을 확인했다.

---

## 프로젝트 구조

```
app/
├── api/
│   ├── deps.py           get_current_user, get_db
│   └── v1/endpoints/     인증 · ingest · 폴링 엔드포인트
├── core/                 설정, DB 엔진(async/sync), 보안
├── enums.py              TaskStatus · Intent · AiJobStatus
├── models/               User · AiJob · Task · Schedule · Memo
├── schemas/              요청·응답 Pydantic 모델
├── services/             ai_job_service — 작업 레코드 생성과 큐 전달
├── worker/
│   ├── celery_app.py     Celery 앱 인스턴스
│   ├── tasks.py          분류 태스크 (동기 세션 사용)
│   └── llm/
│       ├── base.py       LLMClient Protocol, 결과 스키마, 예외 계층
│       ├── gemini.py     Gemini 구현체
│       ├── nvidia.py     NVIDIA NIM 구현체 (현재 체인에서 제외)
│       ├── fallback.py   여러 클라이언트를 순회하는 래퍼
│       ├── factory.py    LLM_CHAIN을 읽어 클라이언트 조립
│       └── time_utils.py 날짜 앵커 생성, UTC 변환
└── main.py

alembic/                  마이그레이션
scripts/                  단계별 검증 스크립트
docker-compose.yml        PostgreSQL · Redis · Celery 워커
Dockerfile                워커 이미지 (API 컨테이너 추가 시 재사용)
```

`worker/llm/` 아래 여섯 개 파일이 Protocol(`base.py`) → 구현체(`gemini.py`,
`nvidia.py`) → 래퍼(`fallback.py`) → 조립(`factory.py`)로 나뉜다. 호출부는
`factory.get_llm_client()`가 반환한 객체만 알면 되고, 그것이 단일
클라이언트인지 폴백 체인인지는 알 필요가 없다.

---

## 로컬 실행

Python 3.12 이상, Docker Desktop이 필요하다.

### 1. 저장소와 환경변수

```bash
git clone https://github.com/hoyonzz/Aiuto-v2.git
cd Aiuto-v2
cp .env.example .env
```

`.env`에서 아래 값을 채운다. 나머지는 기본값으로 동작한다.

| 키 | 비고 |
|---|---|
| `SECRET_KEY` | `openssl rand -hex 32`로 생성 |
| `POSTGRES_USER` `POSTGRES_PASSWORD` `POSTGRES_DB` | 로컬 컨테이너에서만 쓰므로 임의로 지정 |
| `POSTGRES_HOST` `REDIS_HOST` | `localhost` 유지 (아래 실행 구조 참조) |
| `GEMINI_API_KEY` | Gemini API 키 발급 필요 |

`NVIDIA_API_KEY`는 현재 폴백 체인에서 제외돼 있어 비워둬도 된다.

### 2. 인프라 기동

```bash
docker compose up -d
```

PostgreSQL, Redis, **Celery 워커**가 함께 기동된다. 다음 단계로 넘어가기
전에 `docker compose ps`로 postgres가 `healthy`인지 확인한다.

### 3. 애플리케이션 실행

    python -m venv .venv

    # Windows (PowerShell)
    .venv\Scripts\Activate.ps1

    # macOS / Linux
    source .venv/bin/activate

    pip install -r requirements.txt
    alembic upgrade head
    uvicorn app.main:app --reload

확인: `http://localhost:8000/docs`

### 실행 구조

API는 로컬에서, Celery 워커는 컨테이너에서 실행된다. `.env`의
`POSTGRES_HOST` · `REDIS_HOST`가 `localhost`인 것은 로컬 API 기준이고,
워커 컨테이너는 Compose가 `postgres` · `redis`로 자동 치환한다.

---

## API

전체 명세는 `/docs`(Swagger UI) 참고.

| Method | Path | 인증 | 설명 |
|---|---|---|---|
| GET | `/health` | - | 헬스체크 |
| POST | `/api/v1/auth/register` | - | 회원가입 → 201 |
| POST | `/api/v1/auth/login` | - | 로그인 → JWT 발급 |
| GET | `/api/v1/auth/me` | Bearer | 내 정보 조회 |
| POST | `/api/v1/ai/ingest` | Bearer | 자연어 입력 접수 → 202 + 작업 ID |
| GET | `/api/v1/ai/jobs/{job_id}` | Bearer | 작업 상태 조회 |

로그인은 JSON이 아니라 OAuth2 form 형식이며, `username` 필드에 이메일을
넣는다.

### 처리 흐름

```
POST /api/v1/ai/ingest  →  202 { job_id, status: "PENDING" }
                              ↓ 워커가 큐에서 가져가 처리
GET /api/v1/ai/jobs/{job_id}  →  200 { status, intent, result_ref_type,
                                       result_ref_id, error, ... }
```

상태는 `PENDING → PROCESSING → SUCCESS` 순으로 전이하며, LLM 호출이
실패하면 `FAILED`가 되고 `error`에 사유가 기록된다.

분류 결과가 `task` · `schedule` · `memo`면 해당 테이블에 레코드가 생성되고
`result_ref_type` · `result_ref_id`에 참조가 담긴다. `research`는 저장할
엔티티가 없으므로 `SUCCESS`로 종료하되 참조는 비어 있다.

존재하지 않는 작업 ID와 다른 사용자의 작업은 모두 404로 응답한다.

---

## 트러블슈팅

실제로 겪은 문제와 해결 과정은
[TROUBLESHOOTING.md](./docs/TROUBLESHOOTING.md)에 기록한다.

---

## 로드맵

진행 중인 프로젝트다. 아래는 현재까지 구현된 범위와 바로 다음 단계이며,
실제로 사용하면서 계속 확장한다.

| 기능 | 상태 |
|---|---|
| 인증 (회원가입 · 로그인 · 조회) | 구현 완료 |
| LLM 추상화 계층 + 구조화 출력 + 폴백 체인 | 구현 완료 |
| 자연어 입력 → Celery 비동기 처리 → 202/폴링 | 구현 완료 |
| Task · Schedule · Memo 조회 API | 다음 단계 |
| Celery 태스크 재시도 정책 | 다음 단계 |

다음 스코프로 미룬 것: 폴백 체인 실운영 활성화, 상대 시각 지원,
사용자별 타임존, refresh 토큰, RAG 검색. EC2 배포는 이번 버전 범위에
두지 않았다.

---

## 현재 제약 사항 및 향후 개선 과제

- **상대 시각 미지원**: "3시간 뒤"처럼 현재 시각을 기준으로 하는 표현은
  계산하지 않는다. 모델에 현재 시각을 주지 않는 설계의 결과이며, 필요해지면
  결정론적 날짜 파싱으로 후처리하는 것이 정공법이다.

- **시각 미지정 일정의 기본값 미정의**: "다음 주 수요일에 회의"처럼 시각이
  없는 경우 실행마다 다른 기본 시각이 나올 수 있다.

- **요일 표현의 주차 모호성**: "금요일까지"를 오늘이 금요일일 때 이번 주로
  볼지 다음 주로 볼지 실행마다 다르게 해석될 수 있다. 사람에게도 정답이
  하나로 정해지지 않는 경계 케이스로 분류했다.

- **중단된 작업의 복구 미구현**: 워커 프로세스가 중단되거나 결과 기록 중
  예외가 발생하면 해당 작업은 `PROCESSING` 상태로 남는다. 재배달되더라도
  선점 조건(`status = 'PENDING'`)에 걸리지 않아 다시 처리되지 않으며,
  복구는 다음 단계의 재시도 정책에서 다룬다.

- **CORS 미설정**: 현재 클라이언트가 Swagger UI뿐이라 별도 설정을 두지
  않았다. 외부 origin에서 호출하려면 미들웨어 추가가 필요하다.

- **정규 테스트 코드 없음**: 각 단계는 `scripts/` 아래 검증 스크립트로
  실제 값을 확인하며 진행했다. 실제로 사용해보면서 반복 검증이 필요한
  지점부터 정규 테스트로 옮길 계획이다.
