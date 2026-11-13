import sqlalchemy as sa
from app.core.db import get_sync_db, sync_engine
from app.models.user import User



def test_engine_uses_test_db():
    test_database = sync_engine.url.database
    print(test_database)
    assert test_database == "aiuto_test"

def test_tables_exist(migrated_db):
    test_db = sa.inspect(sync_engine)
    assert test_db.has_table('ai_jobs')

def test_insert_user(clean_db):
    with get_sync_db() as session:
        session.add(User(email="k4@test.com", password_hash="x"))
    with sync_engine.connect() as conn:
        result = conn.execute(sa.text(
            "SELECT count(*) FROM users"
        )).scalar_one()
    assert result == 1

def test_user_id_filled_at_flush(clean_db):
    with get_sync_db() as session:
        user = User(email="k5@test.com", password_hash="x")
        before = user.id
        session.add(user)
        session.flush()
        assert before is None
        assert user.id is not None 

def test_pending_job_is_committed(pending_job):
    with sync_engine.connect() as conn:
        result = conn.execute(sa.text(
            "SELECT status FROM ai_jobs WHERE id = :id"
        ), {"id": pending_job}).scalar_one()
    assert result == "PENDING"