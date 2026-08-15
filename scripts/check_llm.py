"""STEP 6 시각 처리 재설계 후 스모크 테스트.

실행: 프로젝트 루트에서  python -m scripts.check_llm
.env의 LLM_CHAIN은 gemini 단독 상태여야 함.
"""

from datetime import datetime, timezone as dt_timezone

from app.worker.llm.factory import get_llm_client


client = get_llm_client()
print("클라이언트 타입:", type(client).__name__)

now_iso = datetime.now(dt_timezone.utc).isoformat()
print("기준 시각:", now_iso)


def show(label: str, result) -> None:
    print(f"\n[{label}] intent: {result.intent} | confidence: {result.confidence}")
    print(f"  title: {result.extracted.title!r} (길이: {len(result.extracted.title or '')})")
    print(f"  start_at: {result.extracted.start_at}")
    print(f"  due_date: {result.extracted.due_date}")   # ← 여기로 이동
    print(f"  content: {result.extracted.content}")
    print(f"  topic: {result.extracted.topic}")


# 1) 회귀 확인 — 어제 title 누출이 터졌던 그 문장
res1 = client.classify("내일 오전 10시에 알고리즘 복습", now_iso=now_iso, timezone="Asia/Seoul")
show("1 회귀", res1)
assert res1.intent == "schedule"
assert res1.extracted.start_at is not None
assert len(res1.extracted.title) <= 30, "title에 사고 과정이 새고 있을 가능성"

# 2) 자정 경계
res2 = client.classify("오늘 자정에 프로젝트 마감이야", now_iso=now_iso, timezone="Asia/Seoul")
show("2 자정 경계", res2)
assert res2.intent == "schedule"
assert res2.extracted.start_at is not None

# 3) 앵커 표 밖(다음주) + 시각 있음
res3 = client.classify("다음주 화요일 오전 9시에 병원 예약", now_iso=now_iso, timezone="Asia/Seoul")
show("3 다음주+시각", res3)
assert res3.intent == "schedule"
# start_at은 확정 assert 없이 눈으로 확인 (앵커 표에 없는 범위라 틀릴 수 있음)

# 4) 앵커 표 밖(다음주) + 시각 없음
res4 = client.classify("다음주 수요일에 정기 회의", now_iso=now_iso, timezone="Asia/Seoul")
show("4 다음주+시각없음", res4)
assert res4.intent == "schedule"
# start_at이 어떻게 채워지는지(또는 None인지) 눈으로 확인

# 5) memo vs schedule 경계 (과거 시제)
res5 = client.classify("어제 회의에서 예산 300만 승인됐음", now_iso=now_iso, timezone="Asia/Seoul")
show("5 memo vs schedule", res5)
assert res5.intent == "memo"

# 6) task vs schedule 경계 — 정답 하나로 안 정함, 관찰만
res6 = client.classify("금요일까지 보고서 제출해야 함", now_iso=now_iso, timezone="Asia/Seoul")
show("6 task vs schedule (관찰용)", res6)

# 7) 상대 시각(현재 몇 시인지 필요) — 지금 설계로는 원천적으로 못 풂, 관찰만
res7 = client.classify("3시간 뒤에 다시 전화하기", now_iso=now_iso, timezone="Asia/Seoul")
show("7 상대시각 (알려진 한계, 관찰용)", res7)

# 8) title 방어 스트레스 — max_length는 아직 미적용, 길이만 관찰
res8 = client.classify(
    "내일 오후 2시에 강남역 스타벅스에서 프로젝트 킥오프 미팅 및 향후 일정 조율하기",
    now_iso=now_iso,
    timezone="Asia/Seoul",
)
show("8 title 길이 스트레스", res8)
assert res8.intent == "schedule"
assert res8.extracted.start_at is not None

# 9) task + due_date
res9 = client.classify("다음주 화요일까지 세미나 자료 준비", now_iso=now_iso, timezone="Asia/Seoul")
show("9 due_date", res9)
assert res9.intent == "task"
assert res9.extracted.start_at is None

print("\n✅ 1·2·3·4·5·8 assert 통과 (6·7은 관찰용, 위 출력을 직접 확인하세요)")