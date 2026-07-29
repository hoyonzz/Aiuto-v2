# Aiuto

자연어 입력을 LLM으로 의도 분류하고 Celery 비동기 파이프라인으로 처리해
할 일·일정·메모로 구조화 저장하는 멀티유저 AI 비서 백엔드.

## 기술 스택

| 역할 | 기술 | 선택 이유 |
|---|---|---|
| 웹 프레임워크 | FastAPI (async) | async 네이티브, 자동 OpenAPI 문서화 |
| ORM / 마이그레이션 | SQLAlchemy 2.0 + Alembic | 비동기 세션 지원, 명시적 2.0 스타일 매핑 |
| DB | PostgreSQL | 멀티유저 SaaS에 필요한 서버형 DB, JSONB·pgvector 확장 여지 |
| 인증 | PyJWT + argon2 | stateless API 인증, argon2는 현행 비밀번호 해싱 권장 표준 |
| PK 전략 | UUID | 순차 정수 PK의 열거(enumeration) 공격 노출 방지 |
| 설정 관리 | pydantic-settings | 환경변수를 타입 검증된 객체로 로드 |
| 로컬 인프라 | Docker Compose (PostgreSQL, Redis) | 재현 가능한 로컬 개발 환경 |

## 아키텍처 결정

### API/워커 드라이버 이원화

FastAPI(비동기)와 향후 추가될 Celery 워커(동기 프로세스)가 같은 PostgreSQL을
쓰지만, 접근 경로를 처음부터 분리했다. API는 `asyncpg` 드라이버로 비동기
접속하고, 마이그레이션 도구(Alembic)는 `psycopg` 동기 드라이버로 별도
접속한다. 마이그레이션 도구를 굳이 비동기로 만들 필요가 없고, 향후 Celery
워커도 동기 세션을 쓸 예정이라 이 경계를 미리 맞춰둔 것이다.

### PK를 UUID로 설계

멀티유저 SaaS에서 순차 정수 PK(`/tasks/1`, `/tasks/2`)는 다른 사용자의
레코드를 추측·열거하기 쉽다. 모든 테이블의 PK를 UUID로 설계해 이 문제를
원천 차단했다.

### JWT 설계 — UUID 기반 subject, type 클레임 분리

JWT의 `sub`(subject)에는 사용자 이메일이 아니라 UUID를 담는다. 이메일은
변경 가능하고 개인정보이므로 토큰에 실을 이유가 없다. 또한 `type` 클레임을
고정값(`access`)으로 명시해, 이후 토큰 종류가 늘어나도(예: refresh) 서로
다른 용도의 토큰이 잘못된 자리에 쓰이는 것을 코드 레벨에서 차단할 수 있게
설계했다.

## 로컬 실행

```bash
git clone https://github.com/hoyonzz/Aiuto-v2.git
cd Aiuto-v2
cp .env.example .env        # SECRET_KEY, POSTGRES_* 값 채우기
docker compose up -d        # postgres, redis 기동
pip install -r requirements.txt
alembic upgrade head        # 마이그레이션 적용
uvicorn app.main:app --reload
```

확인: `http://localhost:8000/docs`

## API 명세 (현재 구현분)

전체 명세는 `/docs`(Swagger UI) 참고.

| Method | Path | 인증 | 설명 |
|---|---|---|---|
| POST | `/api/v1/auth/register` | - | 회원가입 |
| POST | `/api/v1/auth/login` | - | 로그인 → JWT access token 발급 |
| GET | `/api/v1/auth/me` | Bearer | 내 정보 조회 |

## 트러블슈팅

실제로 겪은 문제와 해결 과정은 [TROUBLESHOOTING.md](./TROUBLESHOOTING.md)에 기록한다.

## 로드맵 (V3 설계·예정)

현재는 핵심 인증 파이프라인까지 완료된 상태다. 아래는 설계는 확정했으나
아직 구현하지 않은 항목이다.

| 기능 | 상태 |
|---|---|
| 자연어 입력 → LLM 의도 분류 → Celery 비동기 처리 | 설계 완료, 구현 예정 |
| Task/Schedule/Memo 저장 및 조회 API | 설계 완료, 구현 예정 |
| EC2 + Docker Compose + Nginx 배포 | 설계 완료, 구현 예정 |
| refresh 토큰 / 로그아웃 / 블랙리스트 | V3 설계 예정 |
| streak / 마스코트 게이미피케이션 | V3 설계 예정 (DB 필드 자리만 확보) |
| LangGraph 기반 멀티스텝 분류, SSE 스트리밍 | V3 설계 예정 |
| pgvector 기반 RAG 검색 | V3 설계 예정 |
