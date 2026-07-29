# Aiuto-v2
Aiuto프로젝트 v2개발 레포지토리입니다.

자연어 입력을 LLM으로 의도 분류하고 Celery 비동기 파이프라인으로 처리해
할 일·일정·메모로 구조화 저장하는 멀티유저 AI 비서 백엔드.

## 기술 스택

| 역할 | 기술 |
|---|---|
| 웹 프레임워크 | FastAPI 0.115 (async) |
| ORM / 마이그레이션 | SQLAlchemy 2.0 + Alembic |
| 비동기 큐 | Celery 5 + Redis 7 |
| LLM | Gemini 2.5 Flash |
| DB | PostgreSQL 17 |
| 인증 | PyJWT + argon2 |
| 배포 | Docker Compose + EC2 t3.small |

## 상태

현재 구현 중 (STEP 5 / 10)

> 아키텍처 다이어그램, 실행 방법, API 명세, 설계 결정은
> 핵심 파이프라인 완성 후 추가 예정.

```
Aiuto-v2
├─ aiuto_v2.db
├─ app
│  ├─ api
│  │  ├─ deps.py
│  │  ├─ v1
│  │  │  ├─ endpoints
│  │  │  │  ├─ auth.py
│  │  │  │  └─ __init__.py
│  │  │  └─ __init__.py
│  │  └─ __init__.py
│  ├─ core
│  │  ├─ security.py
│  │  └─ __init__.py
│  ├─ main.py
│  ├─ models
│  │  ├─ user.py
│  │  └─ __init__.py
│  ├─ schemas
│  │  ├─ token.py
│  │  ├─ user.py
│  │  └─ __init__.py
│  └─ __init__.py
├─ README.md
└─ requirements.txt

```