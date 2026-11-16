import sqlalchemy as sa
import threading

# app
from app.core.db import sync_engine
from app.worker import tasks



def test_scenario_a_sequential(pending_job, fake_llm):
    tasks.process_ingest_task(pending_job)
    tasks.process_ingest_task(pending_job)
    assert fake_llm.calls == 1
    with sync_engine.connect() as conn:
        memo_count = conn.execute(sa.text(
            "SELECT count(*) FROM memos"
        )).scalar_one()
        memo_id = conn.execute(sa.text(
            "SELECT id FROM memos"
        )).scalar_one()
        job = conn.execute(sa.text(
            "SELECT status, intent, result_ref_type, result_ref_id FROM ai_jobs WHERE id = :id"
        ), {"id": pending_job}).one()
    assert memo_count == 1
    assert job.status == "SUCCESS"
    assert job.intent == "MEMO"
    assert job.result_ref_type == "memo"
    assert job.result_ref_id == memo_id

def test_scenario_b_concurrent(pending_job, fake_llm):
    errors = []
    barrier = threading.Barrier(2, timeout=5)
    def run_worker():
        try:
            barrier.wait()
            tasks.process_ingest_task(pending_job)
        except Exception as e:
            errors.append(e)
    t1 = threading.Thread(target=run_worker)
    t2 = threading.Thread(target=run_worker)
    t1.start()
    t2.start()
    t1.join()
    t2.join()
    assert errors == []
    assert fake_llm.calls == 1
    with sync_engine.connect() as conn:
        memo_count = conn.execute(sa.text(
            "SELECT count(*) FROM memos"
        )).scalar_one()
        memo_id = conn.execute(sa.text(
            "SELECT id FROM memos"
        )).scalar_one()
        job = conn.execute(sa.text(
            "SELECT status, intent, result_ref_type, result_ref_id FROM ai_jobs WHERE id = :id"
        ), {"id": pending_job}).one()
    assert memo_count == 1
    assert job.status == "SUCCESS"
    assert job.intent == "MEMO"
    assert job.result_ref_type == "memo"
    assert job.result_ref_id == memo_id
