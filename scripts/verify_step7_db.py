import uuid
import sys
import os


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError

from app.core.db import get_sync_db
from app.models.user import User
from app.models.task import Task
from app.models.ai_job import AiJob
from app.enums import TaskStatus, AiJobStatus, Intent



def run_vieryfication():
    print("🚀 [Step 7] DB 도메인 모델 및 제약조건 검증 시작\n")

    test_email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    created_user_id = None
    created_task_id = None

    # 1. 테스트용 부모 User 생성
    with get_sync_db() as session:
        user = User(
            email=test_email,
            password_hash="dummy_hashed_password",
            is_active=True,
        )
        session.add(user)
        session.commit()
        created_user_id = user.id
        print(f"✅ 1. 테스트 User 생성 성공 (user_id: {created_user_id})")

    # 정상 insert 및 별도 세션 재조회, uuid 타입 검증
    with get_sync_db() as session:
        task = Task(
            user_id=created_user_id,
            title="검증용 태스크",
            status=TaskStatus.TODO,
        )
        session.add(task)
        session.commit()
        created_task_id = task.id

    # 새로운 세션에서 분리 조회
    with get_sync_db() as session:
        saved_task = session.get(Task, created_task_id)
        assert saved_task is not None, "❌ Task 조회 실패"
        assert isinstance(saved_task.id, uuid.UUID), "❌ task.id가 UUID 타입이 아닙니다."
        assert isinstance(saved_task.user_id, uuid.UUID), "❌ task.user_id가 UUID 타입이 아닙니다."
        assert saved_task.status == TaskStatus.TODO, "❌ Task 상태값 불일치"
        print("✅ 2. 정상 INSERT 및 별도 세션 재조회 / UUID 타입 검증 통과")        

    # Foreign Key 위반 차단 검증
    fake_user_id = uuid.uuid4()
    fk_blocked = False
    try:
        with get_sync_db() as session:
            invalid_task = Task(
                user_id = fake_user_id,
                title = "FK 위반 테스트",
                status = TaskStatus.TODO,
            )
            session.add(invalid_task)
            session.commit()
    except IntegrityError:
        fk_blocked = True
        print("✅ 3. 존재하지 않는 user_id에 대한 FK 위반 예외 차단 통과 (IntegrityError 발생)")

    assert fk_blocked, "❌ 존재하지 않는 user_id로의 INSERT가 차단되지 않았습니다!"

    # CHECK 제약조건 위반 차단 검증
    check_blocked = False
    try:
        with get_sync_db() as session:
            session.execute(
                sa.text(
                    "INSERT INTO tasks (id, user_id, title, status, created_at, updated_at) "
                    "VALUES (:id, :user_id, :title, :status, NOW(), NOW())"  # 👈 이 줄 추가
                ),
                {
                    "id": uuid.uuid4(),
                    "user_id": created_user_id,
                    "title": "CHECK 위반 테스트",
                    "status": "INVALID_STATUS_VALUE",
                },
            )
            session.commit()

    except IntegrityError:
        check_blocked = True
        print("✅ 4. Enum 정의에 없는 값에 대한 DB CHECK 제약 차단 통과 (IntegrityError 발생)")

    assert (check_blocked), "❌ DB CHECK 제약이 잘못된 status 값을 차단하지 못했습니다!"

    # 테스트 데이터 정리
    with get_sync_db() as session:
        user_to_delete = session.get(User, created_user_id)
        if user_to_delete:
            session.delete(user_to_delete)
            session.commit()
        print("✅ 5. 테스트 데이터 정리 완료")

    print("\n🎉 게이트 ① (DB 모델 / 제약조건 / 동기 세션 라이프사이클) 검증 100% 통과!")      

if __name__ == "__main__":
    run_vieryfication()