import os
os.environ["POSTGRES_DB"] = "aiuto_test"

import pytest
from alembic.config import Config
from alembic import command
import sqlalchemy as sa
from app.core.db import sync_engine



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