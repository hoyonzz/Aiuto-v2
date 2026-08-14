from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo



def build_date_anchors(now_iso: str) -> str:
    utc_dt = datetime.fromisoformat(now_iso)
    kst_dt = utc_dt.astimezone(ZoneInfo("Asia/Seoul"))
    today = kst_dt.date()
    tomorrow = today + timedelta(days=1)
    day_after = today + timedelta(days=2)
    return f"""
    [날짜 참고표 — 계산 없이 이 표만 참조할 것]
    오늘(KST): {today}
    내일(KST): {tomorrow}
    모레(KST): {day_after}
    """

def to_utc_iso(local_str: str, tz_name: str) -> str:
    local_time = datetime.fromisoformat(local_str)
    local_time = local_time.replace(tzinfo=ZoneInfo(tz_name))
    local_time = local_time.astimezone(timezone.utc)
    local_time = local_time.isoformat()
    return local_time