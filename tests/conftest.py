import os
os.environ["POSTGRES_DB"] = "aiuto_test"

import time
import pytest
from alembic.config import Config
from alembic import command
import sqlalchemy as sa

# app
from app.core.db import sync_engine, get_sync_db
from app.models.user import User
from app.models.ai_job import AiJob
from app.enums import AiJobStatus
from app.worker import tasks
from app.worker.llm.base import ClassificationResult, ExtractedData



@pytest.fixture(scope="session")
def migrated_db():
    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head")

@pytest.fixture
def clean_db(migrated_db):
    assert sync_engine.url.database == "aiuto_test", "테스트 DB가 아니라서 비우지 않고 멈춘다"
    with sync_engine.begin() as conn:
        conn.execute(
            sa.text(
                "TRUNCATE users, ai_jobs, memos, tasks, schedules CASCADE"
            )
        )

@pytest.fixture
def pending_job(clean_db):
    with get_sync_db() as session:
        user = User(email="job@test.com", password_hash="x")
        session.add(user)
        session.flush()
        job = AiJob(user_id=user.id, raw_text="이번주 채용공고 지원 계획 점검", status=AiJobStatus.PENDING)
        session.add(job)
        session.flush()
        job_id = str(job.id)
    return job_id

class FakeLLMClient:
    def __init__(self):
        self.calls = 0
        self.delay = 0

    def classify(self, prompt, now_iso, timezone):
        self.calls += 1
        result = ClassificationResult(intent="memo", confidence=0.9, extracted=ExtractedData(content=prompt), model_used="fake")
        time.sleep(self.delay)
        return result

@pytest.fixture
def fake_llm(monkeypatch):
    fake = FakeLLMClient()
    def give_fake():
        return fake
    monkeypatch.setattr(tasks, "get_llm_client", give_fake)
    return fake